from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit

from ..models import AuditContext, AuditStatus, CheckResult
from ._common import build_result, unknown_result

_SECTION = "ssl_https"

_EXPECTED_CERT = (
    "A valid, hostname-matching certificate with more than 30 days to expiry"
)
_EXPECTED_REDIRECT = "Plain-HTTP requests redirect to the canonical HTTPS site"
_EXPECTED_MIXED = "HTTPS pages load no active content over plain HTTP"


def _site_subject(context: AuditContext) -> str:
    return context.pages[0].subject if context.pages else f"https://{context.domain}/"


def parse_cert_datetime(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=timezone.utc
        )
    except (ValueError, TypeError):
        return None


def evaluate_tls_certificate(context: AuditContext) -> list[CheckResult]:
    subject = _site_subject(context)
    tls = context.site_observations.get("tls")
    reason = "The production site is served over HTTPS"
    if tls is None:
        return [
            unknown_result(
                check_id="tls.certificate", section=_SECTION, subject=subject,
                expected=_EXPECTED_CERT, observed={"collected": False},
                evidence_refs=(), applicability_reason=reason,
                instruction="Re-run collection with TLS inspection enabled",
            )
        ]
    data = tls.data
    observed = {key: data.get(key) for key in (
        "verified", "not_after", "error", "unreachable", "host",
    )}
    common = {
        "check_id": "tls.certificate", "section": _SECTION, "subject": subject,
        "expected": _EXPECTED_CERT, "observed": observed,
        "evidence_refs": (tls.id,), "applicability_reason": reason,
    }
    if data.get("unreachable"):
        return [
            unknown_result(
                check_id="tls.certificate", section=_SECTION, subject=subject,
                expected=_EXPECTED_CERT, observed=observed,
                evidence_refs=(tls.id,), applicability_reason=reason,
                instruction="Retry the TLS handshake; the host could not be reached",
            )
        ]
    if not data.get("verified"):
        return [
            build_result(
                **common, status=AuditStatus.FAIL, severity="critical",
                summary="The certificate failed verification",
                instruction=(
                    "Renew or correct the certificate through the platform's SSL"
                    " controls (Squarespace: Settings → Domains → SSL)"
                ),
                remediation_id="tls.fix_certificate",
            )
        ]
    expires = parse_cert_datetime(data.get("not_after") or "")
    if expires is None:
        return [
            unknown_result(
                check_id="tls.certificate", section=_SECTION, subject=subject,
                expected=_EXPECTED_CERT, observed=observed,
                evidence_refs=(tls.id,), applicability_reason=reason,
                instruction="The certificate expiry could not be read; retry the inspection",
            )
        ]
    run_at = datetime.fromisoformat(context.run_timestamp)
    days_left = (expires - run_at).days
    observed["days_to_expiry"] = days_left
    if days_left < 0:
        status, severity, summary = (
            AuditStatus.FAIL, "critical", "The certificate has expired",
        )
    elif days_left <= 7:
        status, severity, summary = (
            AuditStatus.FAIL, "high", f"The certificate expires in {days_left} days",
        )
    elif days_left <= 30:
        status, severity, summary = (
            AuditStatus.REVIEW, "medium",
            f"The certificate expires in {days_left} days; confirm renewal is scheduled",
        )
    else:
        status, severity, summary = (
            AuditStatus.PASS, "low", "The certificate is valid and not near expiry",
        )
    return [
        build_result(
            **common, status=status, severity=severity, summary=summary,
            instruction=(
                "No action required" if status is AuditStatus.PASS else
                "Confirm automatic renewal through the platform's SSL controls"
            ),
            remediation_id=None if status is AuditStatus.PASS else "tls.fix_certificate",
        )
    ]


