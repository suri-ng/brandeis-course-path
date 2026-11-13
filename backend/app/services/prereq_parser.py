"""Parse Brandeis prerequisite prose into nested AND/OR groups."""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.models import PrereqGroup


PrerequisiteItem = str | PrereqGroup

WHITESPACE_PATTERN = re.compile(r"\s+")
COURSE_REFERENCE_PATTERN = re.compile(
    r"\b(?:(?P<subject>(?!(?:and|or|either|both)\b)[A-Za-z]{2,5})\s+)?"
    r"(?P<number>\d{1,3}[A-Za-z]{1,2})\b",
    re.IGNORECASE,
)
EXPLICIT_COURSE_PATTERN = re.compile(
    r"\b(?P<subject>[A-Z]{2,5})\s+"
    r"(?P<number>\d{1,3}[a-z]{1,2})\b"
)

IGNORED_CLAUSE_PATTERNS = (
    re.compile(r"\b(?:and|or)?\s*permission of (?:the )?instructor\b", re.I),
    re.compile(r"\b(?:and|or)?\s*consent of (?:the )?instructor\b", re.I),
    re.compile(r"\b(?:and|or)?\s*(?:an )?equivalent(?:s)?\b", re.I),
    re.compile(r"\b(?:and|or)?\s*at least \w+ standing\b", re.I),
    re.compile(r"\b(?:and|or)?\s*\w+ standing\b", re.I),
)
NON_PREREQUISITE_TAIL_PATTERN = re.compile(
    r"\b(?:May not be taken|Students must|Juniors? and seniors?|"
    r"Enrollment|Priority|Yields)\b.*$",
    re.I,
)
LEADING_PHRASE_PATTERN = re.compile(
    r"^(?:(?:one|any) of (?:the following)?|either|both)\s*:?[ ]*",
    re.I,
)


def _normalize_whitespace(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def _clean_prerequisite_text(text: str) -> str:
    cleaned = _normalize_whitespace(text)
    cleaned = NON_PREREQUISITE_TAIL_PATTERN.sub("", cleaned)

    for pattern in IGNORED_CLAUSE_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    return cleaned.strip(" ,.;:")


def _expand_shorthand_codes(text: str) -> str: # Expand references such as 'PSYC 10a and 51a' to full codes.
    current_subject: str | None = None

    def replace(match: re.Match[str]) -> str:
        nonlocal current_subject

        subject = match.group("subject")
        number = match.group("number").lower()

        if subject is not None:
            current_subject = subject.upper()
        elif current_subject is None:
            return match.group(0)

        return f"{current_subject} {number}"

    return COURSE_REFERENCE_PATTERN.sub(replace, text)


def _strip_wrapping_parentheses(text: str) -> str:
    text = text.strip()

    while text.startswith("(") and text.endswith(")"):
        depth = 0
        wraps_entire_text = True

        for index, character in enumerate(text):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1

            if depth == 0 and index != len(text) - 1:
                wraps_entire_text = False
                break

        if not wraps_entire_text:
            break

        text = text[1:-1].strip()

    return text


def _split_top_level(text: str, delimiter: str) -> list[str]: # Split on a word or comma only when outside parentheses
    parts: list[str] = []
    start = 0
    depth = 0
    index = 0
    lowered = text.lower()

    while index < len(text):
        character = text[index]

        if character == "(":
            depth += 1
            index += 1
            continue
        if character == ")":
            depth = max(0, depth - 1)
            index += 1
            continue

        if depth == 0:
            if delimiter == "," and character == ",":
                parts.append(text[start:index].strip())
                start = index + 1
                index += 1
                continue

            if delimiter != ",":
                candidate = f" {delimiter} "
                if lowered.startswith(candidate, index):
                    parts.append(text[start:index].strip())
                    start = index + len(candidate)
                    index = start
                    continue

        index += 1

    if not parts:
        return [text.strip()]

    parts.append(text[start:].strip())
    return [part for part in parts if part]


def _make_group(
    operator: str,
    items: Sequence[PrerequisiteItem | None],
) -> PrereqGroup | None:
    flattened: list[PrerequisiteItem] = []

    for item in items:
        if item is None:
            continue
        if isinstance(item, PrereqGroup) and len(item.items) == 1:
            flattened.append(item.items[0])
            continue
        if isinstance(item, PrereqGroup) and item.operator == operator:
            flattened.extend(item.items)
        else:
            flattened.append(item)

    if not flattened:
        return None

    return PrereqGroup(operator=operator, items=flattened)


def _parse_leaf(text: str) -> PrereqGroup | None:
    codes = [
        f"{match.group('subject')} {match.group('number')}"
        for match in EXPLICIT_COURSE_PATTERN.finditer(text)
    ]

    if not codes:
        return None

    # Adjacent codes without a recognized connector are treated as jointly
    # required. This is safer than just discarding a course reference.
    return _make_group("AND", codes)


def _parse_expression(text: str) -> PrereqGroup | None:
    text = _strip_wrapping_parentheses(text.strip(" ,.;:"))
    text = LEADING_PHRASE_PATTERN.sub("", text)
    if not text:
        return None

    # Brandeis commonly writes "A and either B or C". "Either" scopes the
    # OR alternatives, so handle that phrase before ordinary precedence.
    and_either_parts = _split_top_level(text, "and either")
    if len(and_either_parts) > 1:
        return _make_group(
            "AND",
            [_parse_expression(part) for part in and_either_parts],
        )

    comma_parts = _split_top_level(text, ",")
    if len(comma_parts) > 1:
        last_part = comma_parts[-1]
        conjunction = "AND"

        if re.match(r"^or\b", last_part, re.I):
            conjunction = "OR"
            comma_parts[-1] = re.sub(r"^or\s+", "", last_part, flags=re.I)
        elif re.match(r"^and\b", last_part, re.I):
            comma_parts[-1] = re.sub(r"^and\s+", "", last_part, flags=re.I)

        return _make_group(
            conjunction,
            [_parse_expression(part) for part in comma_parts],
        )

    or_parts = _split_top_level(text, "or")
    if len(or_parts) > 1:
        return _make_group(
            "OR",
            [_parse_expression(part) for part in or_parts],
        )

    and_parts = _split_top_level(text, "and")
    if len(and_parts) > 1:
        return _make_group(
            "AND",
            [_parse_expression(part) for part in and_parts],
        )

    return _parse_leaf(text)


def parse_prerequisites(text: str) -> PrereqGroup | None:
    """Convert prerequisite prose into a recursive AND/OR tree.

    All referenced course codes are retained. Whether a referenced course is
    external to the prepared catalog is decided later by the graph builder.
    """
    cleaned = _clean_prerequisite_text(text)
    if not cleaned:
        return None

    expanded = _expand_shorthand_codes(cleaned)
    return _parse_expression(expanded)
