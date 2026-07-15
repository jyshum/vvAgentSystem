from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from .site import SiteIdentity


MAX_BODY_BYTES = 512_000
MAX_REDIRECTS = 5
MAX_PAGES = 20
MAX_SITEMAPS = 3
TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class HttpEvidence:
    request_url: str
    final_url: str
    redirect_chain: tuple[str, ...]
    status_code: int
    content_type: str
    body: str
    body_truncated: bool
    error: str | None
    retrieved_at: str = ""
    fingerprint: str = ""


@dataclass(frozen=True)
class CollectedSite:
    identity: SiteIdentity
    homepage: HttpEvidence
    pages: tuple[HttpEvidence, ...]
    llms_txt: HttpEvidence
    scope: dict[str, Any]


FetchResult = HttpEvidence | dict[str, Any]
Fetcher = Callable[[str], FetchResult]


class _UnsafeRedirect(ValueError):
    pass


class _HttpxFetcher:
    def __init__(self, identity: SiteIdentity) -> None:
        self._identity = identity
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=TIMEOUT_SECONDS,
            max_redirects=MAX_REDIRECTS,
            headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"},
            event_hooks={"response": [self._validate_redirect]},
        )

    def _validate_redirect(self, response: httpx.Response) -> None:
        location = response.headers.get("location")
        if not response.is_redirect or not location:
            return
        target = urljoin(str(response.url), location)
        if not self._identity.allows(target):
            raise _UnsafeRedirect(
                f"redirect target is not an allowed same-site HTTPS URL: {target}"
            )

    def __call__(self, url: str) -> FetchResult:
        with self._client.stream("GET", url) as response:
            body, truncated = _bounded_body(response.iter_bytes())
            chain = tuple(str(item.url) for item in response.history) + (
                str(response.url),
            )
            return {
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "body": body,
                "body_truncated": truncated,
                "final_url": str(response.url),
                "redirect_chain": chain,
                "error": None,
            }

    def close(self) -> None:
        self._client.close()


def _retrieved_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bounded_body(value: Any) -> tuple[str, bool]:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
    else:
        collected = bytearray()
        truncated = False
        for chunk in value:
            chunk_bytes = chunk.encode("utf-8") if isinstance(chunk, str) else bytes(chunk)
            remaining = MAX_BODY_BYTES - len(collected)
            if remaining <= 0:
                truncated = True
                break
            collected.extend(chunk_bytes[:remaining])
            if len(chunk_bytes) > remaining:
                truncated = True
                break
        return collected.decode("utf-8", errors="ignore"), truncated
    return (
        raw[:MAX_BODY_BYTES].decode("utf-8", errors="ignore"),
        len(raw) > MAX_BODY_BYTES,
    )


def _normalize_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.username is not None or parts.password is not None:
        raise ValueError("credential-bearing URLs are not allowed")
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower().rstrip(".")
    port = "" if parts.port in {None, 443} else f":{parts.port}"
    path = parts.path or "/"
    return urlunsplit((scheme, f"{host}{port}", path, parts.query, ""))


def _fingerprint(evidence: HttpEvidence) -> str:
    payload = asdict(evidence)
    payload.pop("retrieved_at", None)
    payload.pop("fingerprint", None)
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _raw_value(result: FetchResult, key: str, default: Any = None) -> Any:
    if isinstance(result, HttpEvidence):
        return getattr(result, key, default)
    return result.get(key, default)


def _make_evidence(
    *,
    request_url: str,
    final_url: str,
    redirect_chain: tuple[str, ...],
    status_code: int,
    content_type: str,
    body: Any,
    body_truncated: bool,
    error: str | None,
    retrieved_at: str | None = None,
) -> HttpEvidence:
    bounded_body, truncated = _bounded_body(body or "")
    evidence = HttpEvidence(
        request_url=_normalize_url(request_url),
        final_url=_normalize_url(final_url),
        redirect_chain=tuple(_normalize_url(url) for url in redirect_chain),
        status_code=int(status_code or 0),
        content_type=str(content_type or ""),
        body=bounded_body,
        body_truncated=bool(body_truncated or truncated),
        error=str(error) if error else None,
        retrieved_at=retrieved_at or _retrieved_at(),
    )
    return HttpEvidence(**{**asdict(evidence), "fingerprint": _fingerprint(evidence)})


