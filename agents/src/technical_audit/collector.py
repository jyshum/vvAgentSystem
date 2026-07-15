from __future__ import annotations

import json
import socket
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from ipaddress import ip_address
from queue import Empty, Queue
from threading import Thread
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
MAX_EXTERNAL_PROBES = 50
MAX_IMAGE_PROBES = 40
EXTERNAL_BODY_BYTES = 65_536
HTTP_PROBE_BODY_BYTES = 4_096
TIMEOUT_SECONDS = 10
RESOLVER_TIMEOUT_SECONDS = 10


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
    robots_txt: HttpEvidence | None = None
    sitemaps: tuple[HttpEvidence, ...] = ()
    tls: dict[str, Any] | None = None
    http_probe: HttpEvidence | None = None
    external_probes: tuple[HttpEvidence, ...] = ()
    image_probes: tuple[HttpEvidence, ...] = ()


FetchResult = HttpEvidence | dict[str, Any]
Fetcher = Callable[[str], FetchResult]
Resolver = Callable[[str, int], Any]


class _UnsafeRedirect(ValueError):
    pass


class _ResolverTimeout(TimeoutError):
    pass


def _redacted_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "unknown-host").lower().rstrip(".")
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        try:
            port = parts.port
        except ValueError:
            port = None
        host_port = f"{host}:{port}" if port is not None else host
        credentials = (
            "[REDACTED]@"
            if parts.username is not None or parts.password is not None
            else ""
        )
        return urlunsplit(
            (
                parts.scheme.lower(),
                f"{credentials}{host_port}",
                parts.path or "/",
                "",
                "",
            )
        )
    except Exception:
        return "[invalid URL]"


def _system_resolver(host: str, port: int) -> tuple[str, ...]:
    answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return tuple(dict.fromkeys(answer[4][0] for answer in answers))


def _resolve_with_deadline(
    resolver: Resolver,
    host: str,
    port: int,
    timeout_seconds: float,
) -> Any:
    outcome: Queue[tuple[bool, Any]] = Queue(maxsize=1)

    def resolve() -> None:
        try:
            outcome.put((True, resolver(host, port)))
        except Exception as exc:
            outcome.put((False, exc))

    # Python cannot safely cancel a running getaddrinfo/NSS call. A daemon avoids
    # making the audit caller or interpreter shutdown join a timed-out resolver.
    # The worker exits naturally if/when the underlying resolver returns.
    Thread(target=resolve, name="technical-audit-resolver", daemon=True).start()
    try:
        succeeded, value = outcome.get(timeout=timeout_seconds)
    except Empty as exc:
        raise _ResolverTimeout from exc
    if succeeded:
        return value
    raise value


def validate_public_resolution(
    url: str,
    resolver: Resolver = _system_resolver,
    resolver_timeout_seconds: float = RESOLVER_TIMEOUT_SECONDS,
) -> None:
    # This policy check intentionally runs immediately before HTTPX. HTTPX still
    # resolves the hostname for its own socket, so this validates DNS answers but
    # does not pin the connection to one of the validated addresses.
    safe_url = _redacted_url(url)
    parts = urlsplit(url)
    host = parts.hostname or ""
    try:
        port = parts.port or 443
        answers = tuple(
            _resolve_with_deadline(
                resolver,
                host,
                port,
                resolver_timeout_seconds,
            )
            or ()
        )
    except _ResolverTimeout as exc:
        deadline = f"{resolver_timeout_seconds:g}"
        raise ValueError(
            f"DNS resolution timed out after {deadline} seconds for {safe_url}"
        ) from exc
    except Exception as exc:
        raise ValueError(f"DNS resolution failed for {safe_url}") from exc
    if not answers:
        raise ValueError(f"DNS resolution failed for {safe_url}: no addresses")
    for raw_address in answers:
        try:
            address = ip_address(str(raw_address).split("%", 1)[0])
        except ValueError as exc:
            raise ValueError(
                f"DNS resolution failed for {safe_url}: invalid address"
            ) from exc
        if (
            not address.is_global
            or address.is_loopback
            or address.is_private
            or address.is_link_local
            or address.is_multicast
            or address.is_unspecified
            or address.is_reserved
        ):
            raise ValueError(
                f"DNS resolution for {safe_url} returned non-public address {address}"
            )