def evaluate_https_redirect(context: AuditContext) -> list[CheckResult]:
    subject = _site_subject(context)
    probe = context.site_observations.get("http_probe")
    reason = "Users and crawlers may request the plain-HTTP variant"
    if probe is None:
        return [
            unknown_result(
                check_id="tls.https_redirect", section=_SECTION, subject=subject,
                expected=_EXPECTED_REDIRECT, observed={"collected": False},
                evidence_refs=(), applicability_reason=reason,
                instruction="Re-run collection with the plain-HTTP probe enabled",
            )
        ]
    data = probe.data
    chain = list(data.get("redirect_chain") or [])
    final_url = data.get("final_url") or ""
    error = data.get("error") or ""
    observed = {
        "redirect_chain": chain,
        "final_url": final_url,
        "status_code": data.get("status_code"),
        "error": error or None,
    }
    common = {
        "check_id": "tls.https_redirect", "section": _SECTION, "subject": subject,
        "expected": _EXPECTED_REDIRECT, "observed": observed,
        "evidence_refs": (probe.id,), "applicability_reason": reason,
    }
    if error:
        if "redirect limit" in error or "unsafe redirect" in error:
            return [
                build_result(
                    **common, status=AuditStatus.FAIL, severity="high",
                    summary="Plain-HTTP requests loop or redirect to an unsafe destination",
                    instruction="Correct the domain redirect configuration",
                    remediation_id="tls.fix_http_redirect",
                )
            ]
        return [
            build_result(
                **common, status=AuditStatus.REVIEW, severity="medium",
                summary="The plain-HTTP variant could not be reached",
                instruction=(
                    "Verify that typing the domain without https:// still reaches the"
                    " site; port 80 appears closed"
                ),
            )
        ]
    final_parts = urlsplit(final_url)
    lands_on_https = (
        final_parts.scheme.lower() == "https"
        and (final_parts.hostname or "").lower() in context.site_identity.allowed_hosts
    )
    if lands_on_https:
        return [
            build_result(
                **common, status=AuditStatus.PASS, severity="low",
                summary="Plain-HTTP requests redirect to the canonical HTTPS site",
                instruction="No action required",
            )
        ]
    return [
        build_result(
            **common, status=AuditStatus.FAIL, severity="high",
            summary="Plain-HTTP requests do not reach the canonical HTTPS site",
            instruction="Enable the HTTP-to-HTTPS redirect in the domain settings",
            remediation_id="tls.fix_http_redirect",
        )
    ]


def evaluate_mixed_content(context: AuditContext) -> list[CheckResult]:
    results = []
    for page in context.pages:
        data = page.data
        if not data.get("available", True):
            results.append(
                unknown_result(
                    check_id="tls.mixed_content", section=_SECTION, subject=page.subject,
                    expected=_EXPECTED_MIXED,
                    observed={"status_code": data.get("status_code"), "error": data.get("fetch_error")},
                    evidence_refs=(page.id,),
                    applicability_reason="Audited page retrieval was attempted",
                    instruction="Retry the page request or inspect host access controls",
                )
            )
            continue
        if not data.get("is_html", False):
            results.append(
                CheckResult.not_applicable(
                    check_id="tls.mixed_content", check_version=1, section=_SECTION,
                    subject=page.subject, reason="Page is not an HTML document",
                )
            )
            continue
        candidates = data.get("active_mixed_candidates", [])
        common = {
            "check_id": "tls.mixed_content", "section": _SECTION, "subject": page.subject,
            "expected": _EXPECTED_MIXED,
            "observed": {"active_http_urls": candidates, "evidence": "raw_html"},
            "evidence_refs": (page.id,),
            "applicability_reason": "HTTPS page with observable subresource references",
        }
        if candidates:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="high",
                    summary="Active content is referenced over plain HTTP",
                    instruction=(
                        "Serve the listed resources over HTTPS; review any insecure"
                        " embedded integration with the business before removing it"
                    ),
                    remediation_id="tls.fix_mixed_content",
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary="No active mixed content found in the raw HTML",
                    instruction="No action required",
                )
            )
    return results
