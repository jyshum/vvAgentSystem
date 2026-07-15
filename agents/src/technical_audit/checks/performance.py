from __future__ import annotations

from ..models import AuditContext, AuditStatus, CheckResult
from ._common import build_result, unknown_result

_SECTION = "page_speed"

_EXPECTED_CRUX = (
    "75th-percentile field metrics meet Core Web Vitals: LCP <= 2.5 s,"
    " INP <= 200 ms, CLS <= 0.1"
)
_EXPECTED_LAB = (
    "Median of three mobile Lighthouse runs scores 90+ (an external lab"
    " diagnostic, never the product's own score)"
)
_EXPECTED_LCP_IMAGE = "The measured LCP image is not lazy-loaded"

# (metric, pass_max, review_max)
_CWV_THRESHOLDS = (
    ("lcp_ms", 2_500.0, 4_000.0),
    ("inp_ms", 200.0, 500.0),
    ("cls", 0.1, 0.25),
)


def _classify_metric(name: str, value: float) -> str:
    for metric, pass_max, review_max in _CWV_THRESHOLDS:
        if metric == name:
            if value <= pass_max:
                return "pass"
            if value <= review_max:
                return "review"
            return "fail"
    raise ValueError(f"unknown metric {name}")


def evaluate_crux(context: AuditContext) -> list[CheckResult]:
    records = context.integrations.get("crux")
    subject = context.pages[0].subject if context.pages else f"https://{context.domain}/"
    reason = "Field performance applies to every public page"
    if records is None:
        return [
            unknown_result(
                check_id="performance.crux", section=_SECTION, subject=subject,
                expected=_EXPECTED_CRUX,
                observed={"unavailable": "missing_api_key"}, evidence_refs=(),
                applicability_reason=reason, owner="integration",
                instruction="Configure CRUX_API_KEY to collect field performance evidence",
            )
        ]
    results = []
    for record in records:
        record_subject = record.get("subject") or subject
        if record.get("error"):
            results.append(
                unknown_result(
                    check_id="performance.crux", section=_SECTION, subject=record_subject,
                    expected=_EXPECTED_CRUX, observed={"error": record["error"]},
                    evidence_refs=(), applicability_reason=reason,
                    instruction="Retry the CrUX request; the API call failed",
                )
            )
            continue
        if record.get("insufficient_data"):
            results.append(
                unknown_result(
                    check_id="performance.crux", section=_SECTION, subject=record_subject,
                    expected=_EXPECTED_CRUX, observed={"insufficient_data": True},
                    evidence_refs=(), applicability_reason=reason,
                    instruction=(
                        "Insufficient real-user data exists for this page and origin;"
                        " this is not a failure"
                    ),
                )
            )
            continue
        metrics = record.get("metrics", {})
        classified = {
            name: _classify_metric(name, value)
            for name, value in metrics.items()
            if value is not None
        }
        observed = {
            "metrics": metrics,
            "classified": classified,
            "origin_fallback": bool(record.get("origin_fallback")),
            "form_factor": record.get("form_factor"),
            "collection_period": record.get("collection_period"),
        }
        scope = {
            "sampled": True,
            "urls_checked": 1,
            "level": "origin" if record.get("origin_fallback") else "page",
        }
        common = {
            "check_id": "performance.crux", "section": _SECTION, "subject": record_subject,
            "expected": _EXPECTED_CRUX, "observed": observed, "evidence_refs": (),
            "applicability_reason": reason, "scope": scope,
        }
        label = " (origin-level data)" if record.get("origin_fallback") else ""
        if not classified:
            results.append(
                unknown_result(
                    check_id="performance.crux", section=_SECTION, subject=record_subject,
                    expected=_EXPECTED_CRUX, observed=observed, evidence_refs=(),
                    applicability_reason=reason,
                    instruction="CrUX returned no p75 metrics for this subject",
                    scope=scope,
                )
            )
        elif "fail" in classified.values():
            worst = [name for name, status in classified.items() if status == "fail"]
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="high",
                    summary=f"Field Core Web Vitals fail at p75: {', '.join(worst)}{label}",
                    instruction=(
                        "Investigate the failing metric's root causes in the lab"
                        " diagnostic; never remove analytics, consent, booking, or"
                        " accessibility behavior automatically"
                    ),
                    remediation_id="performance.improve_cwv",
                )
            )
        elif "review" in classified.values():
            needs = [name for name, status in classified.items() if status == "review"]
            results.append(
                build_result(
                    **common, status=AuditStatus.REVIEW, severity="medium",
                    summary=f"Field Core Web Vitals need improvement at p75: {', '.join(needs)}{label}",
                    instruction="Review the lab diagnostic for the named metrics",
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary=f"Field Core Web Vitals pass at p75{label}",
                    instruction="No action required",
                )
            )
    return results


