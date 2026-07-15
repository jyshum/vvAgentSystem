from __future__ import annotations

from ..models import (
    Applicability,
    AuditContext,
    AuditStatus,
    CheckResult,
    Confidence,
    NextAction,
    Observation,
)


def _not_indexable_reason(page: Observation) -> str | None:
    if not page.data.get("is_html", False):
        return "Page is not an HTML document"
    robots_directives = set(page.data.get("robots_directives", []))
    if "noindex" in robots_directives or "none" in robots_directives:
        return "Page is intentionally marked noindex"
    return None


def _unknown_page_result(
    page: Observation, check_id: str, section: str, expected: str
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        check_version=1,
        section=section,
        subject=page.subject,
        status=AuditStatus.UNKNOWN,
        severity="medium",
        summary="Page could not be retrieved for this check",
        expected=expected,
        observed={
            "status_code": page.data.get("status_code"),
            "error": page.data.get("fetch_error"),
        },
        evidence_refs=(page.id,),
        scope={"sampled": False, "urls_checked": 1},
        applicability=Applicability(True, "Audited page retrieval was attempted"),
        confidence=Confidence.HIGH,
        next_action=NextAction("system", "Retry the page request or inspect host access controls"),
        remediation_id=None,
    )


def _result(
    *,
    page: Observation,
    check_id: str,
    section: str,
    status: AuditStatus,
    severity: str,
    summary: str,
    expected: str,
    observed: dict,
    instruction: str,
    remediation_id: str | None,
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        check_version=1,
        section=section,
        subject=page.subject,
        status=status,
        severity=severity,
        summary=summary,
        expected=expected,
        observed=observed,
        evidence_refs=(page.id,),
        scope={"sampled": False, "urls_checked": 1},
        applicability=Applicability(True, "Canonical indexable HTML page"),
        confidence=Confidence.HIGH,
        next_action=NextAction(
            "system" if status is AuditStatus.PASS else "admin", instruction
        ),
        remediation_id=remediation_id,
    )


def evaluate_meta_title(context: AuditContext) -> list[CheckResult]:
    results = []
    for page in context.pages:
        if not page.data.get("available", True):
            results.append(_unknown_page_result(
                page, "meta_title.integrity", "meta_title", "One nonempty title tag"
            ))
            continue
        reason = _not_indexable_reason(page)
        if reason:
            results.append(
                CheckResult.not_applicable(
                    check_id="meta_title.integrity",
                    check_version=1,
                    section="meta_title",
                    subject=page.subject,
                    reason=reason,
                )
            )
            continue

        titles = page.data.get("titles", [])
        if len(titles) != 1 or (len(titles) == 1 and not titles[0].strip()):
            summary = "Title is missing or empty" if len(titles) <= 1 else "Multiple title tags found"
            results.append(
                _result(
                    page=page,
                    check_id="meta_title.integrity",
                    section="meta_title",
                    status=AuditStatus.FAIL,
                    severity="high",
                    summary=summary,
                    expected="Exactly one nonempty title tag",
                    observed={"titles": titles, "count": len(titles)},
                    instruction="Add one truthful SEO title through the authoritative page setting",
                    remediation_id="meta_title.correct",
                )
            )
            continue

        title = titles[0].strip()
        verbose = len(title) > 100 or (65 <= len(title) <= 100 and len(title.split()) > 12)
        results.append(
            _result(
                page=page,
                check_id="meta_title.integrity",
                section="meta_title",
                status=AuditStatus.REVIEW if verbose else AuditStatus.PASS,
                severity="medium" if verbose else "low",
                summary="Title may be too verbose" if verbose else "One usable title tag found",
                expected="One concise, truthful title tag; character count is guidance, not a hard limit",
                observed={"titles": titles, "count": 1, "characters": len(title)},
                instruction="Review title wording without changing the visible heading"
                if verbose
                else "No action required",
                remediation_id="meta_title.correct" if verbose else None,
            )
        )
    return results


def evaluate_meta_description(context: AuditContext) -> list[CheckResult]:
    results = []
    for page in context.pages:
        if not page.data.get("available", True):
            results.append(_unknown_page_result(
                page,
                "meta_description.integrity",
                "meta_description",
                "An observable description state for the priority page",
            ))
            continue
        reason = _not_indexable_reason(page)
        if reason:
            results.append(
                CheckResult.not_applicable(
                    check_id="meta_description.integrity",
                    check_version=1,
                    section="meta_description",
                    subject=page.subject,
                    reason=reason,
                )
            )
            continue

        descriptions = page.data.get("meta_descriptions", [])
        if len(descriptions) > 1:
            results.append(
                _result(
                    page=page,
                    check_id="meta_description.integrity",
                    section="meta_description",
                    status=AuditStatus.FAIL,
                    severity="medium",
                    summary="Multiple meta descriptions found",
                    expected="At most one nonempty meta description",
                    observed={"descriptions": descriptions, "count": len(descriptions)},
                    instruction="Keep one accurate description in the authoritative SEO setting",
                    remediation_id="meta_description.correct",
                )
            )
            continue

        value = descriptions[0].strip() if descriptions else ""
        needs_review = not value or len(value) < 50 or len(value) > 200
        results.append(
            _result(
                page=page,
                check_id="meta_description.integrity",
                section="meta_description",
                status=AuditStatus.REVIEW if needs_review else AuditStatus.PASS,
                severity="medium" if needs_review else "low",
                summary="Meta description needs review"
                if needs_review
                else "One usable meta description found",
                expected="One accurate description; 50–200 characters is a review range, not a ranking rule",
                observed={"descriptions": descriptions, "count": len(descriptions), "characters": len(value)},
                instruction="Draft or review an accurate description from verified page content"
                if needs_review
                else "No action required",
                remediation_id="meta_description.correct" if needs_review else None,
            )
        )
    return results
