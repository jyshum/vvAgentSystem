from __future__ import annotations

from typing import Any

from ..models import (
    Applicability,
    AuditStatus,
    CheckResult,
    Confidence,
    NextAction,
)


def build_result(
    *,
    check_id: str,
    section: str,
    subject: str,
    status: AuditStatus,
    severity: str,
    summary: str,
    expected: str,
    observed: dict[str, Any],
    evidence_refs: tuple[str, ...],
    applicability_reason: str,
    instruction: str,
    owner: str | None = None,
    confidence: Confidence = Confidence.HIGH,
    scope: dict[str, Any] | None = None,
    remediation_id: str | None = None,
    check_version: int = 1,
) -> CheckResult:
    if owner is None:
        owner = "system" if status is AuditStatus.PASS else "admin"
    return CheckResult(
        check_id=check_id,
        check_version=check_version,
        section=section,
        subject=subject,
        status=status,
        severity=severity,
        summary=summary,
        expected=expected,
        observed=observed,
        evidence_refs=evidence_refs,
        scope=scope or {"sampled": False, "urls_checked": 1},
        applicability=Applicability(True, applicability_reason),
        confidence=confidence,
        next_action=NextAction(owner, instruction),
        remediation_id=remediation_id,
    )


def probe_disposition(status_code: int, error: str | None) -> str:
    """Classify a bounded external probe as 'fail', 'unknown', or 'healthy'.

    Errs toward 'unknown' for anything transient or ambiguous: only a confirmed
    dead host (DNS resolution failure) or a definitive 404/410/5xx status fails.
    A timeout, connection reset, TLS handshake error, or protocol error is
    transient/blocked and must never be presented as a confirmed defect.
    """
    if error:
        text = str(error).lower()
        if (
            "dns resolution failed" in text
            or "name or service not known" in text
            or "nodename nor servname" in text
            or "no address" in text
        ):
            return "fail"
        return "unknown"
    if status_code in {404, 410}:
        return "fail"
    if status_code in {403, 429} or status_code == 0:
        return "unknown"
    if status_code >= 500:
        return "fail"
    return "healthy"


def unknown_result(
    *,
    check_id: str,
    section: str,
    subject: str,
    expected: str,
    observed: dict[str, Any],
    evidence_refs: tuple[str, ...],
    applicability_reason: str,
    instruction: str,
    owner: str = "system",
    severity: str = "medium",
    scope: dict[str, Any] | None = None,
) -> CheckResult:
    return build_result(
        check_id=check_id,
        section=section,
        subject=subject,
        status=AuditStatus.UNKNOWN,
        severity=severity,
        summary="Applicable check could not complete",
        expected=expected,
        observed=observed,
        evidence_refs=evidence_refs,
        applicability_reason=applicability_reason,
        instruction=instruction,
        owner=owner,
        scope=scope,
    )
