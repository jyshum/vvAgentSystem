from __future__ import annotations

import json
from hashlib import sha256
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .models import Observation


def _truncate_json_string(value: str, max_bytes: int) -> str:
    def encoded_size(candidate: str) -> int:
        return len(json.dumps(candidate, ensure_ascii=False).encode("utf-8")) - 2

    if encoded_size(value) <= max_bytes:
        return value
    low, high = 0, len(value)
    while low < high:
        midpoint = (low + high + 1) // 2
        if encoded_size(value[:midpoint]) <= max_bytes:
            low = midpoint
        else:
            high = midpoint - 1
    return value[:low]


def _bounded(values, *, count: int, length: int) -> list[str]:
    return [_truncate_json_string(value, length) for value in values[:count]]


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


MAX_LINKS_PER_PAGE = 200
MAX_IMAGES_PER_PAGE = 60
MAX_MIXED_CANDIDATES = 50
MAX_JSONLD_BLOCKS = 20
MAX_JSONLD_BYTES = 8_192
MAX_VISIBLE_DATES = 10

_NON_CONTENT_ANCESTORS = {"nav", "footer", "header", "aside"}
_ACTIVE_MIXED_SELECTORS = (
    ("script", "src"),
    ("iframe", "src"),
    ("img", "src"),
    ("source", "src"),
    ("video", "src"),
    ("audio", "src"),
    ("embed", "src"),
    ("object", "data"),
    ("form", "action"),
)


def _in_content(tag) -> bool:
    for parent in tag.parents:
        if parent.name in _NON_CONTENT_ANCESTORS:
            return False
    return True


def _classify_link(url: str, identity) -> str:
    if identity is None:
        return "unknown"
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    if not hostname:
        return "unknown"
    return "internal" if hostname in identity.allowed_hosts else "external"


def _extract_links(soup, base_url: str, identity) -> list[dict]:
    links = []
    for anchor in soup.find_all("a"):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue
        resolved = urljoin(base_url, href)
        scheme = urlsplit(resolved).scheme.lower()
        if scheme not in {"http", "https"}:
            continue
        links.append(
            {
                "url": _truncate_json_string(resolved, 2_048),
                "text": _truncate_json_string(
                    anchor.get_text(" ", strip=True), 300
                ),
                "rel": " ".join(anchor.get("rel") or []) or None,
                "fragment": urlsplit(resolved).fragment or None,
                "kind": _classify_link(resolved, identity),
                "in_content": _in_content(anchor),
            }
        )
        if len(links) >= MAX_LINKS_PER_PAGE:
            break
    return links


def _extract_images(soup, base_url: str) -> list[dict]:
    images = []
    for image in soup.find_all("img"):
        src = (image.get("src") or "").strip()
        if not src:
            continue
        resolved = urljoin(base_url, src)
        alt = image.get("alt")
        images.append(
            {
                "src": _truncate_json_string(resolved, 2_048),
                "alt": _truncate_json_string(alt, 500) if alt is not None else None,
                "loading": (image.get("loading") or None),
                "width": (image.get("width") or None),
                "height": (image.get("height") or None),
                "in_link": any(parent.name == "a" for parent in image.parents),
            }
        )
        if len(images) >= MAX_IMAGES_PER_PAGE:
            break
    return images


