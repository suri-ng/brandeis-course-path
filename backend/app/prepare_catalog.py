import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from bs4 import ParserRejectedMarkup

from app.catalog_sources import (
    CATALOG_SOURCES,
    InvalidCatalogUrl,
    validate_catalog_sources,
)
from app.models import Course, CourseGraph
from app.services.course_parser import CourseParsingError, parse_courses
from app.services.graph_builder import build_course_graph
from app.services.scraper import CatalogFetchError, fetch_catalog_page, parse_catalog_html


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"


class CatalogPreparationError(RuntimeError):
    """A catalog refresh could not finish."""


def _write_catalog(graph: CourseGraph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(graph.model_dump_json(indent=2) + "\n")

        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def prepare_catalog() -> None:
    sources = validate_catalog_sources(CATALOG_SOURCES)
    if not sources:
        raise CatalogPreparationError("Configure at least one catalog source.")

    all_courses: list[Course] = []

    for source in sources:
        context = f"{source.name} ({source.url})"
        try:
            html = fetch_catalog_page(source.url)
        except CatalogFetchError as exc:
            raise CatalogPreparationError(f"Fetch failed for {source.name}: {exc}") from exc

        try:
            document = parse_catalog_html(html)
        except ParserRejectedMarkup as exc:
            raise CatalogPreparationError(f"Extraction failed for {context}: {exc}") from exc

        title = document.title.get_text(strip=True) if document.title else None

        if not title:
            raise CatalogPreparationError(
                f"Extraction failed for {context}: HTML has no page title."
            )

        print(f"Fetched page's title: {title}")

        def report_issue(message: str) -> None:
            print(f"Warning for {context}: {message}", file=sys.stderr)

        try:
            courses = parse_courses(document, report_issue=report_issue)
        except CourseParsingError as exc:
            raise CatalogPreparationError(f"Parsing failed for {context}: {exc}") from exc

        if not courses:
            raise CatalogPreparationError(
                f"Extraction failed for {context}: no courses found."
            )

        all_courses.extend(courses)
        print(f"Extracted {len(courses)} courses from {source.name}")

    graph = build_course_graph(all_courses)
    _write_catalog(graph, CATALOG_PATH)
    print(f"Wrote {CATALOG_PATH} with {len(graph.nodes)} nodes and {len(graph.edges)} edges")


def main() -> None:
    try:
        prepare_catalog()
    except (CatalogPreparationError, InvalidCatalogUrl, OSError) as exc:
        raise SystemExit(f"Catalog preparation failed: {exc}") from None


if __name__ == "__main__":
    main()