class _HttpxFetcher:
    def __init__(
        self,
        identity: SiteIdentity,
        *,
        resolver: Resolver = _system_resolver,
        resolver_timeout_seconds: float = RESOLVER_TIMEOUT_SECONDS,
    ) -> None:
        self._identity = identity
        self._resolver = resolver
        self._resolver_timeout_seconds = resolver_timeout_seconds
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
                "redirect target is not an allowed same-site HTTPS URL: "
                f"{_redacted_url(target)}"
            )
        validate_public_resolution(
            target,
            self._resolver,
            self._resolver_timeout_seconds,
        )

    def __call__(self, url: str) -> FetchResult:
        validate_public_resolution(
            url,
            self._resolver,
            self._resolver_timeout_seconds,
        )
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
                        error=(
                            "redirect target is not an allowed same-site HTTPS URL: "
                            f"{_redacted_url(url)}"
                        ),
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
                        error=(
                            "redirect target is not an allowed same-site HTTPS URL: "
                            f"{_redacted_url(url)}"
                        ),
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
                    error=(
                        "redirect target is not an allowed same-site HTTPS URL: "
                        f"{_redacted_url(raw_final)}"
                    ),
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
                    error=(
                        "redirect target is not an allowed same-site HTTPS URL: "
                        f"{_redacted_url(raw_target)}"
                    ),
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


def _robots_sitemap_declarations(body: str) -> list[str]:
    declared = []
    for line in body.splitlines():
        key, _, value = line.partition(":")
        if key.strip().lower() == "sitemap" and value.strip():
            declared.append(value.strip())
    return declared


def _html_assets(body: str, base_url: str) -> tuple[list[str], list[str]]:
    """Absolute external link targets and image sources from raw HTML."""
    soup = BeautifulSoup(body, "html.parser")
    links = [
        urljoin(base_url, anchor.get("href") or "")
        for anchor in soup.find_all("a")
        if (anchor.get("href") or "").strip()
    ]
    images = [
        urljoin(base_url, image.get("src") or "")
        for image in soup.find_all("img")
        if (image.get("src") or "").strip()
    ]
    return links, images


def _probe_candidate(url: str) -> str | None:
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() not in {"http", "https"}:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    if not parts.hostname:
        return None
    try:
        return _normalize_url(url)
    except ValueError:
        return None


def _fetch_unrestricted(fetcher: Fetcher, request_url: str) -> HttpEvidence:
    """Bounded fetch for external/off-site targets: no same-site rule, but the
    credential/scheme policy already filtered candidates and the live fetcher
    revalidates public resolution per hop."""
    try:
        result = fetcher(request_url)
    except Exception as exc:
        return _make_evidence(
            request_url=request_url,
            final_url=request_url,
            redirect_chain=(request_url,),
            status_code=0,
            content_type="",
            body="",
            body_truncated=False,
            error=str(exc),
        )
    chain = tuple(_raw_value(result, "redirect_chain", ()) or ()) or (request_url,)
    body, truncated = _bounded_body(_raw_value(result, "body", "") or "")
    body = body[:EXTERNAL_BODY_BYTES]
    try:
        return _make_evidence(
            request_url=request_url,
            final_url=str(_raw_value(result, "final_url", request_url) or request_url),
            redirect_chain=chain,
            status_code=_raw_value(result, "status_code", 0),
            content_type=_raw_value(result, "content_type", ""),
            body=body,
            body_truncated=truncated or bool(_raw_value(result, "body_truncated", False)),
            error=_raw_value(result, "error"),
            retrieved_at=_raw_value(result, "retrieved_at") or None,
        )
    except ValueError as exc:
        return _make_evidence(
            request_url=request_url,
            final_url=request_url,
            redirect_chain=(request_url,),
            status_code=0,
            content_type="",
            body="",
            body_truncated=False,
            error=str(exc),
        )


class _ExternalHttpxFetcher:
    """Live fetcher for external link/image probes: public-resolution checks on
    every hop, bounded bodies, no same-site restriction."""

    def __init__(
        self,
        *,
        resolver: Resolver = _system_resolver,
        resolver_timeout_seconds: float = RESOLVER_TIMEOUT_SECONDS,
    ) -> None:
        self._resolver = resolver
        self._resolver_timeout_seconds = resolver_timeout_seconds
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
        parts = urlsplit(target)
        if parts.username is not None or parts.password is not None:
            raise _UnsafeRedirect(
                f"redirect target carries credentials: {_redacted_url(target)}"
            )
        if parts.scheme.lower() not in {"http", "https"}:
            raise _UnsafeRedirect(
                f"redirect target scheme is not http(s): {_redacted_url(target)}"
            )
        validate_public_resolution(
            target, self._resolver, self._resolver_timeout_seconds
        )

    def __call__(self, url: str) -> FetchResult:
        validate_public_resolution(url, self._resolver, self._resolver_timeout_seconds)
        with self._client.stream("GET", url) as response:
            body, truncated = _bounded_body(response.iter_bytes())
            chain = tuple(str(item.url) for item in response.history) + (
                str(response.url),
            )
            return {
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "body": body[:EXTERNAL_BODY_BYTES],
                "body_truncated": truncated,
                "final_url": str(response.url),
                "redirect_chain": chain,
                "error": None,
            }

    def close(self) -> None:
        self._client.close()


