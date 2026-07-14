from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import httpx

from .checks import build_v1_registry
from .models import AuditContext, AuditStatus, Observation
from .observations import extract_page_observation, normalize_url


FetchResult = dict[str, Any]
Fetcher = Callable[[str], FetchResult]


def _default_fetcher(url: str) -> FetchResult:
    try:
        response = httpx.get(
            url,
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"},
        )
        return {
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "body": response.text,
            "final_url": str(response.url),
            "error": None,
        }
    except Exception as exc:
        return {
            "status_code": 0,
            "content_type": "",
            "body": "",
            "final_url": url,
            "error": str(exc),
        }


def _safe_fetch(fetcher: Fetcher, url: str) -> FetchResult:
    try:
        return fetcher(url)
    except Exception as exc:
        return {
            "status_code": 0,
            "content_type": "",
            "body": "",
            "final_url": url,
            "error": str(exc),
        }


def run_technical_audit(
    *,
    client_id: str,
    domain: str,
    inventory: list[dict],
    profile: dict,
    fetcher: Fetcher = _default_fetcher,
) -> dict[str, Any]:
    run_timestamp = datetime.now(timezone.utc).isoformat()
    homepage = normalize_url(f"https://{domain}/")
    effective_profile = dict(profile)
    priority_urls = list(effective_profile.get("priority_urls") or [])
    if homepage not in {normalize_url(url) for url in priority_urls}:
        priority_urls.append(homepage)
    effective_profile["priority_urls"] = priority_urls
    pages = [dict(page) for page in inventory]
    inventory_urls = {
        normalize_url(page["url"])
        for page in pages
        if page.get("url")
    }

    if homepage not in inventory_urls:
        fetched_homepage = _safe_fetch(fetcher, homepage)
        if fetched_homepage.get("status_code") == 200:
            pages.insert(
                0,
                {
                    "url": fetched_homepage.get("final_url") or homepage,
                    "raw_html": fetched_homepage.get("body") or "",
                    "content_type": fetched_homepage.get("content_type") or "text/html",
                },
            )

    page_observations = tuple(
        extract_page_observation(page, run_timestamp)
        for page in pages
        if page.get("url")
    )

    llms_url = f"https://{domain}/llms.txt"
    llms_data = _safe_fetch(fetcher, llms_url)
    llms_body = llms_data.get("body") or ""
    llms_observation = Observation(
        id=f"site:{llms_url}",
        kind="llms_txt",
        subject=llms_url,
        retrieved_at=run_timestamp,
        fingerprint=sha256(llms_body.encode("utf-8")).hexdigest(),
        data=llms_data,
    )

    context = AuditContext(
        client_id=client_id,
        domain=domain,
        profile=effective_profile,
        pages=page_observations,
        site_observations={"llms_txt": llms_observation},
        run_timestamp=run_timestamp,
    )
    results = build_v1_registry().run(context)
    counts = Counter(result.status.value for result in results)
    summary = {
        status.value: counts.get(status.value, 0)
        for status in AuditStatus
    }
    summary["total"] = len(results)

    observations = [observation.to_dict() for observation in page_observations]
    persisted_llms = llms_observation.to_dict()
    persisted_llms["data"] = {
        key: value
        for key, value in persisted_llms["data"].items()
        if key != "body"
    }
    persisted_llms["data"]["body_excerpt"] = llms_body[:4_000]
    persisted_llms["data"]["body_bytes"] = len(llms_body.encode("utf-8"))
    observations.append(persisted_llms)
    return {
        "audit_version": 1,
        "observations": observations,
        "results": [result.to_dict() for result in results],
        "summary": summary,
    }
