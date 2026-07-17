import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from src.detection import detect_brand, detect_competitors
from src.engines import load_engines


RUNS_PER_PROMPT = 5
RUNS_PER_PARAPHRASE = 1
NON_BRANDED_BUCKETS = ("awareness", "consideration")

# How many requests may be in flight to a SINGLE engine at once. Different
# engines run in parallel, so total concurrency is this times the engine count.
# Kept modest so a large query set finishes in minutes without tripping provider
# rate limits (and with_retries backs off on the occasional 429). Override with
# TRACKER_ENGINE_CONCURRENCY or config["engine_concurrency"].
DEFAULT_ENGINE_CONCURRENCY = 3


def _engine_concurrency(config: dict) -> int:
    raw = config.get("engine_concurrency") or os.environ.get("TRACKER_ENGINE_CONCURRENCY")
    try:
        return max(1, int(raw)) if raw else DEFAULT_ENGINE_CONCURRENCY
    except (TypeError, ValueError):
        return DEFAULT_ENGINE_CONCURRENCY


def _query_text(query: str | dict) -> str:
    return query if isinstance(query, str) else query["prompt_text"]


def _query_id(query: str | dict) -> str | None:
    return None if isinstance(query, str) else query.get("id")


def _query_bucket(query: str | dict) -> str:
    return "consideration" if isinstance(query, str) else query.get("bucket") or "consideration"


def _query_paraphrases(query: str | dict) -> list[str]:
    if isinstance(query, str):
        return []
    return query.get("paraphrases") or []


def load_client_config(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text())


async def _query_engine_once(engine_query_fn, query_text: str, sem: asyncio.Semaphore | None = None) -> str:
    loop = asyncio.get_event_loop()
    if sem is None:
        return await loop.run_in_executor(None, engine_query_fn, query_text)
    # The semaphore is held across the actual network call, so it caps how many
    # requests hit this engine at once — the rate-limit guard.
    async with sem:
        return await loop.run_in_executor(None, engine_query_fn, query_text)