def _fetch(fetcher: Fetcher, identity: SiteIdentity, request_url: str) -> HttpEvidence:
    request_url = _normalize_url(request_url)
    chain = [request_url]
    current_url = request_url

    if not identity.allows(current_url):
        return _make_evidence(
            request_url=request_url,
            final_url=current_url,
            redirect_chain=tuple(chain),
            status_code=0,
            content_type="",
            body="",
            body_truncated=False,
            error=f"URL is not an allowed same-site HTTPS URL: {current_url}",
        )

    while True:
        try:
            result = fetcher(current_url)
        except Exception as exc:
            return _make_evidence(
                request_url=request_url,
                final_url=current_url,
                redirect_chain=tuple(chain),
                status_code=0,
                content_type="",
                body="",
                body_truncated=False,
                error=str(exc),
            )

        result_chain = tuple(_raw_value(result, "redirect_chain", ()) or ())
        raw_final = str(_raw_value(result, "final_url", current_url) or current_url)
        if result_chain:
            for url in result_chain:
                if not identity.allows(url):
                    return _make_evidence(
                        request_url=request_url,
                        final_url=current_url,
                        redirect_chain=tuple(chain),
                        status_code=_raw_value(result, "status_code", 0),
                        content_type=_raw_value(result, "content_type", ""),
                        body="",
                        body_truncated=False,
                        error=f"redirect target is not an allowed same-site HTTPS URL: {url}",
                    )
            normalized_result_chain = [_normalize_url(url) for url in result_chain]
            if normalized_result_chain[0] != current_url:
                normalized_result_chain.insert(0, current_url)
            for url in normalized_result_chain:
                if not identity.allows(url):
                    return _make_evidence(
                        request_url=request_url,
                        final_url=url,
                        redirect_chain=tuple([*chain[:-1], *normalized_result_chain]),
                        status_code=_raw_value(result, "status_code", 0),
                        content_type=_raw_value(result, "content_type", ""),
                        body="",
                        body_truncated=False,
                        error=f"redirect target is not an allowed same-site HTTPS URL: {url}",
                    )
            combined_chain = [*chain[:-1], *normalized_result_chain]
            if len(combined_chain) - 1 > MAX_REDIRECTS:
                return _make_evidence(
                    request_url=request_url,
                    final_url=combined_chain[MAX_REDIRECTS],
                    redirect_chain=tuple(combined_chain[: MAX_REDIRECTS + 1]),
                    status_code=_raw_value(result, "status_code", 0),
                    content_type=_raw_value(result, "content_type", ""),
                    body="",
                    body_truncated=False,
                    error=f"redirect limit exceeded ({MAX_REDIRECTS})",
                )
            chain = combined_chain
            current_url = chain[-1]
            raw_final = current_url
        elif raw_final != current_url:
            if not identity.allows(raw_final):
                return _make_evidence(
                    request_url=request_url,
                    final_url=current_url,
                    redirect_chain=tuple(chain),
                    status_code=_raw_value(result, "status_code", 0),
                    content_type=_raw_value(result, "content_type", ""),
                    body="",
                    body_truncated=False,
                    error=f"redirect target is not an allowed same-site HTTPS URL: {raw_final}",
                )
            final_url = _normalize_url(raw_final)
            if final_url != current_url:
                chain.append(final_url)
                current_url = final_url

        status_code = int(_raw_value(result, "status_code", 0) or 0)
        location = _raw_value(result, "redirect_location") or _raw_value(
            result, "location"
        )
        if 300 <= status_code < 400 and location and not result_chain:
            raw_target = urljoin(current_url, str(location))
            if not identity.allows(raw_target):
                return _make_evidence(
                    request_url=request_url,
                    final_url=current_url,
                    redirect_chain=tuple(chain),
                    status_code=status_code,
                    content_type=_raw_value(result, "content_type", ""),
                    body=_raw_value(result, "body", ""),
                    body_truncated=bool(_raw_value(result, "body_truncated", False)),
                    error=f"redirect target is not an allowed same-site HTTPS URL: {raw_target}",
                )
            target = _normalize_url(raw_target)
            if len(chain) - 1 >= MAX_REDIRECTS:
                return _make_evidence(
                    request_url=request_url,
                    final_url=current_url,
                    redirect_chain=tuple(chain),
                    status_code=status_code,
                    content_type=_raw_value(result, "content_type", ""),
                    body=_raw_value(result, "body", ""),
                    body_truncated=bool(_raw_value(result, "body_truncated", False)),
                    error=f"redirect limit exceeded ({MAX_REDIRECTS})",
                )
            chain.append(target)
            current_url = target
            continue

        return _make_evidence(
            request_url=request_url,
            final_url=current_url,
            redirect_chain=tuple(chain),
            status_code=status_code,
            content_type=_raw_value(result, "content_type", ""),
            body=_raw_value(result, "body", ""),
            body_truncated=bool(_raw_value(result, "body_truncated", False)),
            error=_raw_value(result, "error"),
            retrieved_at=_raw_value(result, "retrieved_at") or None,
        )


