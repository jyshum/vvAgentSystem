from __future__ import annotations

from protego import Protego


CRAWLER_REGISTRY_VERSION = 1

# Versioned registry of crawlers the product cares about: search plus the
# AI crawlers configured across tracked engines. Changing this list is a
# registry version bump, not a silent edit.
RELEVANT_CRAWLERS: tuple[str, ...] = (
    "Googlebot",
    "Bingbot",
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "ClaudeBot",
    "Claude-User",
    "Google-Extended",
    "CCBot",
)


def parse_robots(body: str) -> Protego:
    return Protego.parse(body)


def is_html_fallback(content_type: str, body: str) -> bool:
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if mime in {"text/html", "application/xhtml+xml"}:
        return True
    stripped = body.lstrip().lower()
    return stripped.startswith("<!doctype") or stripped.startswith("<html")


def blocked_targets(
    body: str,
    urls: tuple[str, ...],
    crawlers: tuple[str, ...] = RELEVANT_CRAWLERS,
) -> list[dict[str, str]]:
    """Deterministic effective-access evaluation: which relevant crawlers are
    denied which of the given URLs by this robots policy."""
    policy = parse_robots(body)
    blocked = []
    for crawler in crawlers:
        for url in urls:
            if not policy.can_fetch(url, crawler):
                blocked.append({"crawler": crawler, "url": url})
    return blocked