async def _run_prompt_on_engine(
    query_text: str,
    query_id: str | None,
    intent_prompt: str,
    bucket: str,
    engine_name: str,
    engine_info: dict,
    brand_variations: list[str],
    website_domain: str,
    competitors: list[str],
    runs_per_prompt: int,
    sem: asyncio.Semaphore | None = None,
) -> list[dict]:
    results = []

    try:
        tasks = [_query_engine_once(engine_info["query"], query_text, sem) for _ in range(runs_per_prompt)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        responses = []
        for _ in range(runs_per_prompt):
            try:
                response_text = engine_info["query"](query_text)
                responses.append(response_text)
            except Exception as e:
                responses.append(e)
            time.sleep(0.5)

    for run_num, response in enumerate(responses, 1):
        if isinstance(response, Exception):
            print(f"         → Run {run_num} ERROR: {response}")
            continue

        brand = detect_brand(response, brand_variations, website_domain)
        comps = detect_competitors(response, competitors)

        results.append({
            "query": query_text,
            "intent_prompt": intent_prompt,
            "query_id": query_id,
            "bucket": bucket,
            "engine": engine_name,
            "model": engine_info["model"],
            "response_text": response,
            "brand_mentioned": brand["brand_mentioned"],
            "brand_cited": brand["brand_cited"],
            "citation_url": brand["citation_url"],
            "mention_level": brand["mention_level"],
            "mention_level_label": brand["mention_level_label"],
            "competitor_mentions": comps,
            "run_number": run_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    return results


async def _run_all_units(
    units: list[tuple],
    engine_names: list[str],
    brand_variations: list[str],
    website_domain: str,
    competitors: list[str],
    runs_per_paraphrase: int,
    per_engine_concurrency: int,
) -> list[dict]:
    """Run every (engine, wording) unit concurrently, bounded per engine.

    Each engine gets its own semaphore, so requests to one provider are capped
    while different providers still run in parallel. A single failing unit never
    aborts the batch — its exception is logged and it contributes no samples."""
    sems = {name: asyncio.Semaphore(per_engine_concurrency) for name in engine_names}

    # Size the shared thread pool to the peak number of concurrent blocking
    # calls (one per permit across all engines) so run_in_executor never queues
    # behind the interpreter's small default pool.
    total = per_engine_concurrency * max(len(engine_names), 1)
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=total + 4, thread_name_prefix="tracker")
    )

    async def run_unit(wording, query_id, canonical, bucket, engine_name, engine_info):
        try:
            return await _run_prompt_on_engine(
                wording, query_id, canonical, bucket, engine_name, engine_info,
                brand_variations, website_domain, competitors, runs_per_paraphrase,
                sems[engine_name],
            )
        except Exception as e:
            print(f"  [{engine_name}] ERROR wording={wording[:40]!r}: {e}")
            return []

    batches = await asyncio.gather(*(run_unit(*unit) for unit in units))
    results: list[dict] = []
    for batch in batches:
        results.extend(batch)
    return results


def run_tracker(config: dict) -> tuple[list[dict], dict]:
    engines = load_engines()
    if not engines:
        raise RuntimeError("No engines available. Check your API keys in .env")

    queries = config["target_queries"]
    brand_variations = config["brand_variations"]
    website_domain = config["website_domain"]
    competitors = config.get("competitors", [])
    runs_per_paraphrase = config.get(
        "runs_per_paraphrase",
        config.get("runs_per_prompt", RUNS_PER_PARAPHRASE),
    )
    per_engine_concurrency = _engine_concurrency(config)

    # Flatten to independent units so they can all run concurrently.
    units = []
    for query in queries:
        bucket = _query_bucket(query)
        if bucket == "branded":
            continue
        canonical = _query_text(query)
        query_id = _query_id(query)
        wordings = [canonical] + _query_paraphrases(query)
        for engine_name, engine_info in engines.items():
            for wording in wordings:
                units.append((wording, query_id, canonical, bucket, engine_name, engine_info))

    print(
        f"  [tracker] {len(units)} calls across {len(engines)} engines "
        f"(<= {per_engine_concurrency} concurrent per engine)"
    )
    results = asyncio.run(_run_all_units(
        units, list(engines.keys()), brand_variations, website_domain,
        competitors, runs_per_paraphrase, per_engine_concurrency,
    ))

    scores = compute_scores(results, engines, competitors)
    return results, scores


def _rate_stats(samples: list[dict]) -> dict:
    """mention_rate + avg_mention_level (over mentioned) + citation_rate (conditional)."""
    total = len(samples)
    if total == 0:
        return {"mention_rate": 0.0, "avg_mention_level": 0.0, "citation_rate": 0.0, "count": 0}
    mentioned = [s for s in samples if s.get("brand_mentioned")]
    m = len(mentioned)
    cited = sum(1 for s in mentioned if s.get("brand_cited"))
    return {
        "mention_rate": m / total,
        "avg_mention_level": (sum(s.get("mention_level", 0) for s in mentioned) / m) if m else 0.0,
        "citation_rate": (cited / m) if m else 0.0,
        "count": total,
    }


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def compute_scores(results: list[dict], engines: dict, competitors: list[str] | None = None) -> dict:
    engine_names = set(engines)
    samples = [r for r in results if r["engine"] in engine_names]

    intents: dict = {}
    intent_bucket: dict = {}
    for s in samples:
        iid = s.get("query_id") or s.get("intent_prompt") or s["query"]
        intents.setdefault(iid, []).append(s)
        intent_bucket[iid] = s.get("bucket") or "consideration"

    intent_rate = {iid: _rate_stats(iss)["mention_rate"] for iid, iss in intents.items()}
    non_branded_ids = [iid for iid in intents if intent_bucket[iid] in NON_BRANDED_BUCKETS]
    non_branded_samples = [s for iid in non_branded_ids for s in intents[iid]]

    pooled = _rate_stats(non_branded_samples)
    aggregate_mention_rate = _mean([intent_rate[iid] for iid in non_branded_ids])

    bucket_scores = {}
    for bucket in ("awareness", "consideration", "branded"):
        ids = [iid for iid in intents if intent_bucket[iid] == bucket]
        b = _rate_stats([s for iid in ids for s in intents[iid]])
        bucket_scores[bucket] = {
            "mention_rate": _mean([intent_rate[iid] for iid in ids]),
            "avg_mention_level": b["avg_mention_level"],
            "citation_rate": b["citation_rate"],
            "intent_count": len(ids),
        }

    per_engine = {}
    for engine_name in engine_names:
        eng_intent_rates = []
        eng_samples = []
        for iid in non_branded_ids:
            iss = [s for s in intents[iid] if s["engine"] == engine_name]
            if not iss:
                continue
            eng_intent_rates.append(_rate_stats(iss)["mention_rate"])
            eng_samples.extend(iss)
        ep = _rate_stats(eng_samples)
        per_engine[engine_name] = {
            "mention_rate": _mean(eng_intent_rates),
            "avg_mention_level": ep["avg_mention_level"],
            "citation_rate": ep["citation_rate"],
        }

    competitor_scores = {}
    for comp in (competitors or []):
        c = sum(1 for s in non_branded_samples if comp in s.get("competitor_mentions", []))
        competitor_scores[comp] = {
            "mention_rate": c / len(non_branded_samples) if non_branded_samples else 0.0,
        }

    return {
        "per_engine": per_engine,
        "aggregate_mention_rate": aggregate_mention_rate,
        "non_branded_mention_rate": aggregate_mention_rate,
        "aggregate_avg_mention_level": pooled["avg_mention_level"],
        "aggregate_citation_rate": pooled["citation_rate"],
        "bucket_scores": bucket_scores,
        "competitor_scores": competitor_scores,
    }


def compute_competitive_gaps(results: list[dict], competitors: list[str]) -> list[dict]:
    if not results:
        return []

    intents = []
    groups = {}
    for r in results:
        intent_prompt = r.get("intent_prompt") or r["query"]
        intent_key = r.get("query_id") or intent_prompt
        if intent_key not in groups:
            intents.append((intent_key, intent_prompt))
            groups[intent_key] = []
        groups[intent_key].append(r)

    gaps = []
    for intent_key, intent_prompt in intents:
        intent_results = groups[intent_key]
        total = len(intent_results)

        client_mentions = [r for r in intent_results if r["brand_mentioned"]]
        client_mention_rate = len(client_mentions) / total if total > 0 else 0
        client_avg_level = (
            sum(r["mention_level"] for r in client_mentions) / len(client_mentions)
            if client_mentions else 0
        )

        engines = []
        engine_seen = set()
        for r in intent_results:
            if r["engine"] not in engine_seen:
                engines.append(r["engine"])
                engine_seen.add(r["engine"])

        competitor_data = []
        for comp in competitors:
            comp_total = 0
            comp_mentioned = 0
            per_engine = {}

            for engine in engines:
                engine_results = [r for r in intent_results if r["engine"] == engine]
                engine_total = len(engine_results)
                engine_mentioned = sum(
                    1 for r in engine_results if comp in r.get("competitor_mentions", [])
                )
                per_engine[engine] = engine_mentioned / engine_total if engine_total > 0 else 0
                comp_total += engine_total
                comp_mentioned += engine_mentioned

            competitor_data.append({
                "name": comp,
                "mention_rate": comp_mentioned / comp_total if comp_total > 0 else 0,
                "per_engine": per_engine,
            })

        gaps.append({
            "query": intent_prompt,
            "query_id": intent_results[0].get("query_id"),
            "bucket": intent_results[0].get("bucket") or "consideration",
            "client_mention_rate": client_mention_rate,
            "client_avg_mention_level": client_avg_level,
            "competitor_data": competitor_data,
        })

    return gaps
