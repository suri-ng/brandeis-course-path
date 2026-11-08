from dataclasses import dataclass

import re
from urllib.parse import urlparse

@dataclass(frozen=True)
class CatalogSource:
    key: str
    name: str
    url: str

CATALOG_SOURCES = [
    CatalogSource(
        key="psyc",
        name="Psychology",
        url="https://www.brandeis.edu/registrar/bulletin/2026-2027/courses/subjects/5900.html",
    ),
    CatalogSource(
        key="cosi",
        name="Computer Science",
        url="https://www.brandeis.edu/registrar/bulletin/2026-2027/courses/subjects/1400.html",
    ),
]

SUBJECT_PATH_PATTERN = re.compile(
    r"^/registrar/bulletin/\d{4}-\d{4}/courses/subjects/\d+\.html"
)

class InvalidCatalogUrl(ValueError):
    pass

def validate_catalog_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.scheme != "https":
        return InvalidCatalogUrl("URL must use a HTTPS.")

    if parsed.hostname != "www.brandeis.edu":
        return InvalidCatalogUrl("URL must use www.brandeis.edu host.")

    if not SUBJECT_PATH_PATTERN.fullmatch(parsed.path):
        return InvalidCatalogUrl("URL is not in the format for Subject Listing Areas Brandeis link")

    if parsed.params or parsed.query or parsed.fragment:
        return InvalidCatalogUrl("URL should stay within the Subject Listing Areas page.")

    return url

def validate_catalog_sources(sources: list[CatalogSource]) -> list[CatalogSource]:
    seen_keys: set[str] = set()
    seen_urls: set[str] = set()

    for source in sources:
        if source.key in seen_keys:
            return ValueError(f"Duplicate catalog source key: {source.key}")
        if source.url in seen_urls:
            return ValueError(f"Duplicate catalog source url: {source.url}")

        seen_keys.add(source.key)
        seen_urls.add(source.url)

    return sources
