from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

CRUX_ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
LIGHTHOUSE_RUNS = 3
MAX_PERFORMANCE_SUBJECTS = 3

HttpPost = Callable[[str, dict], dict]
HttpGet = Callable[[str, dict], dict]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_post(url: str, payload: dict) -> dict:
    import httpx

    response = httpx.post(url, json=payload, timeout=30)
    return {"status_code": response.status_code, "json": response.json()}


def _default_get(url: str, params: dict) -> dict:
    import httpx

    response = httpx.get(url, params=params, timeout=120)
    return {"status_code": response.status_code, "json": response.json()}


def performance_subjects(collected, limit: int = MAX_PERFORMANCE_SUBJECTS) -> list[str]:
    """Deterministic lab/field sample: homepage plus the first collected HTML pages."""
    subjects = []
    for page in collected.pages:
        mime = (page.content_type or "").split(";", 1)[0].strip().lower()
        if (
            page.status_code == 200
            and page.error is None
            and mime in {"text/html", "application/xhtml+xml"}
            and page.final_url not in subjects
        ):
            subjects.append(page.final_url)
        if len(subjects) >= limit:
            break
    return subjects


def _crux_metrics(record: dict) -> dict[str, float | None]:
    metrics = record.get("metrics", {})

    def p75(name: str) -> float | None:
        raw = (
            metrics.get(name, {}).get("percentiles", {}).get("p75")
        )
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    return {
        "lcp_ms": p75("largest_contentful_paint"),
        "inp_ms": p75("interaction_to_next_paint"),
        "cls": p75("cumulative_layout_shift"),
    }


def fetch_crux(
    url: str,
    api_key: str,
    form_factor: str = "PHONE",
    http_post: HttpPost | None = None,
) -> dict[str, Any]:
    """Page-level CrUX p75 record with labelled origin fallback. Never raises."""
    post = http_post or _default_post
    endpoint = f"{CRUX_ENDPOINT}?key={api_key}"
    try:
        response = post(endpoint, {"url": url, "formFactor": form_factor})
        if response["status_code"] == 200:
            return {
                "subject": url,
                "form_factor": form_factor,
                "origin_fallback": False,
                "collection_period": response["json"].get("record", {}).get("collectionPeriod"),
                "metrics": _crux_metrics(response["json"].get("record", {})),
                "retrieved_at": _now(),
            }
        if response["status_code"] == 404:
            parts = urlsplit(url)
            origin = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
            fallback = post(endpoint, {"origin": origin, "formFactor": form_factor})
            if fallback["status_code"] == 200:
                return {
                    "subject": url,
                    "form_factor": form_factor,
                    "origin_fallback": True,
                    "origin": origin,
                    "collection_period": fallback["json"].get("record", {}).get("collectionPeriod"),
                    "metrics": _crux_metrics(fallback["json"].get("record", {})),
                    "retrieved_at": _now(),
                }
            if fallback["status_code"] == 404:
                return {"subject": url, "insufficient_data": True, "retrieved_at": _now()}
            return {"subject": url, "error": f"CrUX API status {fallback['status_code']}", "retrieved_at": _now()}
        return {"subject": url, "error": f"CrUX API status {response['status_code']}", "retrieved_at": _now()}
    except Exception as exc:
        return {"subject": url, "error": type(exc).__name__, "retrieved_at": _now()}


def _psi_run(get: HttpGet, url: str, api_key: str) -> dict[str, Any]:
    params = {
        "url": url,
        "strategy": "mobile",
        "category": "performance",
    }
    if api_key:
        params["key"] = api_key
    response = get(PSI_ENDPOINT, params)
    if response["status_code"] != 200:
        return {"error": f"PSI status {response['status_code']}"}
    lighthouse = response["json"].get("lighthouseResult", {})
    score = lighthouse.get("categories", {}).get("performance", {}).get("score")
    audits = lighthouse.get("audits", {})
    return {
        "score": round(score * 100) if isinstance(score, (int, float)) else None,
        "lighthouse_version": lighthouse.get("lighthouseVersion"),
        "fetch_time": lighthouse.get("fetchTime"),
        "throttling": lighthouse.get("configSettings", {}).get("throttlingMethod"),
        "tbt_ms": audits.get("total-blocking-time", {}).get("numericValue"),
        "lcp_lazy_score": audits.get("lcp-lazy-loaded", {}).get("score"),
        "lcp_element": (
            audits.get("largest-contentful-paint-element", {})
            .get("details", {})
            .get("items", [{}])[0:1]
        ),
    }


