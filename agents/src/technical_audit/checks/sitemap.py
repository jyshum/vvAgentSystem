from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

from ..evidence.sitemaps import parse_lastmod
from ..models import AuditContext, AuditStatus, CheckResult
from ._common import build_result, unknown_result

ENTRY_HEALTH_SAMPLE = 10

_SECTION = "sitemap"


def _site_subject(context: AuditContext) -> str:
    return context.pages[0].subject if context.pages else f"https://{context.domain}/"


def _documents(context: AuditContext):
    return tuple(context.site_observations.get("sitemaps") or ())


def _healthy(documents):
    return [
        doc
        for doc in documents
        if int(doc.data.get("status_code") or 0) == 200
        and doc.data.get("sitemap_kind") in {"urlset", "index"}
        and not doc.data.get("parse_error")
    ]


def evaluate_sitemap_discovery(context: AuditContext) -> list[CheckResult]:
    subject = _site_subject(context)
    documents = _documents(context)
    expected = "A sitemap is discoverable at a conventional or robots-declared location"
    reason = "Sitemap discovery applies to every public site"
    observed = {
        "locations_checked": [doc.data.get("request_url") for doc in documents],
        "statuses": [int(doc.data.get("status_code") or 0) for doc in documents],
    }
    refs = tuple(doc.id for doc in documents)
    healthy = _healthy(documents)
    if healthy:
        return [
            build_result(
                check_id="sitemap.discovery", section=_SECTION, subject=subject,
                status=AuditStatus.PASS, severity="low",
                summary="A valid sitemap was discovered",
                expected=expected, observed=observed, evidence_refs=refs,
                applicability_reason=reason, instruction="No action required",
            )
        ]
    blocked = [
        doc for doc in documents
        if doc.data.get("error")
        or int(doc.data.get("status_code") or 0) in {0, 403, 429}
        or int(doc.data.get("status_code") or 0) >= 500
    ]
    if blocked:
        return [
            unknown_result(
                check_id="sitemap.discovery", section=_SECTION, subject=subject,
                expected=expected, observed=observed, evidence_refs=refs,
                applicability_reason=reason,
                instruction="Retry the blocked sitemap request or inspect host access controls",
            )
        ]
    return [
        build_result(
            check_id="sitemap.discovery", section=_SECTION, subject=subject,
            status=AuditStatus.REVIEW, severity="medium",
            summary="No sitemap was found at conventional or declared locations",
            expected=expected, observed=observed, evidence_refs=refs,
            applicability_reason=reason,
            instruction=(
                "Confirm whether this platform publishes a sitemap; enable or declare"
                " one through the platform's page settings if intended"
            ),
            remediation_id="sitemap.enable",
        )
    ]


def _entry_defects(doc, context, run_at):
    defects = []
    for entry in doc.data.get("entries", []):
        loc = entry.get("loc") or ""
        parts = urlsplit(loc)
        if not parts.scheme or not parts.hostname:
            defects.append({"loc": loc, "defect": "relative or schemeless URL"})
            continue
        if parts.scheme.lower() not in {"http", "https"}:
            defects.append({"loc": loc, "defect": "unsupported scheme"})
            continue
        if (parts.hostname or "").lower() not in context.site_identity.allowed_hosts:
            defects.append({"loc": loc, "defect": "URL outside the sitemap host scope"})
        lastmod = entry.get("lastmod")
        if lastmod:
            parsed = parse_lastmod(lastmod)
            if parsed is None:
                defects.append({"loc": loc, "defect": f"invalid lastmod '{lastmod}'"})
            elif parsed > run_at:
                defects.append({"loc": loc, "defect": f"future-dated lastmod '{lastmod}'"})
    return defects


