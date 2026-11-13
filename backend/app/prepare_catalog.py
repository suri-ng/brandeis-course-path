from app.catalog_sources import(
    CATALOG_SOURCES,
    validate_catalog_url,
    validate_catalog_sources,
)

from app.services.scraper import(
    fetch_catalog_page,
    parse_catalog_html,
)

from app.services.course_parser import parse_courses

def prepare_catalog() -> None:
    sources = validate_catalog_sources(CATALOG_SOURCES)

    for source in sources:
        url = validate_catalog_url(source.url)

        html = fetch_catalog_page(url)
        document = parse_catalog_html(html) # used BeautifulSoup

        title = document.title.get_text(strip=True) if document.title else None

        if not title:
            raise RuntimeError(
                f"{source.name} returns HTML without a page title: {source.url}"
            )

        print(f"Fetched page's title: {title}")

        courses = parse_courses(document)
        print(f"Extracted {len(courses)} courses from {source.name}")
        for course in courses[:3]:
            print(course)
        # prerequisite parsing and catalog generation come next

def main() -> None:
    prepare_catalog()

if __name__ == "__main__":
    main()
