from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from ..models import AuditContext, AuditStatus, CheckResult
from ._common import build_result, probe_disposition, unknown_result

_SECTION = "broken_links"
_EXPECTED_INTERNAL = "Internal links resolve directly to healthy pages"
_EXPECTED_EXTERNAL = "External link destinations remain reachable"

_SOFT_404_MARKERS = ("404", "not found", "page not found")


def _strip_fragment(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def _normalized(url: str) -> str:
    return _strip_fragment(url).rstrip("/").lower()


def _soft_404_title(page) -> bool:
    titles = page.data.get("titles") or []
    return any(
        marker in title.lower() for title in titles for marker in _SOFT_404_MARKERS
    )


def evaluate_internal_links(context: AuditContext) -> list[CheckResult]:
    collected = {_normalized(page.subject): page for page in context.pages}
    results = []
    for page in context.pages:
        data = page.data
        if not data.get("available", True):
            results.append(
                unknown_result(
                    check_id="links.internal_health", section=_SECTION,
                    subject=page.subject, expected=_EXPECTED_INTERNAL,
                    observed={"status_code": data.get("status_code")},
                    evidence_refs=(page.id,),
                    applicability_reason="Audited page retrieval was attempted",
                    instruction="Retry the page request or inspect host access controls",
                )
            )
            continue
        internal_links = [
            link for link in data.get("links", []) if link.get("kind") == "internal"
        ]
        if not data.get("is_html", False) or not internal_links:
            results.append(
                CheckResult.not_applicable(
                    check_id="links.internal_health", check_version=1, section=_SECTION,
                    subject=page.subject, reason="Page has no internal links to verify",
                )
            )
            continue

        failures, reviews, unknowns = [], [], []
        checked = 0
        for link in internal_links:
            target = collected.get(_normalized(link["url"]))
            if target is None:
                continue
            checked += 1
            status_code = int(target.data.get("status_code") or 0)
            chain = target.data.get("redirect_chain") or []
            if status_code in {404, 410} or status_code >= 500:
                failures.append({"url": link["url"], "defect": f"status {status_code}"})
            elif target.data.get("fetch_error") or status_code in {403, 429}:
                unknowns.append({"url": link["url"], "status": status_code})
            elif _soft_404_title(target):
                reviews.append({"url": link["url"], "defect": "possible soft 404 (title)"})
            elif len(chain) > 1 and _normalized(link["url"]) != _normalized(chain[-1]):
                # Only flag when the LINK itself points to a non-final URL that
                # redirects. A link to the page's canonical destination is clean
                # even when the crawler reached that page via a redirect (e.g.
                # entering at the bare domain and 301-ing to www) — that chain
                # describes the crawl entry, not the link's path.
                reviews.append({"url": link["url"], "defect": "unnecessary internal redirect"})
        scope = {
            "sampled": True,
            "links_found": len(internal_links),
            "urls_checked": checked,
            "fragments_checked": False,
        }
        observed = {
            "failures": failures[:25],
            "reviews": reviews[:25],
            "blocked": unknowns[:25],
        }
        common = {
            "check_id": "links.internal_health", "section": _SECTION,
            "subject": page.subject, "expected": _EXPECTED_INTERNAL,
            "observed": observed, "evidence_refs": (page.id,),
            "applicability_reason": "The page links to other pages on this site",
            "scope": scope,
        }
        if failures:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="high",
                    summary="Internal links point to missing or failing pages",
                    instruction=(
                        "Repair each listed link: fix the typo, point to the current"
                        " equivalent, or repair the redirect; do not simply delete links"
                    ),
                    remediation_id="links.repair_internal",
                )
            )
        elif unknowns:
            results.append(
                unknown_result(
                    check_id="links.internal_health", section=_SECTION,
                    subject=page.subject, expected=_EXPECTED_INTERNAL,
                    observed=observed, evidence_refs=(page.id,),
                    applicability_reason="The page links to other pages on this site",
                    instruction="Retry the blocked link targets",
                    scope=scope,
                )
            )
        elif reviews:
            results.append(
                build_result(
                    **common, status=AuditStatus.REVIEW, severity="medium",
                    summary="Internal links redirect or look like soft 404s",
                    instruction="Confirm each listed destination is intentional and current",
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary="Verified internal links resolve directly and healthily",
                    instruction="No action required",
                )
            )
    return results


def evaluate_external_links(context: AuditContext) -> list[CheckResult]:
    subject = context.pages[0].subject if context.pages else f"https://{context.domain}/"
    probes = tuple(context.site_observations.get("external_probes") or ())
    has_external_links = any(
        link.get("kind") == "external"
        for page in context.pages
        for link in page.data.get("links", [])
    )
    if not probes and not has_external_links:
        return [
            CheckResult.not_applicable(
                check_id="links.external_health", check_version=1, section=_SECTION,
                subject=subject, reason="No external links were found on collected pages",
            )
        ]
    failures, unknowns, healthy = [], [], 0
    for probe in probes:
        data = probe.data
        status_code = int(data.get("status_code") or 0)
        error = data.get("error")
        # A recorded redirect is not an error for link health; the final status
        # of the followed chain is what the probe reports.
        probe_error = None if error and "redirect" in str(error) else error
        disposition = probe_disposition(status_code, probe_error)
        if disposition == "fail":
            failures.append({
                "url": data.get("request_url"),
                "defect": f"status {status_code}" if status_code else str(error)[:200],
            })
        elif disposition == "unknown":
            unknowns.append({"url": data.get("request_url"), "status": status_code})
        else:
            healthy += 1
    scope = {
        "sampled": True,
        "urls_checked": len(probes),
        "healthy": healthy,
    }
    refs = tuple(probe.id for probe in probes)[:50]
    observed = {"failures": failures[:25], "blocked": unknowns[:25]}
    common = {
        "check_id": "links.external_health", "section": _SECTION, "subject": subject,
        "expected": _EXPECTED_EXTERNAL, "observed": observed, "evidence_refs": refs,
        "applicability_reason": "Collected pages link to external destinations",
        "scope": scope,
    }
    if failures:
        return [
            build_result(
                **common, status=AuditStatus.FAIL, severity="medium",
                summary="External links point to dead destinations",
                instruction=(
                    "Re-source or update each dead external link; prefer the current"
                    " equivalent before reviewed removal"
                ),
                remediation_id="links.repair_external",
            )
        ]
    if unknowns or not probes:
        return [
            unknown_result(
                check_id="links.external_health", section=_SECTION, subject=subject,
                expected=_EXPECTED_EXTERNAL, observed=observed, evidence_refs=refs,
                applicability_reason="Collected pages link to external destinations",
                instruction="Retry the blocked external destinations",
                scope=scope,
            )
        ]
    return [
        build_result(
            **common, status=AuditStatus.PASS, severity="low",
            summary="Sampled external links are reachable",
            instruction="No action required",
        )
    ]
