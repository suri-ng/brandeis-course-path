import pytest
from bs4 import BeautifulSoup

from app.models import Course, PrereqGroup
from app.services.course_parser import (
    RawCourse,
    _build_course,
    _entry_text_parts,
    _extract_raw_course,
    _normalize_text,
    _parse_course_heading,
    parse_courses,
    parse_raw_courses,
)


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def course_entry(
    heading: str,
    *,
    requirements: tuple[str, ...] = (),
    details: str | None = None,
) -> str:
    requirement_html = "".join(
        f'<span class="requirement">{code}</span>' for code in requirements
    )
    details_html = f"<p>{details}</p>" if details is not None else ""

    return f"""
        <p>
            <strong>{heading}</strong>
            <br>
            [{requirement_html}]
            <br>
            {details_html}
        </p>
    """


def catalog_page(*entries: str) -> BeautifulSoup:
    return soup(
        '<div class="accordion">'
        '<div class="accordion__content">'
        + "".join(entries)
        + "</div></div>"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("  PSYC 10a  ", "PSYC 10a"),
        ("PSYC\t10a\nIntroduction", "PSYC 10a Introduction"),
        ("A   title—with punctuation, commas; and (parentheses).", "A title—with punctuation, commas; and (parentheses)."),
        ("", ""),
    ],
)
def test_normalize_text_collapses_whitespace_but_preserves_punctuation(
    text: str,
    expected: str,
) -> None:
    assert _normalize_text(text) == expected


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        ("PSYC 10a Introduction to Psychology", ("PSYC 10a", "Introduction to Psychology")),
        ("COSI 104a Fundamentals of Software Engineering", ("COSI 104a", "Fundamentals of Software Engineering")),
        ("NPSY 199a Human Neuropsychology", ("NPSY 199a", "Human Neuropsychology")),
        ("MUS 99d Senior Research", ("MUS 99d", "Senior Research")),
        ("  PSYC 51a   Statistics  ", ("PSYC 51a", "Statistics")),
    ],
)
def test_parse_valid_course_headings(
    heading: str,
    expected: tuple[str, str],
) -> None:
    assert _parse_course_heading(heading) == expected


@pytest.mark.parametrize(
    "heading",
    [
        "Courses of Instruction",
        "PSYC Introduction to Psychology",
        "10a Introduction to Psychology",
        "PSYC 10a",
        "psyc 10a Introduction to Psychology",
        "",
    ],
)
def test_reject_invalid_course_headings(heading: str) -> None:
    assert _parse_course_heading(heading) is None


def test_entry_text_parts_uses_html_breaks_and_normalizes_each_part() -> None:
    entry = soup(
        "<p>Prerequisite:  PSYC 10a<br><br>"
        "A description with   repeated spaces.<br>Usually offered yearly.</p>"
    ).p

    assert entry is not None
    assert _entry_text_parts(entry) == [
        "Prerequisite: PSYC 10a",
        "A description with repeated spaces.",
        "Usually offered yearly.",
    ]


def test_extract_complete_brandeis_course_entry() -> None:
    document = catalog_page(
        course_entry(
            "NPSY 11b Introduction to Behavioral Neuroscience",
            requirements=("sn", "ss"),
            details=(
                "Prerequisite: PSYC 10a or MATH 10a.<br><br>"
                "Data and theories regarding brain-behavior relationships."
            ),
        )
    )
    entry = document.select_one("div.accordion__content > p")

    assert entry is not None
    assert _extract_raw_course(entry) == RawCourse(
        code="NPSY 11b",
        title="Introduction to Behavioral Neuroscience",
        description="Data and theories regarding brain-behavior relationships.",
        core_req_text="[ sn ss ]",
        pre_req_text="PSYC 10a or MATH 10a.",
    )


def test_fragmented_heading_text_is_joined_and_normalized() -> None:
    document = catalog_page(
        course_entry(
            "<span>PSYC</span> <span>52a</span> "
            "<span>Research Methods and Laboratory</span>",
            details="A supervised laboratory course.",
        )
    )

    assert parse_raw_courses(document)[0].code == "PSYC 52a"
    assert parse_raw_courses(document)[0].title == "Research Methods and Laboratory"


def test_extracts_all_requirement_codes_in_source_order() -> None:
    document = catalog_page(
        course_entry(
            "PSYC 52a Research Methods",
            requirements=("qr", "sn", "ss", "wi"),
            details="Laboratory work.",
        )
    )

    assert parse_raw_courses(document)[0].core_req_text == "[ qr sn ss wi ]"


def test_course_without_requirement_codes_has_empty_requirement_text() -> None:
    document = catalog_page(
        course_entry("PSYC 93a Independent Research", details="Supervised research.")
    )

    assert parse_raw_courses(document)[0].core_req_text == ""


