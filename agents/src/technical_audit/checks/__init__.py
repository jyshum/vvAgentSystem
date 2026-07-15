from ..registry import CheckDefinition, CheckRegistry
from .canonical import evaluate_canonical
from .llms_txt import evaluate_llms_txt
from .metadata import evaluate_meta_description, evaluate_meta_title
from .freshness import evaluate_freshness
from .integrations import evaluate_bing, evaluate_gsc_sitemap
from .performance import evaluate_crux, evaluate_lcp_image, evaluate_lighthouse
from .images import evaluate_alt_text, evaluate_image_integrity
from .links import evaluate_external_links, evaluate_internal_links
from .robots import evaluate_robots_access, evaluate_robots_integrity
from .source_support import evaluate_source_support
from .schema_markup import evaluate_schema_coverage, evaluate_schema_integrity
from .sitemap import (
    evaluate_sitemap_coverage,
    evaluate_sitemap_discovery,
    evaluate_sitemap_entry_health,
    evaluate_sitemap_integrity,
)
from .tls import (
    evaluate_https_redirect,
    evaluate_mixed_content,
    evaluate_tls_certificate,
)


CHECK_SET_ORDER = ("foundation", "protocol", "site_integrity", "performance")

_CHECK_SETS: dict[str, tuple[CheckDefinition, ...]] = {
    "foundation": (
        CheckDefinition("llms_txt.integrity", 1, "llms_txt", "site", evaluate_llms_txt),
        CheckDefinition("meta_title.integrity", 1, "meta_title", "page", evaluate_meta_title),
        CheckDefinition(
            "meta_description.integrity", 1, "meta_description", "page",
            evaluate_meta_description,
        ),
        CheckDefinition("canonical.integrity", 1, "canonical_url", "page", evaluate_canonical),
    ),
    "protocol": (
        CheckDefinition("robots_txt.integrity", 1, "robots_txt", "site", evaluate_robots_integrity),
        CheckDefinition("robots_txt.access", 1, "robots_txt", "site", evaluate_robots_access),
        CheckDefinition("sitemap.discovery", 1, "sitemap", "site", evaluate_sitemap_discovery),
        CheckDefinition("sitemap.integrity", 1, "sitemap", "site", evaluate_sitemap_integrity),
        CheckDefinition("sitemap.coverage", 1, "sitemap", "site", evaluate_sitemap_coverage),
        CheckDefinition(
            "sitemap.entry_health", 1, "sitemap", "site", evaluate_sitemap_entry_health
        ),
        CheckDefinition("tls.certificate", 1, "ssl_https", "site", evaluate_tls_certificate),
        CheckDefinition("tls.https_redirect", 1, "ssl_https", "site", evaluate_https_redirect),
        CheckDefinition("tls.mixed_content", 1, "ssl_https", "page", evaluate_mixed_content),
        CheckDefinition("schema.integrity", 1, "schema_markup", "page", evaluate_schema_integrity),
        CheckDefinition("schema.coverage", 1, "schema_markup", "page", evaluate_schema_coverage),
    ),
    "site_integrity": (
        CheckDefinition("links.internal_health", 1, "broken_links", "page", evaluate_internal_links),
        CheckDefinition("links.external_health", 1, "broken_links", "site", evaluate_external_links),
        CheckDefinition("images.integrity", 1, "image_optimization", "page", evaluate_image_integrity),
        CheckDefinition("images.alt_text", 1, "image_optimization", "page", evaluate_alt_text),
        CheckDefinition("freshness.dates", 1, "freshness", "page", evaluate_freshness),
        CheckDefinition(
            "source_support.link_health", 1, "source_citations", "page",
            evaluate_source_support,
        ),
    ),
    "performance": (
        CheckDefinition("performance.crux", 1, "page_speed", "page", evaluate_crux),
        CheckDefinition("performance.lighthouse", 1, "page_speed", "page", evaluate_lighthouse),
        CheckDefinition("performance.lcp_image", 1, "page_speed", "page", evaluate_lcp_image),
        CheckDefinition(
            "integration.gsc_sitemap", 1, "search_integrations", "site",
            evaluate_gsc_sitemap,
        ),
        CheckDefinition("integration.bing", 1, "search_integrations", "site", evaluate_bing),
    ),
}


def registered_check_sets() -> tuple[str, ...]:
    return tuple(name for name in CHECK_SET_ORDER if name in _CHECK_SETS)


def register_check_set(name: str, definitions: tuple[CheckDefinition, ...]) -> None:
    if name not in CHECK_SET_ORDER:
        raise ValueError(f"unknown check set name: {name}")
    _CHECK_SETS[name] = definitions


def build_v1_registry(
    enabled_check_sets: tuple[str, ...] = ("foundation",),
) -> CheckRegistry:
    unsupported = [name for name in enabled_check_sets if name not in _CHECK_SETS]
    if not enabled_check_sets or unsupported:
        raise ValueError(
            f"Unsupported technical audit check sets: {tuple(enabled_check_sets)}"
        )
    registry = CheckRegistry()
    for set_name in CHECK_SET_ORDER:
        if set_name not in enabled_check_sets:
            continue
        for definition in _CHECK_SETS[set_name]:
            registry.register(definition)
    return registry


__all__ = ["build_v1_registry", "register_check_set", "registered_check_sets", "CHECK_SET_ORDER"]
