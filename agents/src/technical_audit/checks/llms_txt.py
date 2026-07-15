from __future__ import annotations

import re

from ..models import (
    Applicability,
    AuditContext,
    AuditStatus,
    CheckResult,
    Confidence,
    NextAction,
)


UNSAFE_CONTENT = re.compile(
    r"(api[_ -]?key|secret[_ -]?key|password\s*[=:]|-----BEGIN .*PRIVATE KEY-----|staging\.)",
    re.IGNORECASE,
)


def evaluate_llms_txt(context: AuditContext) -> list[CheckResult]:
    subject = f"https://{context.domain}/llms.txt"
    observation = context.site_observations.get("llms_txt")
    if observation is None:
        return [
            CheckResult(
                check_id="llms_txt.integrity",
                check_version=1,
                section="llms_txt",
                subject=subject,
                status=AuditStatus.UNKNOWN,
                severity="low",
                summary="llms.txt could not be observed",
                expected="A retrievable root-file observation",
                observed={},
                evidence_refs=(),
                scope={"sampled": False, "urls_checked": 1},
                applicability=Applicability(True, "The root file request was scheduled"),
                confidence=Confidence.HIGH,
                next_action=NextAction("system", "Retry the root-file request"),
                remediation_id=None,
            )
        ]

    subject = observation.subject
    data = observation.data
    status_code = int(data.get("status_code") or 0)
    body = data.get("body") or ""
    exists = status_code == 200 and bool(body.strip())

    if status_code not in {200, 404, 410} or data.get("error"):
        return [
            CheckResult(
                check_id="llms_txt.integrity",
                check_version=1,
                section="llms_txt",
                subject=subject,
                status=AuditStatus.UNKNOWN,
                severity="medium",
                summary="llms.txt access could not be determined",
                expected="A bounded observation of the optional root file",
                observed={
                    "status_code": status_code,
                    "content_type": data.get("content_type"),
                    "final_url": data.get("final_url"),
                    "error": data.get("error"),
                },
                evidence_refs=(observation.id,),
                scope={"sampled": False, "urls_checked": 1},
                applicability=Applicability(
                    True, "The optional root-file request was scheduled"
                ),
                confidence=Confidence.HIGH,
                next_action=NextAction(
                    "system", "Retry or inspect the host/CDN response"
                ),
                remediation_id=None,
            )
        ]

    if not exists:
        platform = context.site_identity.platform
        reason = (
            "Squarespace does not require or reliably support an optional root llms.txt file"
            if platform == "squarespace"
            else f"Optional llms.txt content is absent on the {platform or 'unknown'} platform"
        )
        return [
            CheckResult.not_applicable(
                check_id="llms_txt.integrity",
                check_version=1,
                section="llms_txt",
                subject=subject,
                reason=reason,
            )
        ]

    status = AuditStatus.PASS
    severity = "low"
    summary = "Optional llms.txt file is structurally usable"
    instruction = "No action required"
    remediation_id = None

    if (data.get("content_type") or "").lower().startswith(
        "text/html"
    ) or body.lstrip().lower().startswith("<html"):
        status = AuditStatus.FAIL
        severity = "medium"
        summary = "llms.txt returns an HTML fallback"
        instruction = "Serve the intended plain-text or Markdown file at the root URL"
        remediation_id = "llms_txt.correct"
    elif UNSAFE_CONTENT.search(body):
        status = AuditStatus.FAIL
        severity = "critical"
        summary = "llms.txt may expose a secret or staging reference"
        instruction = "Remove unsafe content and rotate any exposed secret"
        remediation_id = "llms_txt.correct"

    return [
        CheckResult(
            check_id="llms_txt.integrity",
            check_version=1,
            section="llms_txt",
            subject=subject,
            status=status,
            severity=severity,
            summary=summary,
            expected="When present, a nonempty text/Markdown root file without secrets or staging references",
            observed={
                "status_code": status_code,
                "content_type": data.get("content_type"),
                "final_url": data.get("final_url"),
                "bytes": len(body.encode("utf-8")),
                "error": data.get("error"),
            },
            evidence_refs=(observation.id,),
            scope={"sampled": False, "urls_checked": 1},
            applicability=Applicability(
                True,
                f"An optional llms.txt file exists on {context.site_identity.platform or 'the configured platform'}",
            ),
            confidence=Confidence.HIGH,
            next_action=NextAction(
                "system" if status is AuditStatus.PASS else "admin", instruction
            ),
            remediation_id=remediation_id,
        )
    ]
