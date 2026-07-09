import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.detection import detect_brand, detect_competitors
from src.engines import load_engines


RUNS_PER_PROMPT = 5
RUNS_PER_PARAPHRASE = 1
NON_BRANDED_BUCKETS = ("awareness", "consideration")


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


async def _query_engine_once(engine_query_fn, query_text: str) -> str:
    loop = asyncio.get_event_loop()
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
) -> list[dict]:
    results = []

    try:
        tasks = [_query_engine_once(engine_info["query"], query_text) for _ in range(runs_per_prompt)]
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


def run_tracker(config: dict) -> tuple[list[dict], dict]:
    engines = load_engines()
    if not engines:
        raise RuntimeError("No engines available. Check your API keys in .env")

    results = []
    queries = config["target_queries"]
    brand_variations = config["brand_variations"]
    website_domain = config["website_domain"]
    competitors = config.get("competitors", [])
    runs_per_paraphrase = config.get(
        "runs_per_paraphrase",
        config.get("runs_per_prompt", RUNS_PER_PARAPHRASE),
    )

    for query in queries:
        bucket = _query_bucket(query)
        if bucket == "branded":
            continue
        canonical = _query_text(query)
        query_id = _query_id(query)
        wordings = [canonical] + _query_paraphrases(query)
        for engine_name, engine_info in engines.items():
            for wording in wordings:
                print(f"  [{engine_name}] intent={canonical[:40]!r} wording={wording[:40]!r}")
                try:
                    batch = asyncio.run(_run_prompt_on_engine(
                        wording, query_id, canonical, bucket, engine_name, engine_info,
                        brand_variations, website_domain, competitors, runs_per_paraphrase,
                    ))
                    results.extend(batch)
                except Exception as e:
                    print(f"         → ERROR: {e}")

    scores = compute_scores(results, engines, competitors)
    return results, scores


def compute_scores(results: list[dict], engines: dict, competitors: list[str] | None = None) -> dict:
    def score_group(group_results: list[dict]) -> dict:
        total = len(group_results)
        if total == 0:
            return {
                "mention_rate": 0,
                "avg_mention_level": 0,
                "citation_rate": 0,
                "count": 0,
            }
        mentions = [r for r in group_results if r["brand_mentioned"]]
        mention_count = len(mentions)
        citations = sum(1 for r in mentions if r["brand_cited"])
        return {
            "mention_rate": mention_count / total,
            "avg_mention_level": (
                sum(r["mention_level"] for r in mentions) / mention_count
                if mention_count > 0 else 0
            ),
            "citation_rate": citations / mention_count if mention_count > 0 else 0,
            "count": total,
        }

    per_engine = {}
    for engine_name in engines:
        engine_results = [r for r in results if r["engine"] == engine_name]
        if not engine_results:
            continue
        total = len(engine_results)
        mentions = [r for r in engine_results if r["brand_mentioned"]]
        mention_count = len(mentions)
        citations = sum(1 for r in mentions if r["brand_cited"])

        avg_level = (
            sum(r["mention_level"] for r in mentions) / mention_count
            if mention_count > 0 else 0
        )
        citation_rate = citations / mention_count if mention_count > 0 else 0

        per_engine[engine_name] = {
            "mention_rate": mention_count / total,
            "avg_mention_level": avg_level,
            "citation_rate": citation_rate,
        }

    all_results = [r for r in results if r["engine"] in engines]
    scored_results = [r for r in all_results if r.get("bucket") != "branded"] or all_results
    aggregate = score_group(scored_results)
    all_scores = score_group(all_results)
    bucket_scores = {
        bucket: score_group([r for r in all_results if (r.get("bucket") or "consideration") == bucket])
        for bucket in ("awareness", "consideration", "branded")
    }

    competitor_scores = {}
    for comp in (competitors or []):
        comp_mentions = sum(
            1 for r in scored_results if comp in r.get("competitor_mentions", [])
        )
        competitor_scores[comp] = {
            "mention_rate": comp_mentions / len(scored_results) if scored_results else 0,
        }

    return {
        "per_engine": per_engine,
        "aggregate_mention_rate": aggregate["mention_rate"],
        "aggregate_avg_mention_level": aggregate["avg_mention_level"],
        "aggregate_citation_rate": aggregate["citation_rate"],
        "non_branded_mention_rate": aggregate["mention_rate"],
        "all_prompt_mention_rate": all_scores["mention_rate"],
        "bucket_scores": bucket_scores,
        "competitor_scores": competitor_scores,
    }


def compute_competitive_gaps(results: list[dict], competitors: list[str]) -> list[dict]:
    if not results:
        return []

    queries = []
    seen = set()
    for r in results:
        if r["query"] not in seen:
            queries.append(r["query"])
            seen.add(r["query"])

    gaps = []
    for query in queries:
        query_results = [r for r in results if r["query"] == query]
        total = len(query_results)

        client_mentions = [r for r in query_results if r["brand_mentioned"]]
        client_mention_rate = len(client_mentions) / total if total > 0 else 0
        client_avg_level = (
            sum(r["mention_level"] for r in client_mentions) / len(client_mentions)
            if client_mentions else 0
        )

        engines = []
        engine_seen = set()
        for r in query_results:
            if r["engine"] not in engine_seen:
                engines.append(r["engine"])
                engine_seen.add(r["engine"])

        competitor_data = []
        for comp in competitors:
            comp_total = 0
            comp_mentioned = 0
            per_engine = {}

            for engine in engines:
                engine_results = [r for r in query_results if r["engine"] == engine]
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
            "query": query,
            "query_id": query_results[0].get("query_id"),
            "bucket": query_results[0].get("bucket") or "consideration",
            "client_mention_rate": client_mention_rate,
            "client_avg_mention_level": client_avg_level,
            "competitor_data": competitor_data,
        })

    return gaps