def evaluate_sitemap_integrity(context: AuditContext) -> list[CheckResult]:
    documents = [
        doc for doc in _documents(context)
        if int(doc.data.get("status_code") or 0) == 200
    ]
    expected = "Retrieved sitemaps are valid XML with absolute, in-scope, credibly dated URLs"
    if not documents:
        return [
            CheckResult.not_applicable(
                check_id="sitemap.integrity", check_version=1, section=_SECTION,
                subject=_site_subject(context),
                reason="No sitemap document was retrieved to validate",
            )
        ]
    run_at = datetime.fromisoformat(context.run_timestamp)
    results = []
    for doc in documents:
        subject = doc.data.get("final_url") or doc.subject
        mime = (doc.data.get("content_type") or "").split(";", 1)[0].strip().lower()
        common = {
            "check_id": "sitemap.integrity", "section": _SECTION, "subject": subject,
            "expected": expected, "evidence_refs": (doc.id,),
            "applicability_reason": "A published sitemap must be machine-readable",
        }
        if doc.data.get("parse_error") or doc.data.get("sitemap_kind") == "invalid" or mime in {"text/html", "application/xhtml+xml"}:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="high",
                    summary="Sitemap is not a valid XML sitemap document",
                    observed={
                        "content_type": doc.data.get("content_type"),
                        "parse_error": doc.data.get("parse_error"),
                    },
                    instruction=(
                        "Correct the page/platform setting that generates this sitemap;"
                        " never hand-edit generated XML"
                    ),
                    remediation_id="sitemap.correct_source",
                )
            )
            continue
        defects = _entry_defects(doc, context, run_at)
        scope = {
            "sampled": bool(doc.data.get("entries_truncated")),
            "urls_checked": len(doc.data.get("entries", [])),
        }
        if defects:
            results.append(
                build_result(
                    **common, status=AuditStatus.FAIL, severity="high",
                    summary="Sitemap entries violate sitemap protocol rules",
                    observed={"defects": defects[:25]}, scope=scope,
                    instruction=(
                        "Fix the listed entries through the authoritative page settings"
                    ),
                    remediation_id="sitemap.correct_source",
                )
            )
        else:
            results.append(
                build_result(
                    **common, status=AuditStatus.PASS, severity="low",
                    summary="Sitemap document is valid",
                    observed={
                        "entries": len(doc.data.get("entries", [])),
                        "children": len(doc.data.get("child_locs", [])),
                    },
                    scope=scope, instruction="No action required",
                )
            )
    return results


def _all_entry_locs(context: AuditContext) -> list[str]:
    locs = []
    for doc in _healthy(_documents(context)):
        for entry in doc.data.get("entries", []):
            if entry.get("loc"):
                locs.append(entry["loc"].rstrip("/").lower())
    return locs


def evaluate_sitemap_coverage(context: AuditContext) -> list[CheckResult]:
    subject = _site_subject(context)
    healthy = _healthy(_documents(context))
    expected = "The homepage and primary collected pages appear in the sitemap"
    if not healthy:
        return [
            CheckResult.not_applicable(
                check_id="sitemap.coverage", check_version=1, section=_SECTION,
                subject=subject, reason="No valid sitemap exists to check coverage against",
            )
        ]
    locs = set(_all_entry_locs(context))
    refs = tuple(doc.id for doc in healthy)
    homepage = context.pages[0].subject.rstrip("/").lower() if context.pages else ""
    missing_pages = [
        page.subject
        for page in context.pages[1:]
        if page.data.get("is_html")
        and page.data.get("available")
        and "noindex" not in set(page.data.get("robots_directives", []))
        and page.subject.rstrip("/").lower() not in locs
    ]
    observed = {
        "sitemap_entries": len(locs),
        "homepage_listed": homepage in locs,
        "collected_pages_missing": missing_pages[:10],
    }
    common = {
        "check_id": "sitemap.coverage", "section": _SECTION, "subject": subject,
        "expected": expected, "observed": observed, "evidence_refs": refs,
        "applicability_reason": "The site publishes a sitemap, so key pages should be listed",
        "scope": {"sampled": True, "urls_checked": len(context.pages)},
    }
    if homepage and homepage not in locs:
        return [
            build_result(
                **common, status=AuditStatus.FAIL, severity="high",
                summary="The homepage is missing from the sitemap",
                instruction="Correct the page visibility/indexability setting so the homepage is listed",
                remediation_id="sitemap.correct_source",
            )
        ]
    if missing_pages:
        return [
            build_result(
                **common, status=AuditStatus.REVIEW, severity="medium",
                summary="Some collected public pages are not listed in the sitemap",
                instruction="Confirm the missing pages are intentionally excluded from the sitemap",
            )
        ]
    return [
        build_result(
            **common, status=AuditStatus.PASS, severity="low",
            summary="Key collected pages are listed in the sitemap",
            instruction="No action required",
        )
    ]


