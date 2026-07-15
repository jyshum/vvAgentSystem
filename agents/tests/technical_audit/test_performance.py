from src.technical_audit.checks.integrations import evaluate_bing, evaluate_gsc_sitemap
from src.technical_audit.checks.performance import (
    evaluate_crux,
    evaluate_lcp_image,
    evaluate_lighthouse,
)
from src.technical_audit.evidence.performance import fetch_crux, fetch_psi
from src.technical_audit.models import AuditStatus

from helpers import make_context, sitemap_observation


def _crux_record(lcp=2000.0, inp=150.0, cls=0.05, **extra):
    return {
        "subject": "https://example.com/",
        "origin_fallback": False,
        "metrics": {"lcp_ms": lcp, "inp_ms": inp, "cls": cls},
        **extra,
    }


def test_fetch_crux_page_origin_fallback_and_insufficient():
    def post(url, payload):
        if "url" in payload:
            return {"status_code": 404, "json": {}}
        return {
            "status_code": 200,
            "json": {"record": {"metrics": {
                "largest_contentful_paint": {"percentiles": {"p75": 2400}},
                "interaction_to_next_paint": {"percentiles": {"p75": 180}},
                "cumulative_layout_shift": {"percentiles": {"p75": "0.08"}},
            }}},
        }

    record = fetch_crux("https://example.com/page", "key", http_post=post)
    assert record["origin_fallback"] is True
    assert record["metrics"]["lcp_ms"] == 2400.0
    assert record["metrics"]["cls"] == 0.08

    always_404 = lambda url, payload: {"status_code": 404, "json": {}}
    assert fetch_crux("https://example.com/", "key", http_post=always_404)["insufficient_data"] is True


def test_fetch_psi_median_of_three_runs():
    scores = iter([0.52, 0.91, 0.66])

    def get(url, params):
        return {
            "status_code": 200,
            "json": {"lighthouseResult": {
                "categories": {"performance": {"score": next(scores)}},
                "lighthouseVersion": "12.0.0",
                "fetchTime": "2026-07-15T12:00:00Z",
                "configSettings": {"throttlingMethod": "simulate"},
                "audits": {
                    "total-blocking-time": {"numericValue": 300},
                    "lcp-lazy-loaded": {"score": 1},
                },
            }},
        }

    record = fetch_psi("https://example.com/", "key", http_get=get)
    assert record["runs"] == 3
    assert record["run_scores"] == [52, 91, 66]
    assert record["median_score"] == 66
    assert record["lighthouse_version"] == "12.0.0"


def test_crux_thresholds():
    passing = make_context(integrations={"crux": [_crux_record()]})
    assert evaluate_crux(passing)[0].status is AuditStatus.PASS

    review = make_context(integrations={"crux": [_crux_record(lcp=3000.0)]})
    assert evaluate_crux(review)[0].status is AuditStatus.REVIEW

    failing = make_context(integrations={"crux": [_crux_record(inp=600.0)]})
    result = evaluate_crux(failing)[0]
    assert result.status is AuditStatus.FAIL
    assert "inp_ms" in result.summary

    insufficient = make_context(
        integrations={"crux": [{"subject": "https://example.com/", "insufficient_data": True}]}
    )
    assert evaluate_crux(insufficient)[0].status is AuditStatus.UNKNOWN

    unconfigured = make_context()
    result = evaluate_crux(unconfigured)[0]
    assert result.status is AuditStatus.UNKNOWN
    assert result.next_action.owner == "integration"


def test_crux_origin_fallback_is_labelled():
    context = make_context(
        integrations={"crux": [_crux_record(origin_fallback=True)]}
    )
    result = evaluate_crux(context)[0]
    assert result.scope["level"] == "origin"
    assert "origin-level" in result.summary


def _psi_record(score, lazy=None):
    return {
        "subject": "https://example.com/",
        "runs": 3,
        "run_scores": [score - 2, score, score + 3],
        "median_score": score,
        "lighthouse_version": "12.0.0",
        "device": "mobile",
        "lcp_lazy_score": lazy,
    }


def test_lighthouse_bands_and_unknown():
    assert evaluate_lighthouse(make_context(integrations={"psi": [_psi_record(93)]}))[0].status is AuditStatus.PASS
    review = evaluate_lighthouse(make_context(integrations={"psi": [_psi_record(70)]}))[0]
    assert review.status is AuditStatus.REVIEW
    assert review.observed["label"] == "external lab diagnostic"
    assert evaluate_lighthouse(make_context(integrations={"psi": [_psi_record(40)]}))[0].status is AuditStatus.FAIL
    assert evaluate_lighthouse(make_context())[0].status is AuditStatus.UNKNOWN


