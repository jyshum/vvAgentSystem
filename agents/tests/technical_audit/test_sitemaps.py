from src.technical_audit.checks.sitemap import (
    evaluate_sitemap_coverage,
    evaluate_sitemap_discovery,
    evaluate_sitemap_entry_health,
    evaluate_sitemap_integrity,
)
from src.technical_audit.evidence.sitemaps import parse_sitemap
from src.technical_audit.models import AuditStatus

from helpers import make_context, page_observation, sitemap_observation


def test_parse_sitemap_urlset_index_and_invalid():
    urlset = parse_sitemap(
        "https://example.com/sitemap.xml",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://example.com/a</loc><lastmod>2026-01-01</lastmod></url>"
        "</urlset>",
    )
    assert urlset.kind == "urlset"
    assert urlset.entries[0].loc == "https://example.com/a"
    assert urlset.entries[0].lastmod == "2026-01-01"

    index = parse_sitemap(
        "https://example.com/sitemap.xml",
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<sitemap><loc>https://example.com/pages.xml</loc></sitemap>"
        "</sitemapindex>",
    )
    assert index.kind == "index"
    assert index.child_locs == ("https://example.com/pages.xml",)

    invalid = parse_sitemap("https://example.com/sitemap.xml", "<html>nope")
    assert invalid.kind == "invalid"
    assert invalid.parse_error


def test_discovery_pass_review_unknown():
    healthy = make_context(site_observations={"sitemaps": (sitemap_observation(),)})
    assert evaluate_sitemap_discovery(healthy)[0].status is AuditStatus.PASS

    absent = make_context(
        site_observations={"sitemaps": (sitemap_observation(status=404, kind="invalid"),)}
    )
    assert evaluate_sitemap_discovery(absent)[0].status is AuditStatus.REVIEW

    blocked = make_context(
        site_observations={"sitemaps": (sitemap_observation(status=403, kind="invalid"),)}
    )
    assert evaluate_sitemap_discovery(blocked)[0].status is AuditStatus.UNKNOWN


def test_integrity_fails_on_html_fallback_and_foreign_urls():
    html_fallback = make_context(
        site_observations={
            "sitemaps": (
                sitemap_observation(
                    kind="invalid", parse_error="XML parse error", content_type="text/html"
                ),
            )
        }
    )
    assert evaluate_sitemap_integrity(html_fallback)[0].status is AuditStatus.FAIL

    foreign = make_context(
        site_observations={
            "sitemaps": (
                sitemap_observation(entries=[{"loc": "https://other.example/x", "lastmod": None}]),
            )
        }
    )
    result = evaluate_sitemap_integrity(foreign)[0]
    assert result.status is AuditStatus.FAIL
    assert "host scope" in str(result.observed)


def test_integrity_validates_lastmod_only_when_present():
    future = make_context(
        site_observations={
            "sitemaps": (
                sitemap_observation(
                    entries=[{"loc": "https://example.com/a", "lastmod": "2030-01-01"}]
                ),
            )
        }
    )
    assert evaluate_sitemap_integrity(future)[0].status is AuditStatus.FAIL

    absent = make_context(
        site_observations={
            "sitemaps": (
                sitemap_observation(entries=[{"loc": "https://example.com/a", "lastmod": None}]),
            )
        }
    )
    assert evaluate_sitemap_integrity(absent)[0].status is AuditStatus.PASS


def test_integrity_not_applicable_without_documents():
    context = make_context(site_observations={})
    assert evaluate_sitemap_integrity(context)[0].status is AuditStatus.NOT_APPLICABLE


def test_coverage_homepage_missing_fails():
    context = make_context(
        site_observations={
            "sitemaps": (
                sitemap_observation(entries=[{"loc": "https://example.com/other", "lastmod": None}]),
            )
        }
    )
    assert evaluate_sitemap_coverage(context)[0].status is AuditStatus.FAIL


def test_coverage_missing_collected_page_is_review():
    pages = (
        page_observation("https://example.com/"),
        page_observation("https://example.com/about"),
    )
    context = make_context(
        pages=pages,
        site_observations={
            "sitemaps": (
                sitemap_observation(entries=[{"loc": "https://example.com/", "lastmod": None}]),
            )
        },
    )
    result = evaluate_sitemap_coverage(context)[0]
    assert result.status is AuditStatus.REVIEW
    assert "https://example.com/about" in result.observed["collected_pages_missing"]


def test_coverage_pass_when_all_listed():
    context = make_context(
        site_observations={
            "sitemaps": (
                sitemap_observation(entries=[{"loc": "https://example.com/", "lastmod": None}]),
            )
        }
    )
    assert evaluate_sitemap_coverage(context)[0].status is AuditStatus.PASS


def test_entry_health_redirected_entry_fails():
    pages = (
        page_observation("https://example.com/"),
        page_observation(
            "https://example.com/moved",
            redirect_chain=["https://example.com/moved", "https://example.com/new"],
        ),
    )
    context = make_context(
        pages=pages,
        site_observations={
            "sitemaps": (
                sitemap_observation(
                    entries=[
                        {"loc": "https://example.com/", "lastmod": None},
                        {"loc": "https://example.com/moved", "lastmod": None},
                    ]
                ),
            )
        },
    )
    result = evaluate_sitemap_entry_health(context)[0]
    assert result.status is AuditStatus.FAIL
    assert result.scope["sampled"] is True


def test_entry_health_blocked_entry_is_unknown():
    pages = (
        page_observation("https://example.com/", status_code=429, available=False),
    )
    context = make_context(
        pages=pages,
        site_observations={
            "sitemaps": (
                sitemap_observation(entries=[{"loc": "https://example.com/", "lastmod": None}]),
            )
        },
    )
    assert evaluate_sitemap_entry_health(context)[0].status is AuditStatus.UNKNOWN


def test_entry_health_pass_and_not_applicable():
    context = make_context(
        site_observations={
            "sitemaps": (
                sitemap_observation(entries=[{"loc": "https://example.com/", "lastmod": None}]),
            )
        }
    )
    assert evaluate_sitemap_entry_health(context)[0].status is AuditStatus.PASS

    empty = make_context(site_observations={})
    assert evaluate_sitemap_entry_health(empty)[0].status is AuditStatus.NOT_APPLICABLE
