from __future__ import annotations

from ..models import AuditContext, AuditStatus, CheckResult
from ._common import build_result, probe_disposition, unknown_result

_SECTION = "source_citations"
_EXPECTED = (
    "Existing citation links in page content resolve to retrievable sources;"
    " the link count follows the claims, never a universal rule"
)


def evaluate_source_support(context: AuditContext) -> list[CheckResult]:
    probes = {
        probe.data.get("request_url"): probe
        for probe in tuple(context.site_observations.get("external_probes") or ())
    }
    results = []
    for page in context.pages:
        data = page.data
        if not data.get("available", True):
            results.append(
                unknown_result(
                    check_id="source_support.link_health", section=_SECTION,
                    subject=page.subject, expected=_EXPECTED,
                    observed={"status_code": data.get("status_code")},
                    evidence_refs=(page.id,),
                    applicability_reason="Audited page retrieval was attempted",
                    instruction="Retry the page request or inspect host access controls",
                )
            )
            continue
        citations = [
            link
            for link in data.get("links", [])
            if link.get("kind") == "external" and link.get("in_content")
        ]
        if not data.get("is_html", False) or not citations:
            results.append(
                CheckResult.not_applicable(
                    check_id="source_support.link_health", check_version=1,
                    section=_SECTION, subject=page.subject,
                    reason="Page content contains no external citation links",
                )
            )
            continue

        failures, unknowns, healthy, checked = [], [], [], 0
        refs = [page.id]
        for link in citations:
            probe = probes.get(link["url"])
            if probe is None:
                continue
            checked += 1
            refs.append(probe.id)
            probe_data = probe.data
            status_code = int(probe_data.get("status_code") or 0)
            error = probe_data.get("error")
            probe_error = None if error and "redirect" in str(error) else error
            disposition = probe_disposition(status_code, probe_error)
            if disposition == "fail":
                failures.append({
                    "url": link["url"],
                    "anchor": link.get("text", "")[:100],
                    "defect": f"status {status_code}" if status_code else str(error)[:200],
                })
            elif disposition == "unknown":
                unknowns.append({"url": link["url"], "status": status_code})
            else:
                healthy.append({
                    "url": link["url"],
                    "publisher_host": (link["url"].split("/") + [""])[2],
                    "retrieved_at": probe.retrieved_at,
                    "fingerprint": probe.fingerprint,
                })
        scope = {
            "sampled": True,
            "citation_links": len(citations),
            "urls_checked": checked,
            "semantic_claim_comparison": "out_of_scope_v1",
        }
        observed = {
            "failures": failures[:25],
            "blocked": unknowns[:25],
            "healthy_sources": healthy[:25],
        }
        common = {
            "check_id": "source_support.link_health", "section": _SECTION,
            "subject": page.subject, "expected": _EXPECTED,
            "observed": observed, "evidence_refs": tuple(refs[:30]),
            "applicability_reason": "Page content cites external sources",
            "scope": scope,
        }
        if failures:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="medium",
                    summary="Citation links point to dead sources",
                    instruction=(
                        "Replace each dead source with the current equivalent from the"
                        " original publisher; preserve the page's citation style"
                    ),
                    remediation_id="sources.repair_citations",
                )
            )
        elif unknowns or checked == 0:
            results.append(
                unknown_result(
                    check_id="source_support.link_health", section=_SECTION,
                    subject=page.subject, expected=_EXPECTED,
                    observed=observed, evidence_refs=tuple(refs[:30]),
                    applicability_reason="Page content cites external sources",
                    instruction="Retry the blocked sources; access could not be verified",
                    scope=scope,
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary="Existing citation links resolve to retrievable sources",
                    instruction="No action required",
                )
            )
    return results