def evaluate_sitemap_entry_health(context: AuditContext) -> list[CheckResult]:
    subject = _site_subject(context)
    healthy = _healthy(_documents(context))
    expected = "Sampled sitemap entries resolve directly to indexable 200 pages"
    if not healthy:
        return [
            CheckResult.not_applicable(
                check_id="sitemap.entry_health", check_version=1, section=_SECTION,
                subject=subject, reason="No valid sitemap exists to sample entries from",
            )
        ]
    refs = tuple(doc.id for doc in healthy)
    sample = []
    for doc in healthy:
        for entry in doc.data.get("entries", []):
            if entry.get("loc"):
                sample.append(entry["loc"])
            if len(sample) >= ENTRY_HEALTH_SAMPLE:
                break
        if len(sample) >= ENTRY_HEALTH_SAMPLE:
            break

    collected = {page.subject.rstrip("/").lower(): page for page in context.pages}
    failures, unknowns, checked = [], [], 0
    for loc in sample:
        page = collected.get(loc.rstrip("/").lower())
        if page is None:
            continue
        checked += 1
        status_code = int(page.data.get("status_code") or 0)
        chain = page.data.get("redirect_chain") or []
        if status_code in {404, 410} or status_code >= 500:
            failures.append({"loc": loc, "defect": f"status {status_code}"})
        elif len(chain) > 1:
            failures.append({"loc": loc, "defect": "sitemap entry redirects"})
        elif status_code in {403, 429} or page.data.get("fetch_error"):
            unknowns.append({"loc": loc, "status": status_code, "error": page.data.get("fetch_error")})
        elif "noindex" in set(page.data.get("robots_directives", [])):
            failures.append({"loc": loc, "defect": "sitemap entry is marked noindex"})
    scope = {"sampled": True, "urls_checked": checked, "sample_size": len(sample)}
    observed = {"failures": failures, "blocked": unknowns, "sampled": sample}
    common = {
        "check_id": "sitemap.entry_health", "section": _SECTION, "subject": subject,
        "expected": expected, "observed": observed, "evidence_refs": refs,
        "applicability_reason": "The sitemap asserts these URLs are canonical and healthy",
        "scope": scope,
    }
    if failures:
        return [
            build_result(
                **common, status=AuditStatus.FAIL, severity="high",
                summary="Sampled sitemap entries are redirected, missing, or excluded",
                instruction=(
                    "Fix the underlying page settings so sitemap entries resolve"
                    " directly to indexable 200 pages"
                ),
                remediation_id="sitemap.correct_source",
            )
        ]
    if unknowns or checked == 0:
        return [
            unknown_result(
                check_id="sitemap.entry_health", section=_SECTION, subject=subject,
                expected=expected, observed=observed, evidence_refs=refs,
                applicability_reason="The sitemap asserts these URLs are canonical and healthy",
                instruction=(
                    "Retry the blocked entries or extend the crawl so sampled sitemap"
                    " entries are collected"
                ),
                scope=scope,
            )
        ]
    return [
        build_result(
            **common, status=AuditStatus.PASS, severity="low",
            summary="Sampled sitemap entries resolve directly and are indexable",
            instruction="No action required",
        )
    ]
