import pytest

from app.models import PrereqGroup
from app.services.prereq_parser import parse_prerequisites


def group(operator: str, *items: str | PrereqGroup) -> PrereqGroup:
    return PrereqGroup(operator=operator, items=list(items))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "Permission of the instructor.",
        "Consent of the instructor.",
        "At least sophomore standing.",
        "No formal prerequisite.",
    ],
)
def test_text_without_course_references_returns_none(text: str) -> None:
    assert parse_prerequisites(text) is None


@pytest.mark.parametrize(
    ("text", "expected_code"),
    [
        ("PSYC 10a.", "PSYC 10a"),
        ("psyc 10A.", "PSYC 10a"),
        ("COSI 21a", "COSI 21a"),
        ("NBIO 140b", "NBIO 140b"),
    ],
)
def test_single_course_reference(text: str, expected_code: str) -> None:
    assert parse_prerequisites(text) == group("AND", expected_code)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "PSYC 10a and PSYC 51a.",
            group("AND", "PSYC 10a", "PSYC 51a"),
        ),
        (
            "Both PSYC 10a and PSYC 51a.",
            group("AND", "PSYC 10a", "PSYC 51a"),
        ),
        (
            "PSYC 10a or MATH 10a.",
            group("OR", "PSYC 10a", "MATH 10a"),
        ),
        (
            "Either PSYC 10a or MATH 10a.",
            group("OR", "PSYC 10a", "MATH 10a"),
        ),
    ],
)
def test_simple_and_or_phrases(
    text: str,
    expected: PrereqGroup,
) -> None:
    assert parse_prerequisites(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "PSYC 10a and 51a.",
            group("AND", "PSYC 10a", "PSYC 51a"),
        ),
        (
            "PSYC 10a, 51a, and 52a.",
            group("AND", "PSYC 10a", "PSYC 51a", "PSYC 52a"),
        ),
        (
            "PSYC 31a, 32a, or 33a.",
            group("OR", "PSYC 31a", "PSYC 32a", "PSYC 33a"),
        ),
        (
            "COSI 21a or 29a.",
            group("OR", "COSI 21a", "COSI 29a"),
        ),
    ],
)
def test_abbreviated_codes_inherit_the_previous_subject(
    text: str,
    expected: PrereqGroup,
) -> None:
    assert parse_prerequisites(text) == expected


def test_explicit_subject_changes_shorthand_inheritance() -> None:
    result = parse_prerequisites("PSYC 10a, MATH 10a, and 15a.")

    assert result == group("AND", "PSYC 10a", "MATH 10a", "MATH 15a")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "PSYC 10a, PSYC 51a, and PSYC 52a.",
            group("AND", "PSYC 10a", "PSYC 51a", "PSYC 52a"),
        ),
        (
            "PSYC 31a, PSYC 32a, or PSYC 33a.",
            group("OR", "PSYC 31a", "PSYC 32a", "PSYC 33a"),
        ),
        (
            "One of the following: PSYC 31a, PSYC 32a, or PSYC 33a.",
            group("OR", "PSYC 31a", "PSYC 32a", "PSYC 33a"),
        ),
        (
            "Any of the following: COSI 21a, COSI 29a, or COSI 31a.",
            group("OR", "COSI 21a", "COSI 29a", "COSI 31a"),
        ),
    ],
)
def test_comma_lists(text: str, expected: PrereqGroup) -> None:
    assert parse_prerequisites(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "PSYC 10a and either PSYC 31a or PSYC 32a.",
            group(
                "AND",
                "PSYC 10a",
                group("OR", "PSYC 31a", "PSYC 32a"),
            ),
        ),
        (
            "PSYC 10a and (PSYC 31a or PSYC 32a).",
            group(
                "AND",
                "PSYC 10a",
                group("OR", "PSYC 31a", "PSYC 32a"),
            ),
        ),
        (
            "(PSYC 31a or PSYC 32a) and PSYC 51a.",
            group(
                "AND",
                group("OR", "PSYC 31a", "PSYC 32a"),
                "PSYC 51a",
            ),
        ),
        (
            "PSYC 10a or PSYC 31a and PSYC 51a.",
            group(
                "OR",
                "PSYC 10a",
                group("AND", "PSYC 31a", "PSYC 51a"),
            ),
        ),
    ],
)
def test_nested_groups_and_operator_precedence(
    text: str,
    expected: PrereqGroup,
) -> None:
    assert parse_prerequisites(text) == expected


def test_complex_nested_cosi_prerequisite() -> None:
    text = (
        "COSI 21a, COSI 104a, MATH 8a, and either MATH 22a "
        "or the combination of MATH 15a and MATH 20a."
    )

    assert parse_prerequisites(text) == group(
        "AND",
        "COSI 21a",
        "COSI 104a",
        "MATH 8a",
        group(
            "OR",
            "MATH 22a",
            group("AND", "MATH 15a", "MATH 20a"),
        ),
    )


def test_slash_separated_codes_are_jointly_required() -> None:
    result = parse_prerequisites("NBIO 140b/NBIO 240a.")

    assert result == group("AND", "NBIO 140b", "NBIO 240a")


@pytest.mark.parametrize(
    "text",
    [
        "PSYC 10a or permission of the instructor.",
        "PSYC 10a and permission of the instructor.",
        "PSYC 10a or consent of the instructor.",
        "PSYC 10a or an equivalent.",
        "PSYC 10a and at least sophomore standing.",
    ],
)
def test_non_course_clauses_do_not_become_items(text: str) -> None:
    assert parse_prerequisites(text) == group("AND", "PSYC 10a")


def test_non_prerequisite_tail_does_not_add_course_codes() -> None:
    text = "PSYC 10a. May not be taken after PSYC 51a."

    assert parse_prerequisites(text) == group("AND", "PSYC 10a")


def test_external_subject_codes_are_preserved() -> None:
    result = parse_prerequisites("PSYC 10a or MATH 10a or BIOL 14a.")

    assert result == group("OR", "PSYC 10a", "MATH 10a", "BIOL 14a")


def test_repeated_whitespace_and_newlines_are_normalized() -> None:
    text = "  PSYC 10a  \n\t and   PSYC 51a.  "

    assert parse_prerequisites(text) == group(
        "AND", "PSYC 10a", "PSYC 51a"
    )


def test_unrecognized_prose_without_codes_returns_none() -> None:
    assert parse_prerequisites("A prior programming course is recommended.") is None
