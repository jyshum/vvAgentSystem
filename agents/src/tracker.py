import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.detection import detect_brand, detect_competitors
from src.engines import load_engines


def load_client_config(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text())


def run_tracker(config: dict) -> tuple[list[dict], dict]:
    engines = load_engines()
    if not engines:
        raise RuntimeError("No engines available. Check your API keys in .env")

    results = []
    queries = config["target_queries"]
    brand_variations = config["brand_variations"]
    website_domain = config["website_domain"]
    competitors = config.get("competitors", [])

    total = len(queries) * len(engines)
    count = 0

    for query_text in queries:
        for engine_name, engine_info in engines.items():
            count += 1
            print(f"  [{count}/{total}] {engine_name}: {query_text[:50]}...")

            try:
                response_text = engine_info["query"](query_text)
                brand = detect_brand(response_text, brand_variations, website_domain)
                comps = detect_competitors(response_text, competitors)

                results.append({
                    "query": query_text,
                    "engine": engine_name,
                    "model": engine_info["model"],
                    "response_text": response_text,
                    "brand_mentioned": brand["brand_mentioned"],
                    "brand_cited": brand["brand_cited"],
                    "citation_url": brand["citation_url"],
                    "competitor_mentions": comps,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                status = "MENTIONED" if brand["brand_mentioned"] else "not found"
                if brand["brand_cited"]:
                    status = "CITED"
                print(f"         → {status}")

            except Exception as e:
                print(f"         → ERROR: {e}")

            time.sleep(0.5)

    scores = compute_scores(results, engines, competitors)
    return results, scores


def compute_scores(results: list[dict], engines: dict, competitors: list[str] | None = None) -> dict:
    per_engine = {}
    for engine_name in engines:
        engine_results = [r for r in results if r["engine"] == engine_name]
        if not engine_results:
            continue
        total = len(engine_results)
        mentions = sum(1 for r in engine_results if r["brand_mentioned"])
        citations = sum(1 for r in engine_results if r["brand_cited"])
        per_engine[engine_name] = {
            "mention_rate": mentions / total,
            "citation_rate": citations / total,
        }

    all_results = [r for r in results if r["engine"] in engines]
    total_all = len(all_results) if all_results else 1
    total_mentions = sum(1 for r in all_results if r["brand_mentioned"])
    total_citations = sum(1 for r in all_results if r["brand_cited"])

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
        "aggregate_citation_rate": total_citations / total_all,
        "competitor_scores": competitor_scores,
    }
