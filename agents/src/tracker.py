import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.detection import detect_brand, detect_competitors
from src.engines import load_engines


RUNS_PER_PROMPT = 5


def load_client_config(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text())


async def _query_engine_once(engine_query_fn, query_text: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, engine_query_fn, query_text)


async def _run_prompt_on_engine(
    query_text: str,
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
    runs_per_prompt = config.get("runs_per_prompt", RUNS_PER_PROMPT)

    total = len(queries) * len(engines)
    count = 0

    for query_text in queries:
        for engine_name, engine_info in engines.items():
            count += 1
            print(f"  [{count}/{total}] {engine_name}: {query_text[:50]}... ({runs_per_prompt} runs)")

            try:
                batch = asyncio.run(_run_prompt_on_engine(
                    query_text, engine_name, engine_info,
                    brand_variations, website_domain, competitors, runs_per_prompt,
                ))
                results.extend(batch)

                mentioned = sum(1 for r in batch if r["brand_mentioned"])
                avg_lvl = sum(r["mention_level"] for r in batch if r["brand_mentioned"])
                avg_lvl = avg_lvl / mentioned if mentioned else 0
                print(f"         → {mentioned}/{len(batch)} mentioned, avg level {avg_lvl:.1f}")
            except Exception as e:
                print(f"         → ERROR: {e}")

    scores = compute_scores(results, engines, competitors)
    return results, scores


def compute_scores(results: list[dict], engines: dict, competitors: list[str] | None = None) -> dict:
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
    total_all = len(all_results) if all_results else 1
    all_mentions = [r for r in all_results if r["brand_mentioned"]]
    total_mentions = len(all_mentions)

    aggregate_avg_level = (
        sum(r["mention_level"] for r in all_mentions) / total_mentions
        if total_mentions > 0 else 0
    )

    competitor_scores = {}
    for comp in (competitors or []):
        comp_mentions = sum(
            1 for r in all_results if comp in r.get("competitor_mentions", [])
        )
        competitor_scores[comp] = {
            "mention_rate": comp_mentions / total_all,
        }

    return {
        "per_engine": per_engine,
        "aggregate_mention_rate": total_mentions / total_all,
        "aggregate_avg_mention_level": aggregate_avg_level,
        "competitor_scores": competitor_scores,
    }
