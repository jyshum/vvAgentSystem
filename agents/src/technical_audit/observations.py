from __future__ import annotations

from hashlib import sha256
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .models import Observation


def _bounded(values, *, count: int, length: int) -> list[str]:
    return [value[:length] for value in values[:count]]


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    if parts.port is not None:
        default_port = (scheme == "https" and parts.port == 443) or (
            scheme == "http" and parts.port == 80
        )
        netloc = hostname if default_port else f"{hostname}:{parts.port}"
    else:
        netloc = hostname
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def extract_page_observation(page: dict, retrieved_at: str) -> Observation:
    url = normalize_url(page["url"])
    raw_html = page.get("raw_html") or ""
    soup = BeautifulSoup(raw_html, "html.parser")
    head = soup.find("head")

    titles = []
    descriptions = []
    canonicals = []
    robots_directives = []

    if head is not None:
        titles = _bounded(
            [title.get_text(strip=True) for title in head.find_all("title")],
            count=10,
            length=500,
        )
        descriptions = _bounded([
            (meta.get("content") or "").strip()
            for meta in head.find_all("meta")
            if (meta.get("name") or "").strip().lower() == "description"
        ], count=10, length=1_000)
        canonicals = _bounded([
            urljoin(url, link.get("href") or "")
            for link in head.find_all("link")
            if "canonical" in [str(value).lower() for value in (link.get("rel") or [])]
            and (link.get("href") or "").strip()
        ], count=10, length=2_048)
        for meta in head.find_all("meta"):
            if (meta.get("name") or "").strip().lower() not in {
                "robots",
                "googlebot",
            }:
                continue
            robots_directives.extend(
                directive.strip().lower()
                for directive in (meta.get("content") or "").split(",")
                if directive.strip()
            )
        robots_directives = _bounded(robots_directives, count=50, length=100)

    content_type = (page.get("content_type") or "text/html").split(";", 1)[0].lower()
    is_html = content_type in {"text/html", "application/xhtml+xml"}

    return Observation(
        id=f"page:{url}",
        kind="page",
        subject=url,
        retrieved_at=retrieved_at,
        fingerprint=sha256(raw_html.encode("utf-8")).hexdigest(),
        data={
            "url": url,
            "available": page.get("available", True),
            "status_code": page.get("status_code", 200),
            "fetch_error": page.get("fetch_error"),
            "titles": titles,
            "meta_descriptions": descriptions,
            "canonicals": canonicals,
            "robots_directives": robots_directives,
            "h1_texts": _bounded(
                [h1.get_text(" ", strip=True) for h1 in soup.find_all("h1")],
                count=10,
                length=1_000,
            ),
            "is_html": is_html,
        },
    )