def _is_html(evidence: HttpEvidence) -> bool:
    mime = evidence.content_type.split(";", 1)[0].strip().lower()
    return (
        evidence.error is None
        and evidence.status_code == 200
        and mime in {"text/html", "application/xhtml+xml"}
    )


def _html_discovery(body: str, base_url: str) -> tuple[list[str], list[str]]:
    soup = BeautifulSoup(body, "html.parser")
    pages = [urljoin(base_url, anchor.get("href") or "") for anchor in soup.find_all("a")]
    sitemaps = []
    for link in soup.find_all("link"):
        rel = {str(item).lower() for item in (link.get("rel") or [])}
        href = link.get("href") or ""
        if "sitemap" in rel and href:
            sitemaps.append(urljoin(base_url, href))
    return pages, sitemaps


def _sitemap_locations(body: str) -> list[str]:
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        return []
    return [
        (element.text or "").strip()
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1].lower() == "loc"
        and (element.text or "").strip()
    ]


def collect_foundation(
    identity: SiteIdentity,
    max_pages: int = MAX_PAGES,
    fetcher: Fetcher | None = None,
) -> CollectedSite:
    if not 1 <= max_pages <= MAX_PAGES:
        raise ValueError(f"max_pages must be between 1 and {MAX_PAGES}")

    default_fetcher = _HttpxFetcher(identity) if fetcher is None else None
    effective_fetcher = fetcher or default_fetcher
    assert effective_fetcher is not None

    try:
        homepage_url = f"https://{identity.configured_domain}/"
        homepage = _fetch(effective_fetcher, identity, homepage_url)
        effective_identity = identity
        if identity.allows(homepage.final_url):
            effective_identity = identity.with_final_homepage(homepage.final_url)

        pages = [homepage]
        queued: list[str] = []
        queued_set: set[str] = set()
        visited = {homepage.request_url, homepage.final_url}
        sitemap_queue: list[str] = []

        def queue_page(url: str) -> None:
            try:
                normalized = _normalize_url(url)
            except ValueError:
                return
            if (
                effective_identity.allows(normalized)
                and normalized not in visited
                and normalized not in queued_set
            ):
                queued.append(normalized)
                queued_set.add(normalized)

        if _is_html(homepage):
            discovered_pages, discovered_sitemaps = _html_discovery(
                homepage.body, homepage.final_url
            )
            for url in discovered_pages:
                queue_page(url)
            sitemap_queue.extend(
                _normalize_url(url)
                for url in discovered_sitemaps
                if effective_identity.allows(url)
            )

        sitemaps_fetched = 0
        sitemap_seen: set[str] = set()
        while sitemap_queue and sitemaps_fetched < MAX_SITEMAPS:
            sitemap_url = sitemap_queue.pop(0)
            if sitemap_url in sitemap_seen:
                continue
            sitemap_seen.add(sitemap_url)
            sitemap = _fetch(effective_fetcher, effective_identity, sitemap_url)
            sitemaps_fetched += 1
            for url in _sitemap_locations(sitemap.body):
                try:
                    normalized = _normalize_url(url)
                except ValueError:
                    continue
                if normalized.lower().endswith(".xml"):
                    if effective_identity.allows(normalized):
                        sitemap_queue.append(normalized)
                else:
                    queue_page(normalized)

        while queued and len(pages) < max_pages:
            page_url = queued.pop(0)
            queued_set.discard(page_url)
            visited.add(page_url)
            page = _fetch(effective_fetcher, effective_identity, page_url)
            pages.append(page)
            visited.add(page.final_url)
            if _is_html(page):
                discovered_pages, _ = _html_discovery(page.body, page.final_url)
                for url in discovered_pages:
                    queue_page(url)

        canonical_root = homepage.final_url if effective_identity.allows(homepage.final_url) else homepage_url
        llms_url = urljoin(canonical_root, "/llms.txt")
        llms_txt = _fetch(effective_fetcher, effective_identity, llms_url)
        truncated = bool(queued or sitemap_queue)
        scope = {
            "max_pages": max_pages,
            "pages_collected": len(pages),
            "truncated": truncated,
            "body_byte_limit": MAX_BODY_BYTES,
            "redirect_limit": MAX_REDIRECTS,
            "sitemap_limit": MAX_SITEMAPS,
            "sitemaps_fetched": sitemaps_fetched,
            "timeout_seconds": TIMEOUT_SECONDS,
            "same_site_https": True,
            "concurrency_limit": 1,
        }
        return CollectedSite(
            identity=effective_identity,
            homepage=homepage,
            pages=tuple(pages),
            llms_txt=llms_txt,
            scope=scope,
        )
    finally:
        if default_fetcher is not None:
            default_fetcher.close()