def evaluate_lighthouse(context: AuditContext) -> list[CheckResult]:
    records = context.integrations.get("psi")
    subject = context.pages[0].subject if context.pages else f"https://{context.domain}/"
    reason = "Lab diagnostics support field evidence on sampled pages"
    if records is None:
        return [
            unknown_result(
                check_id="performance.lighthouse", section=_SECTION, subject=subject,
                expected=_EXPECTED_LAB, observed={"unavailable": "missing_api_key"},
                evidence_refs=(), applicability_reason=reason, owner="integration",
                instruction="Configure PAGESPEED_API_KEY to collect Lighthouse lab diagnostics",
            )
        ]
    results = []
    for record in records:
        record_subject = record.get("subject") or subject
        if record.get("error"):
            results.append(
                unknown_result(
                    check_id="performance.lighthouse", section=_SECTION,
                    subject=record_subject, expected=_EXPECTED_LAB,
                    observed={"error": record["error"]}, evidence_refs=(),
                    applicability_reason=reason,
                    instruction="Retry the PageSpeed Insights request",
                )
            )
            continue
        score = record.get("median_score")
        observed = {
            "median_score": score,
            "run_scores": record.get("run_scores"),
            "lighthouse_version": record.get("lighthouse_version"),
            "fetch_times": record.get("fetch_times"),
            "throttling": record.get("throttling"),
            "device": record.get("device"),
            "cache_state": record.get("cache_state"),
            "auth_state": record.get("auth_state"),
            "tbt_ms_runs": record.get("tbt_ms_runs"),
            "label": "external lab diagnostic",
            "inp_note": "Lab data cannot pass INP; TBT is a diagnostic proxy only",
        }
        scope = {"sampled": True, "urls_checked": 1, "runs": record.get("runs")}
        common = {
            "check_id": "performance.lighthouse", "section": _SECTION,
            "subject": record_subject, "expected": _EXPECTED_LAB,
            "observed": observed, "evidence_refs": (),
            "applicability_reason": reason, "scope": scope,
        }
        if score is None:
            results.append(
                unknown_result(
                    check_id="performance.lighthouse", section=_SECTION,
                    subject=record_subject, expected=_EXPECTED_LAB, observed=observed,
                    evidence_refs=(), applicability_reason=reason,
                    instruction="PSI returned no performance score", scope=scope,
                )
            )
        elif score >= 90:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary=f"Lighthouse lab median {score} (external diagnostic)",
                    instruction="No action required",
                )
            )
        elif score >= 50:
            results.append(
                build_result(
                    **common, status=AuditStatus.REVIEW, severity="medium",
                    summary=f"Lighthouse lab median {score} needs review (external diagnostic)",
                    instruction="Review the lab run's LCP/CLS/main-thread causes",
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="high",
                    summary=f"Lighthouse lab median {score} fails the lab check (external diagnostic)",
                    instruction=(
                        "Investigate LCP phases, shifting elements, and main-thread"
                        " causes; group template-level fixes"
                    ),
                    remediation_id="performance.improve_lab",
                )
            )
    return results


def evaluate_lcp_image(context: AuditContext) -> list[CheckResult]:
    records = context.integrations.get("psi")
    subject = context.pages[0].subject if context.pages else f"https://{context.domain}/"
    reason = "The measured LCP element determines whether the rule applies"
    if records is None:
        return [
            unknown_result(
                check_id="performance.lcp_image", section=_SECTION, subject=subject,
                expected=_EXPECTED_LCP_IMAGE,
                observed={"unavailable": "missing_api_key"}, evidence_refs=(),
                applicability_reason=reason, owner="integration",
                instruction="Configure PAGESPEED_API_KEY to measure the LCP element",
            )
        ]
    results = []
    for record in records:
        record_subject = record.get("subject") or subject
        if record.get("error"):
            results.append(
                unknown_result(
                    check_id="performance.lcp_image", section=_SECTION,
                    subject=record_subject, expected=_EXPECTED_LCP_IMAGE,
                    observed={"error": record["error"]}, evidence_refs=(),
                    applicability_reason=reason,
                    instruction="Retry the PageSpeed Insights request",
                )
            )
            continue
        lazy_score = record.get("lcp_lazy_score")
        observed = {
            "lcp_lazy_score": lazy_score,
            "lcp_element": record.get("lcp_element"),
        }
        common = {
            "check_id": "performance.lcp_image", "section": _SECTION,
            "subject": record_subject, "expected": _EXPECTED_LCP_IMAGE,
            "observed": observed, "evidence_refs": (),
            "applicability_reason": reason,
            "scope": {"sampled": True, "urls_checked": 1},
        }
        if lazy_score is None:
            results.append(
                CheckResult.not_applicable(
                    check_id="performance.lcp_image", check_version=1, section=_SECTION,
                    subject=record_subject,
                    reason="The measured LCP element is not an image",
                )
            )
        elif lazy_score >= 1:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary="The measured LCP image is not lazy-loaded",
                    instruction="No action required",
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="high",
                    summary="The measured LCP image is lazy-loaded",
                    instruction=(
                        "Remove lazy-loading from the LCP image and ensure it is"
                        " discoverable early"
                    ),
                    remediation_id="performance.fix_lcp_image",
                )
            )
    return results
