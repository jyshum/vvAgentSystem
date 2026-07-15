from src.technical_audit.collector import (
    MAX_EXTERNAL_PROBES,
    MAX_IMAGE_PROBES,
    collect_foundation,
    collect_site,
)
from src.technical_audit.site import SiteIdentity


def _response(url, *, status=200, content_type="text/html", body="", location=None):
    return {
        "status_code": status,
        "content_type": content_type,
        "body": body,
        "final_url": url,
        "redirect_location": location,
        "error": None,
    }


HOMEPAGE_BODY = (
    "<html><head>"
    '<link rel="sitemap" href="/sitemap.xml">'
    "</head><body>"
    '<a href="/about">About</a>'
    '<a href="https://external.example/report">Report</a>'
    '<img src="/hero.jpg" alt="Hero">'
    "</body></html>"
)

ROBOTS_BODY = "User-agent: *\nAllow: /\nSitemap: https://example.com/robots-sitemap.xml\n"

SITEMAP_BODY = (
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<url><loc>https://example.com/about</loc></url>"
    "</urlset>"
)


def _site_fetcher(calls=None):
    def fetcher(url):
        if calls is not None:
            calls.append(url)
        if url == "https://example.com/robots.txt":
            return _response(url, content_type="text/plain", body=ROBOTS_BODY)
        if url in {
            "https://example.com/sitemap.xml",
            "https://example.com/robots-sitemap.xml",
        }:
            return _response(url, content_type="application/xml", body=SITEMAP_BODY)
        if url == "https://example.com/llms.txt":
            return _response(url, status=404, content_type="text/plain")
        if url == "https://external.example/report":
            return _response(url, body="<html>report</html>")
        if url == "https://example.com/hero.jpg":
            return _response(url, content_type="image/jpeg", body="binary")
        return _response(url, body=HOMEPAGE_BODY)

    return fetcher


def test_collect_site_gathers_protocol_evidence():
    calls = []
    collected = collect_site(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=_site_fetcher(calls),
        tls_inspector=lambda host: {"verified": True, "host": host},
        http_prober=lambda url: {"status_code": 301, "redirect_chain": [url, "https://example.com/"], "error": None},
    )

    assert collected.robots_txt is not None
    assert collected.robots_txt.body == ROBOTS_BODY
    assert collected.robots_txt.status_code == 200

    sitemap_urls = {doc.request_url for doc in collected.sitemaps}
    assert "https://example.com/robots-sitemap.xml" in sitemap_urls
    assert "https://example.com/sitemap.xml" in sitemap_urls

    assert collected.tls == {"verified": True, "host": "example.com"}
    assert collected.http_probe is not None
    assert collected.http_probe.status_code == 301

    external = {probe.request_url for probe in collected.external_probes}
    assert external == {"https://external.example/report"}
    images = {probe.request_url for probe in collected.image_probes}
    assert images == {"https://example.com/hero.jpg"}

    assert collected.scope["extended"] is True
    assert collected.scope["external_probe_limit"] == MAX_EXTERNAL_PROBES
    assert collected.scope["image_probe_limit"] == MAX_IMAGE_PROBES


def test_collect_site_bounds_external_and_image_probes():
    anchors = "".join(
        f'<a href="https://ext-{number}.example/page">x</a>'
        for number in range(MAX_EXTERNAL_PROBES + 5)
    )
    images = "".join(
        f'<img src="/image-{number}.png" alt="">'
        for number in range(MAX_IMAGE_PROBES + 5)
    )
    body = f"<html><body>{anchors}{images}</body></html>"

    def fetcher(url):
        if url.endswith(("robots.txt", "llms.txt")):
            return _response(url, status=404, content_type="text/plain")
        if ".example/" in url or ".png" in url:
            return _response(url, content_type="image/png", body="x")
        return _response(url, body=body)

    collected = collect_site(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert len(collected.external_probes) == MAX_EXTERNAL_PROBES
    assert len(collected.image_probes) == MAX_IMAGE_PROBES
    assert collected.scope["external_probes_truncated"] is True
    assert collected.scope["image_probes_truncated"] is True


def test_collect_site_rejects_credential_and_non_http_external_targets():
    body = (
        "<html><body>"
        '<a href="https://user:pass@evil.example/">bad</a>'
        '<a href="ftp://files.example/">ftp</a>'
        '<a href="mailto:someone@example.com">mail</a>'
        '<a href="https://ok.example/">ok</a>'
        "</body></html>"
    )

    def fetcher(url):
        if url.endswith(("robots.txt", "llms.txt")):
            return _response(url, status=404, content_type="text/plain")
        return _response(url, body=body)

    collected = collect_site(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert {probe.request_url for probe in collected.external_probes} == {
        "https://ok.example/"
    }


def test_collect_site_without_live_inspectors_records_absent_evidence():
    def fetcher(url):
        if url.endswith(("robots.txt", "llms.txt")):
            return _response(url, status=404, content_type="text/plain")
        return _response(url, body="<html></html>")

    collected = collect_site(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert collected.tls is None
    assert collected.http_probe is None


def test_collect_foundation_keeps_legacy_shape():
    def fetcher(url):
        if url.endswith("llms.txt"):
            return _response(url, status=404, content_type="text/plain")
        return _response(url, body="<html></html>")

    collected = collect_foundation(
        SiteIdentity.from_domain("example.com", "other"),
        fetcher=fetcher,
    )

    assert collected.robots_txt is None
    assert collected.sitemaps == ()
    assert collected.external_probes == ()
    assert "extended" not in collected.scope