@pytest.mark.parametrize(
    "prefix",
    ["Prerequisite:", "Prerequisites:", "PREREQUISITE:"],
)
def test_recognizes_prerequisite_prefix_variants(prefix: str) -> None:
    document = catalog_page(
        course_entry(
            "PSYC 52a Research Methods",
            details=f"{prefix} PSYC 10a and 51a.<br><br>Laboratory work.",
        )
    )

    course = parse_raw_courses(document)[0]
    assert course.pre_req_text == "PSYC 10a and 51a."
    assert course.description == "Laboratory work."


def test_course_without_prerequisite_uses_all_detail_text_as_description() -> None:
    document = catalog_page(
        course_entry(
            "MUS 1a Exploring Music",
            requirements=("ca",),
            details="Does not meet requirements for the major.<br><br>A general introduction to music.",
        )
    )

    course = parse_raw_courses(document)[0]
    assert course.pre_req_text == ""
    assert course.description == (
        "Does not meet requirements for the major. A general introduction to music."
    )


def test_prerequisite_and_description_punctuation_is_preserved() -> None:
    document = catalog_page(
        course_entry(
            "PSYC 153b Psychology of Trauma",
            details=(
                "Prerequisites: PSYC 10a and either PSYC 31a or PSYC 32a.<br><br>"
                "Examines trauma: theory, evidence, and treatment (clinical and social)."
            ),
        )
    )

    course = parse_raw_courses(document)[0]
    assert course.pre_req_text == "PSYC 10a and either PSYC 31a or PSYC 32a."
    assert course.description == (
        "Examines trauma: theory, evidence, and treatment (clinical and social)."
    )


def test_missing_detail_paragraph_produces_empty_optional_fields() -> None:
    document = catalog_page(course_entry("PSYC 98a Readings in Psychology"))

    assert parse_raw_courses(document) == [
        RawCourse(code="PSYC 98a", title="Readings in Psychology")
    ]


def test_skips_candidate_without_strong_heading() -> None:
    document = catalog_page("<p>An ordinary paragraph.</p>")

    assert parse_raw_courses(document) == []


def test_skips_strong_text_that_is_not_a_course_heading() -> None:
    document = catalog_page("<p><strong>Foundational Literacies:</strong> Text</p>")

    assert parse_raw_courses(document) == []


def test_skips_malformed_heading_but_continues_with_later_course() -> None:
    document = catalog_page(
        "<p><strong>Not a course</strong></p>",
        course_entry("PSYC 10a Introduction to Psychology", details="A survey."),
    )

    courses = parse_raw_courses(document)
    assert [course.code for course in courses] == ["PSYC 10a"]


def test_extracts_courses_from_multiple_accordion_sections() -> None:
    document = soup(
        '<div class="accordion__content">'
        + course_entry("PSYC 10a Introduction to Psychology", details="A survey.")
        + "</div>"
        '<div class="accordion__content">'
        + course_entry("PSYC 101a Seminar in Psychology", details="A seminar.")
        + "</div>"
    )

    assert [course.code for course in parse_raw_courses(document)] == [
        "PSYC 10a",
        "PSYC 101a",
    ]


def test_ignores_course_like_paragraph_outside_accordion_content() -> None:
    document = soup(
        course_entry("FAKE 10a Outside Course Section", details="Ignore me.")
        + '<div class="accordion__content">'
        + course_entry("PSYC 10a Introduction to Psychology", details="A survey.")
        + "</div>"
    )

    assert [course.code for course in parse_raw_courses(document)] == ["PSYC 10a"]


def test_empty_document_returns_no_courses() -> None:
    assert parse_raw_courses(soup("")) == []
    assert parse_courses(soup("")) == []


def test_build_course_converts_requirements_and_prerequisite_tree() -> None:
    raw = RawCourse(
        code="PSYC 52a",
        title="Research Methods",
        description="Laboratory work.",
        core_req_text="[ qr sn ss wi ]",
        pre_req_text="PSYC 10a and 51a.",
    )

    assert _build_course(raw) == Course(
        code="PSYC 52a",
        title="Research Methods",
        description="Laboratory work.",
        core_req=["qr", "sn", "ss", "wi"],
        pre_req=PrereqGroup(
            operator="AND",
            items=["PSYC 10a", "PSYC 51a"],
        ),
    )


def test_build_course_handles_missing_optional_fields() -> None:
    raw = RawCourse(code="PSYC 98a", title="Readings in Psychology")

    assert _build_course(raw) == Course(
        code="PSYC 98a",
        title="Readings in Psychology",
        description="",
        core_req=[],
        pre_req=None,
    )


def test_parse_courses_returns_final_pydantic_courses() -> None:
    document = catalog_page(
        course_entry(
            "PSYC 52a Research Methods",
            requirements=("qr", "sn"),
            details="Prerequisites: PSYC 10a and 51a.<br><br>Laboratory work.",
        )
    )

    courses = parse_courses(document)

    assert len(courses) == 1
    assert isinstance(courses[0], Course)
    assert courses[0].code == "PSYC 52a"
    assert courses[0].core_req == ["qr", "sn"]
    assert courses[0].pre_req == PrereqGroup(
        operator="AND",
        items=["PSYC 10a", "PSYC 51a"],
    )