def _extract_mixed_candidates(soup, base_url: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for tag_name, attribute in _ACTIVE_MIXED_SELECTORS:
        for tag in soup.find_all(tag_name):
            if tag_name == "form" and not (tag.get(attribute) or "").strip():
                continue
            raw = (tag.get(attribute) or "").strip()
            values = [raw] if raw else []
            if tag_name == "source":
                values.extend(
                    part.strip().split(" ")[0]
                    for part in (tag.get("srcset") or "").split(",")
                    if part.strip()
                )
            for value in values:
                resolved = urljoin(base_url, value)
                if resolved.lower().startswith("http://") and resolved not in seen:
                    seen.add(resolved)
                    candidates.append(_truncate_json_string(resolved, 2_048))
                if len(candidates) >= MAX_MIXED_CANDIDATES:
                    return candidates
    for link in soup.find_all("link"):
        rel = {str(value).lower() for value in (link.get("rel") or [])}
        href = (link.get("href") or "").strip()
        if "stylesheet" in rel and href:
            resolved = urljoin(base_url, href)
            if resolved.lower().startswith("http://") and resolved not in seen:
                seen.add(resolved)
                candidates.append(_truncate_json_string(resolved, 2_048))
            if len(candidates) >= MAX_MIXED_CANDIDATES:
                break
    return candidates


def _extract_jsonld_blocks(soup) -> list[str]:
    blocks = []
    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").strip().lower()
        if script_type != "application/ld+json":
            continue
        text = (script.string or script.get_text() or "").strip()
        if text:
            blocks.append(_truncate_json_string(text, MAX_JSONLD_BYTES))
        if len(blocks) >= MAX_JSONLD_BLOCKS:
            break
    return blocks


def _extract_dates(soup) -> tuple[list[str], dict[str, str | None]]:
    visible = []
    for time_tag in soup.find_all("time"):
        value = (time_tag.get("datetime") or time_tag.get_text(strip=True) or "").strip()
        if value:
            visible.append(_truncate_json_string(value, 100))
        if len(visible) >= MAX_VISIBLE_DATES:
            break
    meta_dates: dict[str, str | None] = {"published": None, "modified": None}
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").strip().lower()
        content = (meta.get("content") or "").strip()
        if not content:
            continue
        if prop == "article:published_time" and meta_dates["published"] is None:
            meta_dates["published"] = _truncate_json_string(content, 100)
        elif prop == "article:modified_time" and meta_dates["modified"] is None:
            meta_dates["modified"] = _truncate_json_string(content, 100)
    return visible, meta_dates


MAX_OBSERVATION_DATA_BYTES = 60_000
_TRIMMABLE_LISTS = ("links", "images", "active_mixed_candidates", "jsonld_blocks")


def _bound_observation_data(data: dict) -> dict:
    """Persisted observation rows enforce a 64 KiB data limit; trim the largest
    evidence lists deterministically instead of failing the insert."""
    def size(payload: dict) -> int:
        return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    if size(data) <= MAX_OBSERVATION_DATA_BYTES:
        return data
    data = dict(data)
    data["data_truncated"] = True
    while size(data) > MAX_OBSERVATION_DATA_BYTES:
        largest = max(
            (key for key in _TRIMMABLE_LISTS if data.get(key)),
            key=lambda key: len(json.dumps(data[key], ensure_ascii=False)),
            default=None,
        )
        if largest is None:
            break
        data[largest] = data[largest][: max(len(data[largest]) // 2, 0)]
        if not data[largest]:
            data[largest] = []
    return data


def extract_page_observation(page: dict, retrieved_at: str, identity=None) -> Observation:
    url = normalize_url(page.get("final_url") or page["url"])
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

    links = _extract_links(soup, url, identity) if is_html else []
    images = _extract_images(soup, url) if is_html else []
    mixed_candidates = _extract_mixed_candidates(soup, url) if is_html else []
    jsonld_blocks = _extract_jsonld_blocks(soup) if is_html else []
    visible_dates, meta_dates = _extract_dates(soup) if is_html else ([], {"published": None, "modified": None})
    has_microdata = bool(soup.find(attrs={"itemscope": True})) if is_html else False
    has_rdfa = bool(soup.find(attrs={"typeof": True})) if is_html else False

    return Observation(
        id=f"page:{url}",
        kind="page",
        subject=url,
        retrieved_at=retrieved_at,
        fingerprint=page.get("fingerprint")
        or sha256(raw_html.encode("utf-8")).hexdigest(),
        data=_bound_observation_data({
            "url": _truncate_json_string(url, 2_048),
            "request_url": _truncate_json_string(
                normalize_url(page.get("request_url") or page["url"]), 2_048
            ),
            "final_url": _truncate_json_string(url, 2_048),
            "redirect_chain": _bounded(
                [normalize_url(item) for item in page.get("redirect_chain", (url,))],
                count=6,
                length=2_048,
            ),
            "available": page.get("available", True),
            "status_code": page.get("status_code", 200),
            "content_type": _truncate_json_string(
                str(page.get("content_type") or ""), 500
            ),
            "body_truncated": bool(page.get("body_truncated", False)),
            "fetch_error": _truncate_json_string(
                str(page.get("fetch_error") or ""), 2_000
            ) or None,
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
            "links": links,
            "images": images,
            "active_mixed_candidates": mixed_candidates,
            "jsonld_blocks": jsonld_blocks,
            "has_microdata": has_microdata,
            "has_rdfa": has_rdfa,
            "visible_dates": visible_dates,
            "meta_dates": meta_dates,
        }),
    )
