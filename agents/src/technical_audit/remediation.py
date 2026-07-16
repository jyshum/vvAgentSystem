from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RemediationEntry:
    remediation_id: str
    risk: str  # "low" | "medium" | "high"
    build_guidance: Callable[[dict[str, Any], str], dict[str, Any]]


_SQS = "squarespace"


def _generic(title: str, steps: list[str]) -> dict[str, Any]:
    return {"title": title, "instructions": steps, "copy_values": {}}


def _guidance_meta_title(result: dict, platform: str) -> dict[str, Any]:
    subject = result.get("subject", "")
    steps = (
        [
            f"Open the page {subject} in Squarespace.",
            "Open Page Settings → SEO and edit the SEO Title field only.",
            "Do not change the visible page or navigation title.",
            "Save and republish the page.",
        ]
        if platform == _SQS
        else [
            f"Edit the SEO/meta title for {subject} in the platform's page settings.",
            "Keep the visible heading unchanged.",
        ]
    )
    return _generic("Correct the SEO title", steps)


def _guidance_meta_description(result: dict, platform: str) -> dict[str, Any]:
    subject = result.get("subject", "")
    steps = (
        [
            f"Open the page {subject} in Squarespace.",
            "Open Page Settings → SEO and edit the SEO Description field.",
            "Describe the page accurately from its visible content; do not invent claims.",
            "Preview the social share appearance before saving.",
        ]
        if platform == _SQS
        else [
            f"Edit the meta description for {subject} in the platform's SEO settings.",
            "Describe the page accurately from its visible content.",
        ]
    )
    return _generic("Correct the meta description", steps)


def _guidance_canonical(result: dict, platform: str) -> dict[str, Any]:
    steps = (
        [
            "Squarespace generates canonical URLs from the page URL slug and domain settings.",
            "Check Settings → Domains for the correct primary domain.",
            "Correct the page's URL slug in Page Settings if the canonical target is wrong.",
            "Never inject a manual canonical tag that conflicts with the generated one.",
        ]
        if platform == _SQS
        else ["Correct the canonical URL through the platform's authoritative setting."]
    )
    return _generic("Correct the canonical URL", steps)


def _guidance_robots(result: dict, platform: str) -> dict[str, Any]:
    steps = (
        [
            "Open Squarespace Settings → Crawlers (or SEO → Crawlers).",
            "Allow the listed AI/search crawlers; keep intentional private exclusions.",
            "Squarespace generates robots.txt — never hand-edit or proxy the file.",
        ]
        if platform == _SQS
        else [
            "Adjust the robots policy minimally so the listed crawlers can reach the blocked public URLs.",
            "Preserve intentional private/admin exclusions.",
        ]
    )
    return _generic("Adjust the robots policy", steps)


def _guidance_sitemap(result: dict, platform: str) -> dict[str, Any]:
    steps = (
        [
            "Squarespace generates /sitemap.xml automatically; never edit the XML.",
            "Fix the underlying page: check Page Settings → SEO → 'Hide from search results',"
            " the page's URL slug, and whether the page is public.",
            "Republish and re-check the sitemap after a few minutes.",
        ]
        if platform == _SQS
        else [
            "Fix the page/platform setting that generates the sitemap entry;"
            " never hand-edit generated XML.",
        ]
    )
    return _generic("Correct the sitemap through page settings", steps)


def _guidance_tls(result: dict, platform: str) -> dict[str, Any]:
    steps = (
        [
            "Open Squarespace Settings → Domains → select the domain → SSL.",
            "Ensure SSL is set to 'Secure' and the certificate has renewed.",
            "If the domain is external, verify its DNS records point at Squarespace.",
        ]
        if platform == _SQS
        else ["Renew or correct the certificate and HTTPS redirect through the host's SSL controls."]
    )
    return _generic("Fix SSL/HTTPS through the domain settings", steps)


def _guidance_mixed_content(result: dict, platform: str) -> dict[str, Any]:
    all_urls = (result.get("observed") or {}).get("active_http_urls", [])
    steps = [
        "Update each listed resource to load over https://.",
        "If a resource belongs to an embedded business integration, review it with"
        " the business before removing it.",
        "Never blindly replace every http:// string on the site.",
    ]
    guidance = _generic("Serve active content over HTTPS", steps)
    guidance["copy_values"] = {
        "insecure_urls": all_urls[:10],
        "insecure_urls_total": len(all_urls),
    }
    return guidance


def _guidance_schema(result: dict, platform: str) -> dict[str, Any]:
    steps = (
        [
            "Squarespace injects basic structured data automatically.",
            "For custom JSON-LD, use Page Settings → Advanced → Page Header Code Injection"
            " (requires a plan that supports code injection).",
            "Correct only the defects listed in the finding; never invent authors, dates,"
            " or business facts.",
        ]
        if platform == _SQS
        else [
            "Correct the structured data at its source.",
            "Never invent authors, dates, locations, or business facts.",
        ]
    )
    return _generic("Correct the structured data", steps)


def _guidance_links(result: dict, platform: str) -> dict[str, Any]:
    all_failures = (result.get("observed") or {}).get("failures", [])
    steps = [
        "For each listed destination: fix the typo, point to the current equivalent,"
        " or repair the redirect.",
        "Only remove a link after review when no replacement exists.",
    ]
    guidance = _generic("Repair the broken links", steps)
    guidance["copy_values"] = {
        "broken": all_failures[:10],
        "broken_total": len(all_failures),
    }
    return guidance


