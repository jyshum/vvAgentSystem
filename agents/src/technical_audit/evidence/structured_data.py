from __future__ import annotations

import json
from typing import Any

PLACEHOLDER_MARKERS = ("lorem", "example.com", "changeme", "placeholder", "your company name")


def parse_jsonld(blocks: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """Flatten JSON-LD blocks (arrays and @graph included) into entity dicts.

    Returns (entities, parse_errors). Deterministic: no schema.org vocabulary
    validation, only structural parsing.
    """
    entities: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, block in enumerate(blocks):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError as exc:
            errors.append(f"block {index}: {exc.msg} at position {exc.pos}")
            continue
        items = parsed if isinstance(parsed, list) else [parsed]
        for item in items:
            if not isinstance(item, dict):
                errors.append(f"block {index}: non-object JSON-LD value")
                continue
            graph = item.get("@graph")
            if isinstance(graph, list):
                entities.extend(node for node in graph if isinstance(node, dict))
                remainder = {k: v for k, v in item.items() if k != "@graph"}
                if remainder.get("@type"):
                    entities.append(remainder)
            else:
                entities.append(item)
    return entities, errors


def _types(entity: dict[str, Any]) -> list[str]:
    raw = entity.get("@type")
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, str)]
    return []


def entity_types(entities: list[dict[str, Any]]) -> set[str]:
    found: set[str] = set()
    for entity in entities:
        found.update(_types(entity))
    return found


def _string_values(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_values(item)


def find_placeholders(entities: list[dict[str, Any]]) -> list[str]:
    hits = []
    for entity in entities:
        for value in _string_values(entity):
            lowered = value.lower()
            for marker in PLACEHOLDER_MARKERS:
                if marker in lowered:
                    hits.append(value[:200])
                    break
    return hits


def find_duplicate_entities(entities: list[dict[str, Any]]) -> list[str]:
    """Same @type repeated with the same @id or same normalized name."""
    seen: dict[tuple[str, str], int] = {}
    duplicates = []
    for entity in entities:
        for entity_type in _types(entity):
            identifier = entity.get("@id") or entity.get("name")
            if not isinstance(identifier, str) or not identifier.strip():
                continue
            key = (entity_type, identifier.strip().lower())
            seen[key] = seen.get(key, 0) + 1
            if seen[key] == 2:
                duplicates.append(f"{entity_type}:{identifier.strip()[:100]}")
    return duplicates


def same_site_urls(entities: list[dict[str, Any]], allowed_hosts: frozenset[str]) -> list[str]:
    from urllib.parse import urlsplit

    urls = []
    for entity in entities:
        for value in _string_values(entity):
            if not value.lower().startswith(("http://", "https://")):
                continue
            host = (urlsplit(value).hostname or "").lower()
            if host in allowed_hosts:
                urls.append(value)
    return urls
