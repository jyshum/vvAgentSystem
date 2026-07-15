from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from xml.etree import ElementTree

MAX_ENTRIES_PER_DOCUMENT = 200


@dataclass(frozen=True)
class SitemapEntry:
    loc: str
    lastmod: str | None


@dataclass(frozen=True)
class SitemapDocument:
    url: str
    kind: str  # "urlset" | "index" | "invalid"
    entries: tuple[SitemapEntry, ...]
    child_locs: tuple[str, ...]
    parse_error: str | None
    entries_truncated: bool


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_sitemap(url: str, body: str) -> SitemapDocument:
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        return SitemapDocument(url, "invalid", (), (), f"XML parse error: {exc}", False)

    root_kind = _local(root.tag)
    if root_kind == "sitemapindex":
        children = []
        for element in root:
            if _local(element.tag) != "sitemap":
                continue
            for child in element:
                if _local(child.tag) == "loc" and (child.text or "").strip():
                    children.append(child.text.strip())
        return SitemapDocument(url, "index", (), tuple(children[:MAX_ENTRIES_PER_DOCUMENT]),
                               None, len(children) > MAX_ENTRIES_PER_DOCUMENT)
    if root_kind == "urlset":
        entries = []
        for element in root:
            if _local(element.tag) != "url":
                continue
            loc = None
            lastmod = None
            for child in element:
                if _local(child.tag) == "loc":
                    loc = (child.text or "").strip() or None
                elif _local(child.tag) == "lastmod":
                    lastmod = (child.text or "").strip() or None
            if loc:
                entries.append(SitemapEntry(loc, lastmod))
        return SitemapDocument(url, "urlset", tuple(entries[:MAX_ENTRIES_PER_DOCUMENT]), (),
                               None, len(entries) > MAX_ENTRIES_PER_DOCUMENT)
    return SitemapDocument(url, "invalid", (), (), f"unexpected root element <{root_kind}>", False)


def parse_lastmod(value: str) -> datetime | None:
    """W3C datetime forms used by sitemaps; None when unparseable."""
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
