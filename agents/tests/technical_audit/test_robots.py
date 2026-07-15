from src.technical_audit.checks.robots import (
    evaluate_robots_access,
    evaluate_robots_integrity,
)
from src.technical_audit.models import AuditStatus

from helpers import make_context, page_observation, robots_observation, sitemap_observation


def _statuses(results):
    return [result.status for result in results]


def test_parseable_text_policy_passes():
    context = make_context(site_observations={"robots_txt": robots_observation()})
    (result,) = evaluate_robots_integrity(context)
    assert result.status is AuditStatus.PASS
    assert result.evidence_refs


def test_missing_robots_is_advisory_pass():
    context = make_context(
        site_observations={"robots_txt": robots_observation(status=404, body="")}
    )
    (result,) = evaluate_robots_integrity(context)
    assert result.status is AuditStatus.PASS
    assert "advisory" in result.summary


def test_html_fallback_fails():
    context = make_context(
        site_observations={
            "robots_txt": robots_observation(
                body="<!DOCTYPE html><html>not robots</html>",
                content_type="text/html",
            )
        }
    )
    (result,) = evaluate_robots_integrity(context)
    assert result.status is AuditStatus.FAIL


def test_blocked_robots_fetch_is_unknown():
    context = make_context(
        site_observations={"robots_txt": robots_observation(status=403, body="")}
    )
    (result,) = evaluate_robots_integrity(context)
    assert result.status is AuditStatus.UNKNOWN


def test_missing_evidence_is_unknown():
    context = make_context(site_observations={})
    (result,) = evaluate_robots_integrity(context)
    assert result.status is AuditStatus.UNKNOWN


def test_access_passes_when_all_crawlers_allowed():
    context = make_context(
        site_observations={
            "robots_txt": robots_observation(body="User-agent: *\nDisallow: /admin/\n"),
            "sitemaps": (sitemap_observation(),),
        }
    )
    (result,) = evaluate_robots_access(context)
    assert result.status is AuditStatus.PASS
    assert result.scope["delivery_confirmed"] is False


def test_access_fails_when_gptbot_blocked_from_public_page():
    context = make_context(
        site_observations={
            "robots_txt": robots_observation(
                body="User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
            )
        }
    )
    (result,) = evaluate_robots_access(context)
    assert result.status is AuditStatus.FAIL
    assert {"crawler": "GPTBot", "url": "https://example.com/"} in result.observed["blocked"]


def test_access_respects_longest_match_precedence():
    body = (
        "User-agent: *\n"
        "Disallow: /private\n"
        "Allow: /private/public-report\n"
    )
    pages = (
        page_observation("https://example.com/"),
        page_observation("https://example.com/private/public-report"),
    )
    context = make_context(
        pages=pages,
        site_observations={"robots_txt": robots_observation(body=body)},
    )
    (result,) = evaluate_robots_access(context)
    assert result.status is AuditStatus.PASS


def test_access_missing_robots_means_everything_allowed():
    context = make_context(
        site_observations={"robots_txt": robots_observation(status=404, body="")}
    )
    (result,) = evaluate_robots_access(context)
    assert result.status is AuditStatus.PASS


def test_access_unknown_when_robots_blocked():
    context = make_context(
        site_observations={"robots_txt": robots_observation(status=503, body="")}
    )
    (result,) = evaluate_robots_access(context)
    assert result.status is AuditStatus.UNKNOWN
