from __future__ import annotations

from ..evidence.structured_data import (
    entity_types,
    find_duplicate_entities,
    find_placeholders,
    parse_jsonld,
    same_site_urls,
)
from ..models import AuditContext, AuditStatus, CheckResult
from ._common import build_result, unknown_result

_SECTION = "schema_markup"
_EXPECTED_INTEGRITY = (
    "Structured data parses cleanly with no placeholders, duplicate entities,"
    " or references to broken same-site URLs"
)
_EXPECTED_COVERAGE = "The homepage identifies the organization or website in JSON-LD"


def evaluate_schema_integrity(context: AuditContext) -> list[CheckResult]:
    collected_status: dict[str, int] = {}
    for page in context.pages:
        key = page.subject.rstrip("/").lower()
        collected_status[key] = int(page.data.get("status_code") or 0)

    results = []
    for page in context.pages:
        data = page.data
        if not data.get("available", True):
            results.append(
                unknown_result(
                    check_id="schema.integrity", section=_SECTION, subject=page.subject,
                    expected=_EXPECTED_INTEGRITY,
                    observed={"status_code": data.get("status_code"), "error": data.get("fetch_error")},
                    evidence_refs=(page.id,),
                    applicability_reason="Audited page retrieval was attempted",
                    instruction="Retry the page request or inspect host access controls",
                )
            )
            continue
        blocks = data.get("jsonld_blocks", [])
        has_other_syntax = data.get("has_microdata") or data.get("has_rdfa")
        if not data.get("is_html", False) or (not blocks and not has_other_syntax):
            results.append(
                CheckResult.not_applicable(
                    check_id="schema.integrity", check_version=1, section=_SECTION,
                    subject=page.subject,
                    reason="Page declares no structured data",
                )
            )
            continue

        entities, parse_errors = parse_jsonld(blocks)
        placeholders = find_placeholders(entities)
        duplicates = find_duplicate_entities(entities)
        broken_refs = [
            url
            for url in same_site_urls(entities, context.site_identity.allowed_hosts)
            if collected_status.get(url.rstrip("/").lower()) in {404, 410}
        ]
        observed = {
            "jsonld_blocks": len(blocks),
            "entities": sorted(entity_types(entities)),
            "parse_errors": parse_errors,
            "placeholders": placeholders[:10],
            "duplicate_entities": duplicates[:10],
            "broken_same_site_urls": broken_refs[:10],
            "has_microdata": bool(data.get("has_microdata")),
            "has_rdfa": bool(data.get("has_rdfa")),
        }
        common = {
            "check_id": "schema.integrity", "section": _SECTION, "subject": page.subject,
            "expected": _EXPECTED_INTEGRITY, "observed": observed,
            "evidence_refs": (page.id,),
            "applicability_reason": "The page declares structured data",
        }
        if parse_errors or placeholders or duplicates or broken_refs:
            defects = []
            if parse_errors:
                defects.append("malformed JSON-LD")
            if placeholders:
                defects.append("placeholder values")
            if duplicates:
                defects.append("duplicate entities")
            if broken_refs:
                defects.append("references to broken pages")
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="high",
                    summary=f"Structured data has {', '.join(defects)}",
                    instruction=(
                        "Correct the structured data at its source (platform schema"
                        " settings or injected JSON-LD); do not invent replacement facts"
                    ),
                    remediation_id="schema.correct_markup",
                )
            )
        elif has_other_syntax and not blocks:
            results.append(
                build_result(
                    **common, status=AuditStatus.REVIEW, severity="medium",
                    summary="Non-JSON-LD structured data is present (Microdata/RDFa)",
                    instruction=(
                        "Verify the Microdata/RDFa markup with a structured-data"
                        " validator; this audit parses JSON-LD deterministically"
                    ),
                )
            )
        else:
            summary = "JSON-LD structured data parses cleanly"
            if has_other_syntax:
                results.append(
                    build_result(
                        **common, status=AuditStatus.REVIEW, severity="low",
                        summary=summary + "; additional Microdata/RDFa needs manual validation",
                        instruction="Verify the non-JSON-LD markup with a structured-data validator",
                    )
                )
            else:
                results.append(
                    build_result(
                        **common, status=AuditStatus.PASS, severity="low",
                        summary=summary, instruction="No action required",
                    )
                )
    return results


def evaluate_schema_coverage(context: AuditContext) -> list[CheckResult]:
    if not context.pages:
        return []
    homepage = context.pages[0]
    data = homepage.data
    if not data.get("available", True):
        return [
            unknown_result(
                check_id="schema.coverage", section=_SECTION, subject=homepage.subject,
                expected=_EXPECTED_COVERAGE,
                observed={"status_code": data.get("status_code")},
                evidence_refs=(homepage.id,),
                applicability_reason="Homepage retrieval was attempted",
                instruction="Retry the homepage request",
            )
        ]
    entities, _ = parse_jsonld(data.get("jsonld_blocks", []))
    types = entity_types(entities)
    observed = {"entities": sorted(types)}
    common = {
        "check_id": "schema.coverage", "section": _SECTION, "subject": homepage.subject,
        "expected": _EXPECTED_COVERAGE, "observed": observed,
        "evidence_refs": (homepage.id,),
        "applicability_reason": "Organization/WebSite coverage suits the homepage",
    }
    if types & {"Organization", "WebSite", "LocalBusiness"}:
        return [
            build_result(
                **common, status=AuditStatus.PASS, severity="low",
                summary="The homepage declares organization/website structured data",
                instruction="No action required",
            )
        ]
    return [
        build_result(
            **common, status=AuditStatus.REVIEW, severity="medium",
            summary="The homepage declares no Organization or WebSite structured data",
            instruction=(
                "Consider adding Organization/WebSite JSON-LD from verified business"
                " facts; missing recommended coverage is not a defect"
            ),
            remediation_id="schema.add_homepage_coverage",
        )
    ]
