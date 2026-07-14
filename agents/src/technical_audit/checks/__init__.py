from ..registry import CheckDefinition, CheckRegistry
from .canonical import evaluate_canonical
from .llms_txt import evaluate_llms_txt
from .metadata import evaluate_meta_description, evaluate_meta_title


def build_v1_registry(
    enabled_check_sets: tuple[str, ...] = ("foundation",),
) -> CheckRegistry:
    if enabled_check_sets != ("foundation",):
        raise ValueError(
            f"Unsupported technical audit check sets: {enabled_check_sets}"
        )
    registry = CheckRegistry()
    registry.register(
        CheckDefinition(
            "llms_txt.integrity", 1, "llms_txt", "site", evaluate_llms_txt
        )
    )
    registry.register(
        CheckDefinition(
            "meta_title.integrity", 1, "meta_title", "page", evaluate_meta_title
        )
    )
    registry.register(
        CheckDefinition(
            "meta_description.integrity",
            1,
            "meta_description",
            "page",
            evaluate_meta_description,
        )
    )
    registry.register(
        CheckDefinition(
            "canonical.integrity", 1, "canonical_url", "page", evaluate_canonical
        )
    )
    return registry


__all__ = ["build_v1_registry"]