def test_lcp_image_rules():
    lazy = evaluate_lcp_image(make_context(integrations={"psi": [_psi_record(90, lazy=0)]}))[0]
    assert lazy.status is AuditStatus.FAIL
    eager = evaluate_lcp_image(make_context(integrations={"psi": [_psi_record(90, lazy=1)]}))[0]
    assert eager.status is AuditStatus.PASS
    text = evaluate_lcp_image(make_context(integrations={"psi": [_psi_record(90, lazy=None)]}))[0]
    assert text.status is AuditStatus.NOT_APPLICABLE


def test_gsc_sitemap_states():
    unconfigured = make_context(integrations={"gsc": {"configured": False}})
    assert evaluate_gsc_sitemap(unconfigured)[0].status is AuditStatus.NOT_APPLICABLE

    broken = make_context(
        integrations={"gsc": {"configured": True, "data": {"error": "HttpError"}}}
    )
    assert evaluate_gsc_sitemap(broken)[0].status is AuditStatus.UNKNOWN

    sitemap = sitemap_observation()
    submitted = make_context(
        site_observations={"sitemaps": (sitemap,)},
        integrations={"gsc": {"configured": True, "data": {"sitemaps": [
            {"path": "https://example.com/sitemap.xml", "errors": 0, "warnings": 0},
        ]}}},
    )
    assert evaluate_gsc_sitemap(submitted)[0].status is AuditStatus.PASS

    unsubmitted = make_context(
        site_observations={"sitemaps": (sitemap,)},
        integrations={"gsc": {"configured": True, "data": {"sitemaps": []}}},
    )
    assert evaluate_gsc_sitemap(unsubmitted)[0].status is AuditStatus.REVIEW

    with_errors = make_context(
        site_observations={"sitemaps": (sitemap,)},
        integrations={"gsc": {"configured": True, "data": {"sitemaps": [
            {"path": "https://example.com/sitemap.xml", "errors": 3, "warnings": 0},
        ]}}},
    )
    assert evaluate_gsc_sitemap(with_errors)[0].status is AuditStatus.FAIL


def test_bing_disconnected_is_unknown_with_integration_owner():
    result = evaluate_bing(make_context())[0]
    assert result.status is AuditStatus.UNKNOWN
    assert result.next_action.owner == "integration"

    connected_empty = make_context(
        integrations={"bing": {"configured": True, "data": {"sitemaps": []}}}
    )
    assert evaluate_bing(connected_empty)[0].status is AuditStatus.REVIEW

    connected = make_context(
        integrations={"bing": {"configured": True, "data": {"sitemaps": [{"path": "x"}]}}}
    )
    assert evaluate_bing(connected)[0].status is AuditStatus.PASS


def test_collect_integrations_respects_configuration():
    from src.technical_audit.collector import CollectedSite, HttpEvidence
    from src.technical_audit.evidence.performance import collect_integrations
    from src.technical_audit.site import SiteIdentity

    def evidence(url):
        return HttpEvidence(
            request_url=url, final_url=url, redirect_chain=(url,), status_code=200,
            content_type="text/html", body="<html></html>", body_truncated=False,
            error=None, retrieved_at="2026-07-15T12:00:00+00:00", fingerprint="a" * 64,
        )

    home = evidence("https://example.com/")
    collected = CollectedSite(
        identity=SiteIdentity.from_domain("example.com", "other"),
        homepage=home, pages=(home,), llms_txt=evidence("https://example.com/llms.txt"),
        scope={},
    )

    bare = collect_integrations(collected, "", env={})
    assert "crux" not in bare and "psi" not in bare
    assert bare["gsc"] == {"configured": False}
    assert bare["bing"] == {"configured": False}

    calls = []
    full = collect_integrations(
        collected, "https://www.example.com/",
        env={"CRUX_API_KEY": "c", "PAGESPEED_API_KEY": "p", "BING_WEBMASTER_API_KEY": "b"},
        crux_fetch=lambda url, key: calls.append(("crux", url)) or {"subject": url},
        psi_fetch=lambda url, key: calls.append(("psi", url)) or {"subject": url},
        gsc_fetch=lambda site: calls.append(("gsc", site)) or {"sitemaps": []},
        bing_fetch=lambda site, key: calls.append(("bing", site)) or {"sitemaps": []},
    )
    assert full["gsc"]["configured"] and full["bing"]["configured"]
    assert ("crux", "https://example.com/") in calls
    assert ("psi", "https://example.com/") in calls
    assert ("gsc", "https://www.example.com/") in calls
