from __future__ import annotations

from ..models import AuditContext, AuditStatus, CheckResult
from ._common import build_result, unknown_result

_SECTION = "search_integrations"
_EXPECTED_GSC = (
    "The discovered sitemap is submitted to Search Console and processes"
    " without errors"
)
_EXPECTED_BING = "The sitemap is submitted to Bing Webmaster Tools"


def _site_subject(context: AuditContext) -> str:
    return context.pages[0].subject if context.pages else f"https://{context.domain}/"


def _discovered_sitemap_urls(context: AuditContext) -> list[str]:
    return [
        doc.data.get("final_url")
        for doc in tuple(context.site_observations.get("sitemaps") or ())
        if int(doc.data.get("status_code") or 0) == 200 and doc.data.get("final_url")
    ]


def evaluate_gsc_sitemap(context: AuditContext) -> list[CheckResult]:
    subject = _site_subject(context)
    gsc = context.integrations.get("gsc") or {}
    if not gsc.get("configured"):
        return [
            CheckResult.not_applicable(
                check_id="integration.gsc_sitemap", check_version=1, section=_SECTION,
                subject=subject,
                reason="No Search Console property is configured for this client",
            )
        ]
    data = gsc.get("data") or {}
    if data.get("error") or "sitemaps" not in data:
        return [
            unknown_result(
                check_id="integration.gsc_sitemap", section=_SECTION, subject=subject,
                expected=_EXPECTED_GSC,
                observed={"error": data.get("error", "no sitemap data returned")},
                evidence_refs=(), owner="integration",
                applicability_reason="A Search Console property is configured",
                instruction=(
                    "Reconnect Search Console or fix its credentials; the public"
                    " sitemap checks remain independent of this integration"
                ),
            )
        ]
    submitted = data.get("sitemaps") or []
    discovered = _discovered_sitemap_urls(context)
    submitted_paths = {item.get("path", "").rstrip("/").lower() for item in submitted}
    with_errors = [item for item in submitted if item.get("errors")]
    missing = [
        url for url in discovered
        if url.rstrip("/").lower() not in submitted_paths
    ]
    observed = {
        "submitted": submitted[:10],
        "discovered_sitemaps": discovered,
        "missing_from_gsc": missing,
        "with_errors": with_errors[:10],
    }
    common = {
        "check_id": "integration.gsc_sitemap", "section": _SECTION, "subject": subject,
        "expected": _EXPECTED_GSC, "observed": observed, "evidence_refs": (),
        "applicability_reason": "A Search Console property is configured",
        "scope": {"sampled": False, "urls_checked": len(discovered)},
    }
    if with_errors:
        return [
            build_result(
                **common, status=AuditStatus.FAIL, severity="medium",
                summary="Search Console reports sitemap processing errors",
                instruction="Open the sitemap report in Search Console and fix the listed errors",
                remediation_id="integrations.fix_gsc_sitemap",
            )
        ]
    if discovered and missing:
        return [
            build_result(
                **common, status=AuditStatus.REVIEW, severity="medium",
                summary="The discovered sitemap has not been submitted to Search Console",
                instruction="Submit the discovered sitemap URL in Search Console's sitemap report",
                remediation_id="integrations.submit_gsc_sitemap",
            )
        ]
    if not submitted and not discovered:
        return [
            build_result(
                **common, status=AuditStatus.REVIEW, severity="low",
                summary="No sitemap exists to submit to Search Console",
                instruction="Resolve the sitemap discovery finding first",
            )
        ]
    return [
        build_result(
            **common, status=AuditStatus.PASS, severity="low",
            summary="The sitemap is submitted and processing without errors",
            instruction="No action required",
        )
    ]


def evaluate_bing(context: AuditContext) -> list[CheckResult]:
    subject = _site_subject(context)
    bing = context.integrations.get("bing") or {}
    if not bing.get("configured"):
        return [
            unknown_result(
                check_id="integration.bing", section=_SECTION, subject=subject,
                expected=_EXPECTED_BING,
                observed={"connected": False}, evidence_refs=(),
                owner="integration",
                applicability_reason=(
                    "Bing submission is in scope for AI-answer visibility but its"
                    " integration is not connected"
                ),
                instruction="Connect Bing Webmaster Tools (set BING_WEBMASTER_API_KEY)",
            )
        ]
    data = bing.get("data") or {}
    if data.get("error"):
        return [
            unknown_result(
                check_id="integration.bing", section=_SECTION, subject=subject,
                expected=_EXPECTED_BING, observed={"error": data["error"]},
                evidence_refs=(), owner="integration",
                applicability_reason="The Bing integration is connected",
                instruction="Retry the Bing Webmaster request or fix its credentials",
            )
        ]
    submitted = data.get("sitemaps") or []
    observed = {"submitted": submitted[:10]}
    common = {
        "check_id": "integration.bing", "section": _SECTION, "subject": subject,
        "expected": _EXPECTED_BING, "observed": observed, "evidence_refs": (),
        "applicability_reason": "The Bing integration is connected",
        "scope": {"sampled": False, "urls_checked": len(submitted)},
    }
    if submitted:
        return [
            build_result(
                **common, status=AuditStatus.PASS, severity="low",
                summary="A sitemap is submitted to Bing Webmaster Tools",
                instruction="No action required",
            )
        ]
    return [
        build_result(
            **common, status=AuditStatus.REVIEW, severity="medium",
            summary="No sitemap is submitted to Bing Webmaster Tools",
            instruction="Submit the discovered sitemap in Bing Webmaster Tools",
            remediation_id="integrations.submit_bing_sitemap",
        )
    ]