def _live_http_probe(
    url: str,
    *,
    resolver: Resolver = _system_resolver,
    resolver_timeout_seconds: float = RESOLVER_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Observe plain-HTTP behavior for the configured domain without following
    past the redirect cap; bodies are capped small because only the redirect
    behavior is evidence."""
    chain = [url]
    current = url
    with httpx.Client(
        follow_redirects=False,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"},
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            validate_public_resolution(current, resolver, resolver_timeout_seconds)
            response = client.get(current)
            if not response.is_redirect:
                return {
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "body": response.text[:HTTP_PROBE_BODY_BYTES],
                    "final_url": current,
                    "redirect_chain": tuple(chain),
                    "error": None,
                }
            location = response.headers.get("location", "")
            target = urljoin(current, location)
            parts = urlsplit(target)
            if (
                parts.scheme.lower() not in {"http", "https"}
                or parts.username is not None
                or parts.password is not None
            ):
                return {
                    "status_code": response.status_code,
                    "content_type": "",
                    "body": "",
                    "final_url": current,
                    "redirect_chain": tuple(chain),
                    "error": f"unsafe redirect target: {_redacted_url(target)}",
                }
            chain.append(target)
            current = target
    return {
        "status_code": 0,
        "content_type": "",
        "body": "",
        "final_url": current,
        "redirect_chain": tuple(chain),
        "error": f"redirect limit exceeded ({MAX_REDIRECTS})",
    }


def collect_foundation(
    identity: SiteIdentity,
    max_pages: int = MAX_PAGES,
    fetcher: Fetcher | None = None,
    resolver: Resolver = _system_resolver,
    resolver_timeout_seconds: float = RESOLVER_TIMEOUT_SECONDS,
) -> CollectedSite:
    return _collect(
        identity,
        max_pages=max_pages,
        fetcher=fetcher,
        resolver=resolver,
        resolver_timeout_seconds=resolver_timeout_seconds,
        extended=False,
    )


def collect_site(
    identity: SiteIdentity,
    max_pages: int = MAX_PAGES,
    fetcher: Fetcher | None = None,
    resolver: Resolver = _system_resolver,
    resolver_timeout_seconds: float = RESOLVER_TIMEOUT_SECONDS,
    tls_inspector: Callable[[str], dict[str, Any]] | None = None,
    http_prober: Callable[[str], dict[str, Any]] | None = None,
    external_fetcher: Fetcher | None = None,
) -> CollectedSite:
    return _collect(
        identity,
        max_pages=max_pages,
        fetcher=fetcher,
        resolver=resolver,
        resolver_timeout_seconds=resolver_timeout_seconds,
        extended=True,
        tls_inspector=tls_inspector,
        http_prober=http_prober,
        external_fetcher=external_fetcher,
    )


def _collect(
    identity: SiteIdentity,
    *,
    max_pages: int,
    fetcher: Fetcher | None,
    resolver: Resolver,
    resolver_timeout_seconds: float,
    extended: bool,
    tls_inspector: Callable[[str], dict[str, Any]] | None = None,
    http_prober: Callable[[str], dict[str, Any]] | None = None,
    external_fetcher: Fetcher | None = None,
) -> CollectedSite:
    if not 1 <= max_pages <= MAX_PAGES:
        raise ValueError(f"max_pages must be between 1 and {MAX_PAGES}")
    if resolver_timeout_seconds <= 0:
        raise ValueError("resolver_timeout_seconds must be positive")

    default_fetcher = (
        _HttpxFetcher(
            identity,
            resolver=resolver,
            resolver_timeout_seconds=resolver_timeout_seconds,
        )
        if fetcher is None
        else None
    )
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
        external_candidates: list[str] = []
        external_seen: set[str] = set()
        image_candidates: list[str] = []
        image_seen: set[str] = set()

        def note_assets(body: str, base_url: str) -> None:
            if not extended:
                return
            link_urls, image_urls = _html_assets(body, base_url)
            for url in link_urls:
                candidate = _probe_candidate(url)
                candidate_host = urlsplit(candidate).hostname if candidate else None
                if (
                    candidate
                    and candidate_host
                    and candidate_host not in effective_identity.allowed_hosts
                    and candidate not in external_seen
                ):
                    external_seen.add(candidate)
                    external_candidates.append(candidate)
            for url in image_urls:
                candidate = _probe_candidate(url)
                if candidate and candidate not in image_seen:
                    image_seen.add(candidate)
                    image_candidates.append(candidate)

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
            note_assets(homepage.body, homepage.final_url)

        canonical_root = (
            homepage.final_url
            if effective_identity.allows(homepage.final_url)
            else homepage_url
        )

        robots_txt: HttpEvidence | None = None
        if extended:
            robots_txt = _fetch(
                effective_fetcher,
                effective_identity,
                urljoin(canonical_root, "/robots.txt"),
            )
            if robots_txt.status_code == 200 and robots_txt.error is None:
                declared = [
                    _normalize_url(url)
                    for url in _robots_sitemap_declarations(robots_txt.body)
                    if effective_identity.allows(url)
                ]
                sitemap_queue[:0] = declared
            conventional = urljoin(canonical_root, "/sitemap.xml")
            if conventional not in sitemap_queue:
                sitemap_queue.append(conventional)

        sitemap_documents: list[HttpEvidence] = []
        sitemaps_fetched = 0
        sitemap_seen: set[str] = set()
        while sitemap_queue and sitemaps_fetched < MAX_SITEMAPS:
            sitemap_url = sitemap_queue.pop(0)
            if sitemap_url in sitemap_seen:
                continue
            sitemap_seen.add(sitemap_url)
            sitemap = _fetch(effective_fetcher, effective_identity, sitemap_url)
            sitemaps_fetched += 1
            sitemap_documents.append(sitemap)
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
                note_assets(page.body, page.final_url)

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
            "resolver_timeout_seconds": resolver_timeout_seconds,
            "same_site_https": True,
            "concurrency_limit": 1,
        }
        if not extended:
            return CollectedSite(
                identity=effective_identity,
                homepage=homepage,
                pages=tuple(pages),
                llms_txt=llms_txt,
                scope=scope,
            )

        default_external = (
            _ExternalHttpxFetcher(
                resolver=resolver,
                resolver_timeout_seconds=resolver_timeout_seconds,
            )
            if external_fetcher is None and fetcher is None
            else None
        )
        effective_external = external_fetcher or default_external or effective_fetcher
        try:
            external_probes = tuple(
                _fetch_unrestricted(effective_external, url)
                for url in external_candidates[:MAX_EXTERNAL_PROBES]
            )
            image_probes = tuple(
                _fetch_unrestricted(effective_external, url)
                for url in image_candidates[:MAX_IMAGE_PROBES]
            )
        finally:
            if default_external is not None:
                default_external.close()

        tls_evidence: dict[str, Any] | None = None
        if tls_inspector is not None:
            tls_evidence = tls_inspector(
                (urlsplit(canonical_root).hostname or identity.configured_domain)
            )
        elif fetcher is None:
            from .evidence.tls import inspect_tls

            tls_evidence = inspect_tls(
                (urlsplit(canonical_root).hostname or identity.configured_domain)
            )

        http_probe_evidence: HttpEvidence | None = None
        bare_host = min(identity.allowed_hosts, key=len)
        http_url = f"http://{bare_host}/"
        prober = http_prober
        if prober is None and fetcher is None:
            prober = lambda url: _live_http_probe(
                url,
                resolver=resolver,
                resolver_timeout_seconds=resolver_timeout_seconds,
            )
        if prober is not None:
            try:
                probe_result = prober(http_url)
                http_probe_evidence = _make_evidence(
                    request_url=http_url,
                    final_url=str(
                        probe_result.get("final_url", http_url) or http_url
                    ),
                    redirect_chain=tuple(
                        probe_result.get("redirect_chain", (http_url,)) or (http_url,)
                    ),
                    status_code=probe_result.get("status_code", 0),
                    content_type=probe_result.get("content_type", ""),
                    body=probe_result.get("body", ""),
                    body_truncated=bool(probe_result.get("body_truncated", False)),
                    error=probe_result.get("error"),
                )
            except Exception as exc:
                http_probe_evidence = _make_evidence(
                    request_url=http_url,
                    final_url=http_url,
                    redirect_chain=(http_url,),
                    status_code=0,
                    content_type="",
                    body="",
                    body_truncated=False,
                    error=str(exc),
                )

        scope.update(
            {
                "extended": True,
                "robots_fetched": robots_txt is not None,
                "external_probe_limit": MAX_EXTERNAL_PROBES,
                "external_probes": len(external_probes),
                "external_probes_truncated": len(external_candidates)
                > MAX_EXTERNAL_PROBES,
                "image_probe_limit": MAX_IMAGE_PROBES,
                "image_probes": len(image_probes),
                "image_probes_truncated": len(image_candidates) > MAX_IMAGE_PROBES,
                "external_body_byte_limit": EXTERNAL_BODY_BYTES,
            }
        )
        return CollectedSite(
            identity=effective_identity,
            homepage=homepage,
            pages=tuple(pages),
            llms_txt=llms_txt,
            scope=scope,
            robots_txt=robots_txt,
            sitemaps=tuple(sitemap_documents),
            tls=tls_evidence,
            http_probe=http_probe_evidence,
            external_probes=external_probes,
            image_probes=image_probes,
        )
    finally:
        if default_fetcher is not None:
            default_fetcher.close()
