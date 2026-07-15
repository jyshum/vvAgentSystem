from src.technical_audit.collector import MAX_BODY_BYTES, collect_foundation
from src.technical_audit.site import SiteIdentity


def _response(
    url,
    *,
    status=200,
    content_type="text/html",
    body="",
    location=None,
):
    return {
        "status_code": status,
        "content_type": content_type,
        "body": body,
        "final_url": url,
        "redirect_location": location,
        "error": None,
    }


def test_collection_follows_bare_domain_and_bounds_sitemap_and_nav_pages():
    bare = "https://budgetyourmd.ca/"
    www = "https://www.budgetyourmd.ca/"
    sitemap = "https://www.budgetyourmd.ca/sitemap.xml"
    calls = []
    homepage_body = (
        '<html><head><link rel="sitemap" href="/sitemap.xml"></head>'
        '<body><a href="/page-1">Page 1</a></body></html>'
    )
    sitemap_body = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(
            f"<url><loc>https://www.budgetyourmd.ca/page-{number}</loc></url>"
            for number in range(1, 22)
        )
        + "</urlset>"
    )

    def fetcher(url):
        calls.append(url)
        if url == bare:
            return _response(url, status=301, location=www)
        if url == www:
            return _response(url, body=homepage_body)
        if url == sitemap:
            return _response(
                url,
                content_type="application/xml",
                body=sitemap_body,
            )
        if url == "https://www.budgetyourmd.ca/page-7":
            return _response(url, status=403, body="Forbidden")
        if url.startswith("https://www.budgetyourmd.ca/page-"):
            return _response(
                url,
                body=f"<html><head><title>{url}</title></head></html>",
            )
        if url == "https://www.budgetyourmd.ca/llms.txt":
            return _response(url, status=404, content_type="text/plain")
        raise AssertionError(f"unexpected URL: {url}")

    collected = collect_foundation(
        SiteIdentity.from_domain("budgetyourmd.ca", "squarespace"),
        fetcher=fetcher,
    )

    assert collected.homepage.final_url == www
    assert len(collected.pages) == 20
    assert collected.pages[0].redirect_chain == (bare, www)
    assert collected.scope["truncated"] is True
    assert collected.scope["max_pages"] == 20
    assert collected.scope["body_byte_limit"] == MAX_BODY_BYTES
    assert collected.scope["redirect_limit"] == 5
    assert collected.scope["timeout_seconds"] == 10
    assert collected.identity.allowed_hosts == frozenset(
        {"budgetyourmd.ca", "www.budgetyourmd.ca"}
    )
    assert "https://www.budgetyourmd.ca/page-20" not in calls
    blocked = next(
        page
        for page in collected.pages
        if page.request_url == "https://www.budgetyourmd.ca/page-7"
    )
    assert blocked.status_code == 403
    assert blocked.error is None
    assert blocked.body == "Forbidden"
    for evidence in (*collected.pages, collected.llms_txt):
        assert evidence.retrieved_at.endswith("+00:00")
        assert len(evidence.fingerprint) == 64


