"""Post-implementation verification — re-fetch the page after publishing and
confirm the change is live and nothing broke.

Checks:
- page_renders: HTTP < 400, response has <body> and <title>
- change_present: schema cards → a JSON-LD block with the card's @type exists;
  content cards → after_text (first 200 chars, normalized) appears in page text

The result is advisory: it's stored on the card for the dashboard, it never
rolls anything back on its own.
"""

import json
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; VV-Verify/1.0)"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_schema_types(soup: BeautifulSoup) -> set[str]:
    types: set[str] = set()
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            if not isinstance(block, dict):
                continue
            t = block.get("@type")
            if isinstance(t, list):
                types.update(t)
            elif t:
                types.add(t)
    return types


def verify_implementation(card: dict, timeout: float = 15.0) -> dict:
    """Verify one implemented card against the live page."""
    result = {
        "verified": False,
        "skipped": False,
        "checks": {"page_renders": False, "change_present": False},
        "error": None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    url = card.get("page_url")
    if not url:
        result["skipped"] = True
        result["error"] = "card has no page_url"
        return result

    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True,
                         headers={"User-Agent": USER_AGENT})
    except Exception as e:
        result["error"] = str(e)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")
    renders = resp.status_code < 400 and soup.find("body") is not None and soup.find("title") is not None
    result["checks"]["page_renders"] = renders

    change_present = False
    code_block = card.get("code_block") or ""
    after_text = card.get("after_text") or ""

    if code_block:
        try:
            expected = json.loads(code_block)
            expected_type = expected.get("@type") if isinstance(expected, dict) else None
        except json.JSONDecodeError:
            expected_type = None
        if expected_type:
            live_types = _extract_schema_types(soup)
            if isinstance(expected_type, list):
                change_present = any(t in live_types for t in expected_type)
            else:
                change_present = expected_type in live_types
    elif after_text:
        page_text = _normalize(soup.get_text(separator=" "))
        change_present = _normalize(after_text)[:200] in page_text
    result["checks"]["change_present"] = change_present
    result["verified"] = renders and change_present
    return result
