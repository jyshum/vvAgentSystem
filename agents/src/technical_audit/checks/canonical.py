from __future__ import annotations

from urllib.parse import urlsplit

from ..models import (
    Applicability,
    AuditContext,
    AuditStatus,
    CheckResult,
    Confidence,
    NextAction,
)
from .metadata import _not_indexable_reason, _unknown_page_result


def evaluate_canonical(context: AuditContext) -> list[CheckResult]:
    allowed_hosts = {context.domain.lower()}
    allowed_hosts.update(
        host.lower() for host in context.profile.get("allowed_canonical_hosts", [])
    )
    results = []
    for page in context.pages:
        if not page.data.get("available", True):
            results.append(_unknown_page_result(
                page,
                "canonical.integrity",
                "canonical_url",
                "An observable canonical declaration state",
            ))
            continue
        reason = _not_indexable_reason(page)
        if reason:
            results.append(
                CheckResult.not_applicable(
                    check_id="canonical.integrity",
                    check_version=1,
                    section="canonical_url",
                    subject=page.subject,
                    reason=reason,
                )
            )
            continue

        canonicals = page.data.get("canonicals", [])
        status = AuditStatus.PASS
        severity = "low"
        summary = "One structurally valid canonical found"
        instruction = "No action required"
        remediation_id = None

        if not canonicals:
            status = AuditStatus.REVIEW
            severity = "medium"
            summary = "Canonical declaration is missing"
            instruction = "Confirm the preferred URL before adding a canonical"
            remediation_id = "canonical.correct"
        elif len(canonicals) > 1:
            status = AuditStatus.FAIL
            severity = "high"
            summary = "Multiple canonical declarations found"
            instruction = "Remove conflicts and keep the authoritative canonical declaration"
            remediation_id = "canonical.correct"
        else:
            target = urlsplit(canonicals[0])
            host = (target.hostname or "").lower()
            unsafe = (
                target.scheme != "https"
                or not host
                or host not in allowed_hosts
                or any(marker in host for marker in ("staging", "preview", "localhost"))
                or bool(target.fragment)
            )
            if unsafe:
                status = AuditStatus.FAIL
                severity = "critical" if host not in allowed_hosts else "high"
                summary = "Canonical target is structurally unsafe or unexpected"
                instruction = "Confirm the preferred production URL and correct the canonical target"
                remediation_id = "canonical.correct"

        results.append(
            CheckResult(
                check_id="canonical.integrity",
                check_version=1,
                section="canonical_url",
                subject=page.subject,
                status=status,
                severity=severity,
                summary=summary,
                expected="Zero or one absolute HTTPS canonical on an approved production host; target health is validated separately",
                observed={"canonicals": canonicals, "count": len(canonicals)},
                evidence_refs=(page.id,),
                scope={"sampled": False, "urls_checked": 1},
                applicability=Applicability(True, "Canonical indexable HTML page"),
                confidence=Confidence.HIGH,
                next_action=NextAction(
                    "system" if status is AuditStatus.PASS else "admin", instruction
                ),
                remediation_id=remediation_id,
            )
        )
    return results
