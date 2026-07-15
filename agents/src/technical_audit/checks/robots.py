from __future__ import annotations

from ..evidence.robots import (
    CRAWLER_REGISTRY_VERSION,
    RELEVANT_CRAWLERS,
    blocked_targets,
    is_html_fallback,
    parse_robots,
)
from ..models import AuditContext, AuditStatus, CheckResult
from ._common import build_result, unknown_result

MAX_ACCESS_SAMPLE = 10

_EXPECTED_INTEGRITY = (
    "robots.txt returns a real text policy (or is absent), never an HTML fallback"
)
_EXPECTED_ACCESS = (
    "Configured AI/search crawlers can fetch the homepage, sampled public pages,"
    " and the sitemap"
)


def _site_subject(context: AuditContext) -> str:
    return context.pages[0].subject if context.pages else f"https://{context.domain}/"


def _public_sample(context: AuditContext) -> list[str]:
    sample = []
    for page in context.pages:
        data = page.data
        if not data.get("available", False) or not data.get("is_html", False):
            continue
        directives = set(data.get("robots_directives", []))
        if "noindex" in directives or "none" in directives:
            continue
        sample.append(page.subject)
        if len(sample) >= MAX_ACCESS_SAMPLE:
            break
    return sample


def evaluate_robots_integrity(context: AuditContext) -> list[CheckResult]:
    subject = _site_subject(context)
    robots = context.site_observations.get("robots_txt")
    if robots is None:
        return [
            unknown_result(
                check_id="robots_txt.integrity",
                section="robots_txt",
                subject=subject,
                expected=_EXPECTED_INTEGRITY,
                observed={"collected": False},
                evidence_refs=(),
                applicability_reason="Every production site has observable robots behavior",
                instruction="Re-run collection with the protocol evidence layer enabled",
            )
        ]

    data = robots.data
    status_code = int(data.get("status_code") or 0)
    body = data.get("body") or ""
    content_type = data.get("content_type") or ""
    observed = {
        "status_code": status_code,
        "content_type": content_type,
        "final_url": data.get("final_url"),
        "error": data.get("error"),
    }
    common = {
        "check_id": "robots_txt.integrity",
        "section": "robots_txt",
        "subject": data.get("final_url") or subject,
        "expected": _EXPECTED_INTEGRITY,
        "observed": observed,
        "evidence_refs": (robots.id,),
        "applicability_reason": "Every production site has observable robots behavior",
    }

    if data.get("error") or status_code in {403, 429} or status_code >= 500 or status_code == 0:
        return [
            unknown_result(
                **{k: v for k, v in common.items()},
                instruction="Retry the robots.txt request or inspect host access controls",
            )
        ]
    if status_code == 404:
        return [
            build_result(
                **common,
                status=AuditStatus.PASS,
                severity="low",
                summary="robots.txt is absent; crawling is semantically allowed (advisory)",
                instruction="No action required; adding a robots.txt with a sitemap declaration is optional",
            )
        ]
    if status_code == 200 and is_html_fallback(content_type, body):
        return [
            build_result(
                **common,
                status=AuditStatus.FAIL,
                severity="high",
                summary="robots.txt returns an HTML fallback instead of a text policy",
                instruction="Serve a plain-text robots policy from the platform's robots control",
                remediation_id="robots.correct_policy",
            )
        ]
    if status_code == 200:
        parse_robots(body)
        return [
            build_result(
                **common,
                status=AuditStatus.PASS,
                severity="low",
                summary="robots.txt returns a parseable text policy",
                instruction="No action required",
            )
        ]
    return [
        build_result(
            **common,
            status=AuditStatus.REVIEW,
            severity="medium",
            summary=f"robots.txt returned unexpected status {status_code}",
            instruction="Confirm the robots.txt response is intentional for this platform",
        )
    ]


def evaluate_robots_access(context: AuditContext) -> list[CheckResult]:
    subject = _site_subject(context)
    robots = context.site_observations.get("robots_txt")
    scope = {
        "sampled": True,
        "crawlers": list(RELEVANT_CRAWLERS),
        "crawler_registry_version": CRAWLER_REGISTRY_VERSION,
        "delivery_confirmed": False,
    }
    if robots is None:
        return [
            unknown_result(
                check_id="robots_txt.access",
                section="robots_txt",
                subject=subject,
                expected=_EXPECTED_ACCESS,
                observed={"collected": False},
                evidence_refs=(),
                applicability_reason="Crawler access policy applies to every public site",
                instruction="Re-run collection with the protocol evidence layer enabled",
                scope=scope,
            )
        ]

    data = robots.data
    status_code = int(data.get("status_code") or 0)
    if data.get("error") or status_code in {403, 429} or status_code >= 500 or status_code == 0:
        return [
            unknown_result(
                check_id="robots_txt.access",
                section="robots_txt",
                subject=subject,
                expected=_EXPECTED_ACCESS,
                observed={"status_code": status_code, "error": data.get("error")},
                evidence_refs=(robots.id,),
                applicability_reason="Crawler access policy applies to every public site",
                instruction="Retry the robots.txt request; access cannot be evaluated without the policy",
                scope=scope,
            )
        ]

    targets = _public_sample(context)
    sitemaps = context.site_observations.get("sitemaps") or ()
    sitemap_urls = [
        item.data.get("final_url")
        for item in sitemaps
        if int(item.data.get("status_code") or 0) == 200
    ]
    checked = tuple(targets + [url for url in sitemap_urls if url])
    scope = {**scope, "urls_checked": len(checked)}

    body = data.get("body") or "" if status_code == 200 else ""
    blocked = blocked_targets(body, checked) if checked else []
    observed = {
        "status_code": status_code,
        "blocked": blocked[:50],
        "urls_checked": len(checked),
        "note": "Synthetic evaluation of the published policy; real WAF/CDN delivery is not confirmed",
    }
    common = {
        "check_id": "robots_txt.access",
        "section": "robots_txt",
        "subject": subject,
        "expected": _EXPECTED_ACCESS,
        "observed": observed,
        "evidence_refs": (robots.id,),
        "applicability_reason": "Crawler access policy applies to every public site",
        "scope": scope,
    }

    blocked_public = [
        item for item in blocked if item["url"] in set(targets) or item["url"] in set(sitemap_urls)
    ]
    if blocked_public:
        return [
            build_result(
                **common,
                status=AuditStatus.FAIL,
                severity="high",
                summary="The robots policy blocks configured crawlers from public pages",
                instruction=(
                    "Adjust the robots policy minimally so listed crawlers can reach the"
                    " blocked public URLs while preserving intentional private exclusions"
                ),
                remediation_id="robots.allow_configured_crawlers",
            )
        ]
    return [
        build_result(
            **common,
            status=AuditStatus.PASS,
            severity="low",
            summary="Configured crawlers can access the sampled public pages and sitemap",
            instruction="No action required",
        )
    ]
