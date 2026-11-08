# send requests to fetch the page's html -> BeautifulSoup

import requests
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT = (5,30)

HEADERS = {
    "User-Agent": (
        "BrandeisCoursePath/0.1 (catalog preparation, educational project)"
    )
}

class CatalogFetchError(RuntimeError):
    pass

def fetch_catalog_page(url: str) -> str:
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        raise CatalogFetchError(
            f"Timed out while fetching {url}"
        ) from exc
    except requests.RequestException as exc:
        raise CatalogFetchError(
            f"Cout not fetch {url}: {exc}"
        ) from exc

    return response.text # HTML string

def parse_catalog_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser") # HTML document