def fetch_psi(
    url: str,
    api_key: str,
    runs: int = LIGHTHOUSE_RUNS,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    """Median of three controlled PSI mobile runs; an external lab diagnostic."""
    get = http_get or _default_get
    results = []
    try:
        for _ in range(runs):
            results.append(_psi_run(get, url, api_key))
    except Exception as exc:
        return {"subject": url, "error": type(exc).__name__, "retrieved_at": _now()}
    errors = [run["error"] for run in results if run.get("error")]
    scores = [run["score"] for run in results if run.get("score") is not None]
    if not scores:
        return {
            "subject": url,
            "error": errors[0] if errors else "PSI returned no performance score",
            "retrieved_at": _now(),
        }
    lazy_scores = [run.get("lcp_lazy_score") for run in results if run.get("lcp_lazy_score") is not None]
    return {
        "subject": url,
        "runs": len(scores),
        "run_scores": scores,
        "median_score": int(median(scores)),
        "lighthouse_version": results[0].get("lighthouse_version"),
        "fetch_times": [run.get("fetch_time") for run in results if run.get("fetch_time")],
        "throttling": results[0].get("throttling"),
        "tbt_ms_runs": [run.get("tbt_ms") for run in results],
        "lcp_lazy_score": min(lazy_scores) if lazy_scores else None,
        "lcp_element": results[0].get("lcp_element"),
        "device": "mobile",
        "cache_state": "cold (PSI default)",
        "auth_state": "unauthenticated",
        "retrieved_at": _now(),
    }


def fetch_bing_sitemaps(
    site_url: str,
    api_key: str,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    """Bing Webmaster GetFeeds: submitted sitemap feeds for the site."""
    get = http_get or _default_get
    try:
        response = get(
            "https://ssl.bing.com/webmaster/api.svc/json/GetFeeds",
            {"siteUrl": site_url, "apikey": api_key},
        )
        if response["status_code"] != 200:
            return {
                "site_url": site_url,
                "error": f"Bing API status {response['status_code']}",
                "retrieved_at": _now(),
            }
        feeds = response["json"].get("d") or []
        return {
            "site_url": site_url,
            "sitemaps": [
                {"path": feed.get("Url"), "status": feed.get("Status")}
                for feed in feeds
                if isinstance(feed, dict)
            ],
            "retrieved_at": _now(),
        }
    except Exception as exc:
        return {"site_url": site_url, "error": type(exc).__name__, "retrieved_at": _now()}


def collect_integrations(
    collected,
    gsc_site_url: str,
    env: dict | None = None,
    crux_fetch=fetch_crux,
    psi_fetch=fetch_psi,
    gsc_fetch=None,
    bing_fetch=fetch_bing_sitemaps,
) -> dict[str, Any]:
    """Assemble integration evidence for the performance check set.

    Missing keys leave their integration absent/unconfigured so the checks
    return explicit unknown or not_applicable — never fabricated data.
    """
    import os

    if gsc_fetch is None:
        gsc_fetch = fetch_gsc_sitemaps
    environment = env if env is not None else dict(os.environ)
    subjects = performance_subjects(collected)
    integrations: dict[str, Any] = {}

    crux_key = environment.get("CRUX_API_KEY", "")
    if crux_key:
        integrations["crux"] = [crux_fetch(subject, crux_key) for subject in subjects]

    psi_key = environment.get("PAGESPEED_API_KEY", "")
    if psi_key:
        integrations["psi"] = [psi_fetch(subject, psi_key) for subject in subjects]

    if gsc_site_url:
        integrations["gsc"] = {"configured": True, "data": gsc_fetch(gsc_site_url)}
    else:
        integrations["gsc"] = {"configured": False}

    bing_key = environment.get("BING_WEBMASTER_API_KEY", "")
    homepage = collected.homepage.final_url
    if bing_key:
        integrations["bing"] = {
            "configured": True,
            "data": bing_fetch(homepage, bing_key),
        }
    else:
        integrations["bing"] = {"configured": False}
    return integrations


def fetch_gsc_sitemaps(site_url: str) -> dict[str, Any]:
    """Search Console sitemap submission state via existing GSC credentials."""
    try:
        from src.gsc import _get_service

        service = _get_service()
        response = service.sitemaps().list(siteUrl=site_url).execute()
        sitemaps = [
            {
                "path": item.get("path"),
                "last_submitted": item.get("lastSubmitted"),
                "last_downloaded": item.get("lastDownloaded"),
                "is_pending": item.get("isPending"),
                "errors": int(item.get("errors") or 0),
                "warnings": int(item.get("warnings") or 0),
            }
            for item in response.get("sitemap", [])
        ]
        return {"site_url": site_url, "sitemaps": sitemaps, "retrieved_at": _now()}
    except Exception as exc:
        return {"site_url": site_url, "error": type(exc).__name__, "retrieved_at": _now()}
