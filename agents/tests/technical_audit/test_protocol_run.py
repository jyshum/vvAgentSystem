import pytest

from src.technical_audit.checks import build_v1_registry
from src.technical_audit.collector import collect_site
from src.technical_audit.runner import run_technical_audit
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


HOMEPAGE = (
    "<html><head><title>Example</title>"
    '<meta name="description" content="A perfectly reasonable page description here.">'
    '<link rel="canonical" href="https://example.com/">'
    '<script type="application/ld+json">{"@type": "WebSite", "name": "Example"}</script>'
    "</head><body><a href='/about'>About</a></body></html>"
)

SITEMAP = (
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<url><loc>https://example.com/</loc></url>"
    "<url><loc>https://example.com/about</loc></url>"
    "</urlset>"
)


def _fetcher(url):
    if url == "https://example.com/robots.txt":
        return _response(
            url,
            content_type="text/plain",
            body="User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n",
        )
    if url == "https://example.com/sitemap.xml":
        return _response(url, content_type="application/xml", body=SITEMAP)
    if url == "https://example.com/llms.txt":
        return _response(url, status=404, content_type="text/plain")
    if url == "https://example.com/about":
        return _response(
            url,
            body=HOMEPAGE.replace('href="https://example.com/"', 'href="https://example.com/about"'),
        )
    return _response(url, body=HOMEPAGE)


def _collect():
    identity = SiteIdentity.from_domain("example.com", "other")
    return identity, collect_site(
        identity,
        fetcher=_fetcher,
        tls_inspector=lambda host: {
            "verified": True,
            "host": host,
            "not_after": "Oct  1 12:00:00 2027 GMT",
            "unreachable": False,
            "error": None,
        },
        http_prober=lambda url: {
            "status_code": 301,
            "redirect_chain": [url, "https://example.com/"],
            "final_url": "https://example.com/",
            "error": None,
        },
    )


def test_protocol_run_produces_five_state_results_for_every_protocol_check():
    identity, collected = _collect()
    report = run_technical_audit(
        "client-1", identity, collected, enabled_check_sets=("foundation", "protocol")
    )

    check_ids = {result["check_id"] for result in report["results"]}
    assert {
        "robots_txt.integrity", "robots_txt.access",
        "sitemap.discovery", "sitemap.integrity", "sitemap.coverage",
        "sitemap.entry_health", "tls.certificate", "tls.https_redirect",
        "tls.mixed_content", "schema.integrity", "schema.coverage",
        "llms_txt.integrity", "meta_title.integrity",
    } <= check_ids

    by_id = {}
    for result in report["results"]:
        by_id.setdefault(result["check_id"], []).append(result)
    assert by_id["robots_txt.integrity"][0]["status"] == "pass"
    assert by_id["robots_txt.access"][0]["status"] == "pass"
    assert by_id["sitemap.coverage"][0]["status"] == "pass"
    assert by_id["tls.certificate"][0]["status"] == "pass"
    assert by_id["tls.https_redirect"][0]["status"] == "pass"
    assert by_id["schema.coverage"][0]["status"] == "pass"

    kinds = {observation["kind"] for observation in report["observations"]}
    assert {"page", "llms_txt", "robots_txt", "sitemap", "tls", "http_probe"} <= kinds

    for result in report["results"]:
        assert result["status"] in {"pass", "fail", "review", "unknown", "not_applicable"}
        assert result["applicability"]["reason"]
        assert "sampled" in result["scope"] or result["status"] == "not_applicable"
        assert result["next_action"]["instruction"]


def test_protocol_run_is_repeatable():
    identity, collected = _collect()
    first = run_technical_audit("c", identity, collected, ("foundation", "protocol"))
    second = run_technical_audit("c", identity, collected, ("foundation", "protocol"))
    assert [r["status"] for r in first["results"]] == [r["status"] for r in second["results"]]
    assert first["summary"] == second["summary"]


def test_registry_rejects_unknown_and_unimplemented_sets():
    with pytest.raises(ValueError):
        build_v1_registry(("nonsense",))
    with pytest.raises(ValueError):
        build_v1_registry(())
