"""Turn BeautifulSoup document into string lines for each course, then
parse lines/elements into its right component of RawCourse"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from app.models import Course
from app.services.prereq_parser import parse_prerequisites


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
    requirement_codes = [
        _normalize_text(requirement.get_text(" ", strip=True))
        for requirement in entry.select("span.requirement")
    ]
    core_req_text = (
        f"[ {' '.join(requirement_codes)} ]" if requirement_codes else ""
    )

    pre_req_text = ""
    details = entry.find("p")
    detail_parts = _entry_text_parts(details) if details is not None else []

    if detail_parts and PREREQUISITE_PATTERN.match(detail_parts[0]):
        pre_req_text = PREREQUISITE_PATTERN.sub(
            "", detail_parts.pop(0), count=1
        )

    return RawCourse(
        code=code,
        title=title,
        description=_normalize_text(" ".join(detail_parts)),
        core_req_text=core_req_text,
        pre_req_text=pre_req_text,
    )


def parse_raw_courses(document: BeautifulSoup) -> list[RawCourse]:
    courses: list[RawCourse] = []

    for entry in document.select(COURSE_ENTRY_SELECTOR):
        course = _extract_raw_course(entry)

        if course is not None:
            courses.append(course)

    return courses


def _build_course(raw: RawCourse) -> Course:
    core_requirements = raw.core_req_text.strip("[] ").split()

    return Course(
        code=raw.code,
        title=raw.title,
        description=raw.description,
        core_req=core_requirements,
        pre_req=parse_prerequisites(raw.pre_req_text),
    )


def parse_courses(document: BeautifulSoup) -> list[Course]:
    return [_build_course(raw) for raw in parse_raw_courses(document)]
