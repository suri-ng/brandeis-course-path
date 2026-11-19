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
        raise InvalidCatalogUrl("URL must use HTTPS.")

    if parsed.hostname != "www.brandeis.edu":
        raise InvalidCatalogUrl("URL must use the www.brandeis.edu host.")

    if not SUBJECT_PATH_PATTERN.fullmatch(parsed.path):
        raise InvalidCatalogUrl("URL must point to a Brandeis subject listing.")

    if parsed.params or parsed.query or parsed.fragment:
        raise InvalidCatalogUrl("URL cannot contain parameters, a query, or a fragment.")

    return url

def validate_catalog_sources(sources: list[CatalogSource]) -> list[CatalogSource]:
    seen_keys: set[str] = set()
    seen_urls: set[str] = set()

    for source in sources:
        context = f"{source.name} ({source.url})"
        if source.key in seen_keys:
            raise InvalidCatalogUrl(f"Duplicate catalog source key {source.key!r} for {context}")
        if source.url in seen_urls:
            raise InvalidCatalogUrl(f"Duplicate catalog source URL for {context}")

        try:
            validate_catalog_url(source.url)
        except ValueError as exc:
            raise InvalidCatalogUrl(f"Invalid catalog source for {context}: {exc}") from exc

        seen_keys.add(source.key)
        seen_urls.add(source.url)

    return sources