def test_collection_rejects_unsafe_redirect_without_fetching_destination():
    calls = []

    def fetcher(url):
        calls.append(url)
        return _response(
            url,
            status=302,
            location="https://attacker.example/internal",
        )

    collected = collect_foundation(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert calls == ["https://example.com/", "https://example.com/llms.txt"]
    assert collected.homepage.status_code == 302
    assert "not an allowed same-site HTTPS URL" in collected.homepage.error
    assert collected.pages == (collected.homepage,)


def test_collection_rejects_credential_bearing_redirect_before_normalization():
    calls = []

    def fetcher(url):
        calls.append(url)
        return _response(
            url,
            status=302,
            location="https://user:secret@example.com/private",
        )

    collected = collect_foundation(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert calls == ["https://example.com/", "https://example.com/llms.txt"]
    assert "not an allowed same-site HTTPS URL" in collected.homepage.error
    assert all("secret" not in url for url in collected.homepage.redirect_chain)


def test_collection_enforces_five_redirect_limit():
    calls = []

    def fetcher(url):
        calls.append(url)
        path = url.removeprefix("https://example.com/")
        step = int(path.removeprefix("redirect-")) if path else 0
        if step < 6:
            return _response(
                url,
                status=302,
                location=f"https://example.com/redirect-{step + 1}",
            )
        return _response(url, body="<html></html>")

    collected = collect_foundation(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert calls[:6] == [
        "https://example.com/",
        "https://example.com/redirect-1",
        "https://example.com/redirect-2",
        "https://example.com/redirect-3",
        "https://example.com/redirect-4",
        "https://example.com/redirect-5",
    ]
    assert "https://example.com/redirect-6" not in calls
    assert collected.homepage.error == "redirect limit exceeded (5)"
    assert len(collected.homepage.redirect_chain) == 6


def test_collection_caps_response_body_and_fingerprint_is_deterministic(monkeypatch):
    timestamp = "2026-07-15T12:00:00+00:00"
    monkeypatch.setattr(
        "src.technical_audit.collector._retrieved_at",
        lambda: timestamp,
    )

    def fetcher(url):
        if url.endswith("/llms.txt"):
            return _response(url, status=404, content_type="text/plain")
        return _response(url, body="x" * (MAX_BODY_BYTES + 10))

    identity = SiteIdentity.from_domain("example.com", "other")
    first = collect_foundation(identity, fetcher=fetcher)
    second = collect_foundation(identity, fetcher=fetcher)

    assert len(first.homepage.body.encode("utf-8")) == MAX_BODY_BYTES
    assert first.homepage.body_truncated is True
    assert first.homepage.retrieved_at == timestamp
    assert first.homepage.fingerprint == second.homepage.fingerprint


def test_collection_body_cap_is_strict_for_multibyte_utf8():
    oversized = "abc" + ("🧪" * MAX_BODY_BYTES)

    def fetcher(url):
        if url.endswith("/llms.txt"):
            return _response(url, status=404, content_type="text/plain")
        return _response(url, body=oversized)

    collected = collect_foundation(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert len(collected.homepage.body.encode("utf-8")) <= MAX_BODY_BYTES
    assert collected.homepage.body_truncated is True


def test_collection_ignores_malformed_sitemap_locations_and_keeps_collecting():
    homepage = (
        '<html><head><link rel="sitemap" href="/sitemap.xml"></head>'
        '<body><a href="/valid">Valid</a></body></html>'
    )
    sitemap = (
        "<urlset>"
        "<url><loc>https://example.com:invalid/private</loc></url>"
        "<url><loc>https://example.com/from-sitemap</loc></url>"
        "</urlset>"
    )

    def fetcher(url):
        if url == "https://example.com/":
            return _response(url, body=homepage)
        if url == "https://example.com/sitemap.xml":
            return _response(url, content_type="application/xml", body=sitemap)
        if url == "https://example.com/llms.txt":
            return _response(url, status=404, content_type="text/plain")
        return _response(url, body="<html></html>")

    collected = collect_foundation(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert [page.request_url for page in collected.pages] == [
        "https://example.com/",
        "https://example.com/valid",
        "https://example.com/from-sitemap",
    ]


def test_collection_fetches_at_most_three_linked_sitemaps():
    homepage = "<html><head>" + "".join(
        f'<link rel="sitemap" href="/sitemap-{number}.xml">'
        for number in range(1, 5)
    ) + "</head></html>"
    calls = []

    def fetcher(url):
        calls.append(url)
        if url == "https://example.com/":
            return _response(url, body=homepage)
        if url == "https://example.com/llms.txt":
            return _response(url, status=404, content_type="text/plain")
        return _response(url, content_type="application/xml", body="<urlset />")

    collected = collect_foundation(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert collected.scope["sitemaps_fetched"] == 3
    assert "https://example.com/sitemap-4.xml" not in calls
    assert collected.scope["truncated"] is True


def test_collection_rejects_invalid_page_limit_before_fetching():
    calls = []

    try:
        collect_foundation(
            SiteIdentity.from_domain("example.com", "other"),
            max_pages=0,
            fetcher=lambda url: calls.append(url),
        )
    except ValueError as exc:
        assert str(exc) == "max_pages must be between 1 and 20"
    else:
        raise AssertionError("expected ValueError")

    assert calls == []