def _guidance_images(result: dict, platform: str) -> dict[str, Any]:
    steps = (
        [
            "Open the affected image blocks in the Squarespace editor.",
            "Re-upload broken images; fill the image Description (alt text) for informative"
            " images, or leave it empty for purely decorative ones.",
        ]
        if platform == _SQS
        else [
            "Re-upload broken images and set appropriate alt text in the editor.",
        ]
    )
    return _generic("Fix the affected images", steps)


def _guidance_freshness(result: dict, platform: str) -> dict[str, Any]:
    return _generic(
        "Correct the declared dates",
        [
            "Fix the listed invalid/misordered dates at their source (page settings or schema).",
            "Never change a date without a meaningful content update.",
        ],
    )


def _guidance_sources(result: dict, platform: str) -> dict[str, Any]:
    all_failures = (result.get("observed") or {}).get("failures", [])
    guidance = _generic(
        "Repair the dead citations",
        [
            "Replace each dead source with the current equivalent from the original publisher.",
            "Link the relevant human-readable words; preserve the page's citation style.",
        ],
    )
    guidance["copy_values"] = {
        "dead_sources": all_failures[:10],
        "dead_sources_total": len(all_failures),
    }
    return guidance


def _guidance_performance(result: dict, platform: str) -> dict[str, Any]:
    return _generic(
        "Investigate the performance diagnostic",
        [
            "Open the Lighthouse lab diagnostic for the failing metric's root causes.",
            "Group template-level causes; never automatically remove analytics, consent,"
            " booking, payment, accessibility, fonts, scripts, or layout behavior.",
        ],
    )


def _guidance_gsc(result: dict, platform: str) -> dict[str, Any]:
    return _generic(
        "Update Search Console sitemaps",
        [
            "Open Search Console → Sitemaps for the configured property.",
            "Submit the discovered sitemap URL or fix the reported processing errors.",
        ],
    )


def _guidance_bing(result: dict, platform: str) -> dict[str, Any]:
    return _generic(
        "Submit the sitemap to Bing",
        [
            "Open Bing Webmaster Tools for the site.",
            "Submit the discovered sitemap URL under Sitemaps.",
        ],
    )


def _guidance_llms(result: dict, platform: str) -> dict[str, Any]:
    return _generic(
        "Correct the llms.txt file",
        [
            "Fix the defects listed in the finding on the served /llms.txt file.",
            "Do not build proxy infrastructure to force root-file support on platforms"
            " that cannot serve one.",
        ],
    )


CATALOGUE: dict[str, RemediationEntry] = {
    "meta_title.correct": RemediationEntry("meta_title.correct", "low", _guidance_meta_title),
    "meta_description.correct": RemediationEntry("meta_description.correct", "low", _guidance_meta_description),
    "canonical.correct": RemediationEntry("canonical.correct", "medium", _guidance_canonical),
    "llms_txt.correct": RemediationEntry("llms_txt.correct", "low", _guidance_llms),
    "robots.correct_policy": RemediationEntry("robots.correct_policy", "medium", _guidance_robots),
    "robots.allow_configured_crawlers": RemediationEntry("robots.allow_configured_crawlers", "medium", _guidance_robots),
    "sitemap.enable": RemediationEntry("sitemap.enable", "low", _guidance_sitemap),
    "sitemap.correct_source": RemediationEntry("sitemap.correct_source", "medium", _guidance_sitemap),
    "tls.fix_certificate": RemediationEntry("tls.fix_certificate", "high", _guidance_tls),
    "tls.fix_http_redirect": RemediationEntry("tls.fix_http_redirect", "high", _guidance_tls),
    "tls.fix_mixed_content": RemediationEntry("tls.fix_mixed_content", "medium", _guidance_mixed_content),
    "schema.correct_markup": RemediationEntry("schema.correct_markup", "medium", _guidance_schema),
    "schema.add_homepage_coverage": RemediationEntry("schema.add_homepage_coverage", "low", _guidance_schema),
    "links.repair_internal": RemediationEntry("links.repair_internal", "low", _guidance_links),
    "links.repair_external": RemediationEntry("links.repair_external", "low", _guidance_links),
    "images.repair": RemediationEntry("images.repair", "low", _guidance_images),
    "images.add_alt_text": RemediationEntry("images.add_alt_text", "low", _guidance_images),
    "freshness.correct_dates": RemediationEntry("freshness.correct_dates", "medium", _guidance_freshness),
    "sources.repair_citations": RemediationEntry("sources.repair_citations", "medium", _guidance_sources),
    "performance.improve_cwv": RemediationEntry("performance.improve_cwv", "high", _guidance_performance),
    "performance.improve_lab": RemediationEntry("performance.improve_lab", "high", _guidance_performance),
    "performance.fix_lcp_image": RemediationEntry("performance.fix_lcp_image", "medium", _guidance_performance),
    "integrations.fix_gsc_sitemap": RemediationEntry("integrations.fix_gsc_sitemap", "low", _guidance_gsc),
    "integrations.submit_gsc_sitemap": RemediationEntry("integrations.submit_gsc_sitemap", "low", _guidance_gsc),
    "integrations.submit_bing_sitemap": RemediationEntry("integrations.submit_bing_sitemap", "low", _guidance_bing),
}


def build_guidance(result: dict[str, Any], platform: str) -> dict[str, Any] | None:
    """Deterministic platform guidance for a finding, or None when the
    remediation is unavailable (the finding itself stays fully visible)."""
    remediation_id = result.get("remediation_id")
    entry = CATALOGUE.get(remediation_id or "")
    if entry is None:
        return None
    guidance = entry.build_guidance(result, platform.strip().lower())
    guidance["remediation_id"] = entry.remediation_id
    guidance["risk"] = entry.risk
    guidance["mode"] = "guided"
    return guidance
