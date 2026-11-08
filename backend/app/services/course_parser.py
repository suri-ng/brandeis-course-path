"""Turn BeautifulSoup document into string lines for each course, then
parse lines/elements into its right component of RawCourse"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag


@dataclass(frozen=True)
class RawCourse:
    code: str
    title: str
    description: str = ""
    core_req_text: str = ""
    pre_req_text: str = ""


COURSE_ENTRY_SELECTOR = "div.accordion__content > p"

COURSE_HEADING_PATTERN = re.compile(
    r"^(?P<code>[A-Z]{2,5}\s+\d+[A-Za-z]?)\s+(?P<title>.+)$"
)
WHITESPACE_PATTERN = re.compile(r"\s+")
CORE_REQUIREMENT_PATTERN = re.compile(r"^\[[^]]+\]$")
PREREQUISITE_PATTERN = re.compile(r"^Prerequisites?:\s*", re.IGNORECASE)


def _normalize_text(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def _parse_course_heading(text: str) -> tuple[str, str] | None:
    match = COURSE_HEADING_PATTERN.fullmatch(_normalize_text(text))
    if match is None:
        return None

    return match.group("code"), match.group("title")


def _entry_text_parts(entry: Tag) -> list[str]: # turn each entry into list of string lines
    return [
        normalized
        for part in entry.get_text("\n", strip=True).splitlines()
        if (normalized := _normalize_text(part))
    ]


def _extract_raw_course(entry: Tag) -> RawCourse | None: #return singular RawCourse
    heading = entry.find("strong")
    if heading is None:
        return None

    heading_text = _normalize_text(heading.get_text(" ", strip=True))
    parsed_heading = _parse_course_heading(heading_text)
    if parsed_heading is None:
        return None

    code, title = parsed_heading
    parts = _entry_text_parts(entry)

    if parts and parts[0] == heading_text: # if list is not empty and first item of the list is heading_text then parts is the rest of the list
        parts = parts[1:]

    core_req_text = ""
    pre_req_text = ""
    description_parts: list[str] = []

    for part in parts:
        if not core_req_text and CORE_REQUIREMENT_PATTERN.fullmatch(part):
            core_req_text = part
        elif not pre_req_text and PREREQUISITE_PATTERN.match(part):
            pre_req_text = PREREQUISITE_PATTERN.sub("", part, count=1)
        else:
            description_parts.append(part)

    return RawCourse(
        code=code,
        title=title,
        description=_normalize_text(" ".join(description_parts)),
        core_req_text=core_req_text,
        pre_req_text=pre_req_text,
    )


def parse_courses(document: BeautifulSoup) -> list[RawCourse]: # return list of RawCourse
    courses: list[RawCourse] = []

    for entry in document.select(COURSE_ENTRY_SELECTOR):
        course = _extract_raw_course(entry)

        if course is not None:
            courses.append(course)

    return courses
