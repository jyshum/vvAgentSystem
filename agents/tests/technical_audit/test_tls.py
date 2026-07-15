from src.technical_audit.checks.tls import (
    evaluate_https_redirect,
    evaluate_mixed_content,
    evaluate_tls_certificate,
)
from src.technical_audit.models import AuditStatus

from helpers import make_context, page_observation, site_observation


def _tls(**overrides):
    data = {
        "verified": True,
        "host": "example.com",
        "not_after": "Oct  1 12:00:00 2027 GMT",
        "unreachable": False,
        "error": None,
    }
    data.update(overrides)
    return site_observation("tls", "example.com", **data)


def _probe(chain, *, status=301, error=None):
    return site_observation(
        "http_probe",
        chain[0],
        request_url=chain[0],
        final_url=chain[-1],
        redirect_chain=list(chain),
        status_code=status,
        error=error,
    )


def test_certificate_windows():
    healthy = make_context(site_observations={"tls": _tls()})
    assert evaluate_tls_certificate(healthy)[0].status is AuditStatus.PASS

    soon = make_context(
        site_observations={"tls": _tls(not_after="Aug  1 12:00:00 2026 GMT")}
    )
    result = evaluate_tls_certificate(soon)[0]
    assert result.status is AuditStatus.REVIEW
    assert result.observed["days_to_expiry"] == 17

    urgent = make_context(
        site_observations={"tls": _tls(not_after="Jul 20 12:00:00 2026 GMT")}
    )
    assert evaluate_tls_certificate(urgent)[0].status is AuditStatus.FAIL

    expired = make_context(
        site_observations={"tls": _tls(not_after="Jul  1 12:00:00 2026 GMT")}
    )
    result = evaluate_tls_certificate(expired)[0]
    assert result.status is AuditStatus.FAIL
    assert result.severity == "critical"


def test_certificate_verification_failure_is_critical_fail():
    context = make_context(
        site_observations={
            "tls": _tls(verified=False, error="certificate_verification: hostname mismatch")
        }
    )
    result = evaluate_tls_certificate(context)[0]
    assert result.status is AuditStatus.FAIL
    assert result.severity == "critical"


def test_certificate_unreachable_and_missing_are_unknown():
    unreachable = make_context(
        site_observations={"tls": _tls(verified=False, unreachable=True, error="TimeoutError")}
    )
    assert evaluate_tls_certificate(unreachable)[0].status is AuditStatus.UNKNOWN

    missing = make_context(site_observations={})
    assert evaluate_tls_certificate(missing)[0].status is AuditStatus.UNKNOWN


def test_https_redirect_pass_fail_review():
    good = make_context(
        site_observations={
            "http_probe": _probe(["http://example.com/", "https://example.com/"], status=200)
        }
    )
    assert evaluate_https_redirect(good)[0].status is AuditStatus.PASS

    served_plain = make_context(
        site_observations={"http_probe": _probe(["http://example.com/"], status=200)}
    )
    assert evaluate_https_redirect(served_plain)[0].status is AuditStatus.FAIL

    loop = make_context(
        site_observations={
            "http_probe": _probe(
                ["http://example.com/"], status=301, error="redirect limit exceeded (5)"
            )
        }
    )
    assert evaluate_https_redirect(loop)[0].status is AuditStatus.FAIL

    closed = make_context(
        site_observations={
            "http_probe": _probe(["http://example.com/"], status=0, error="ConnectError")
        }
    )
    assert evaluate_https_redirect(closed)[0].status is AuditStatus.REVIEW


def test_https_redirect_to_foreign_host_fails():
    context = make_context(
        site_observations={
            "http_probe": _probe(
                ["http://example.com/", "https://attacker.example/"], status=200
            )
        }
    )
    assert evaluate_https_redirect(context)[0].status is AuditStatus.FAIL


def test_mixed_content_statuses():
    dirty = page_observation(
        "https://example.com/",
        active_mixed_candidates=["http://cdn.example/app.js"],
    )
    clean = page_observation("https://example.com/clean")
    pdf = page_observation(
        "https://example.com/file.pdf", is_html=False, content_type="application/pdf"
    )
    blocked = page_observation(
        "https://example.com/blocked", available=False, status_code=403
    )
    context = make_context(pages=(dirty, clean, pdf, blocked))
    results = {result.subject: result for result in evaluate_mixed_content(context)}

    assert results["https://example.com/"].status is AuditStatus.FAIL
    assert results["https://example.com/clean"].status is AuditStatus.PASS
    assert results["https://example.com/file.pdf"].status is AuditStatus.NOT_APPLICABLE
    assert results["https://example.com/blocked"].status is AuditStatus.UNKNOWN
