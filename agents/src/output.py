import csv
import json
from datetime import datetime, timezone
from pathlib import Path


CSV_FIELDS = [
    "query",
    "engine",
    "model",
    "brand_mentioned",
    "brand_cited",
    "citation_url",
    "competitor_mentions",
    "response_text",
    "timestamp",
]


def write_csv(results: list[dict], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in results:
            row = {k: r.get(k, "") for k in CSV_FIELDS}
            if isinstance(row["competitor_mentions"], list):
                row["competitor_mentions"] = "; ".join(row["competitor_mentions"])
            writer.writerow(row)


def write_json(
    results: list[dict],
    scores: dict,
    client_name: str,
    output_path: Path,
) -> None:
    report = {
        "client_name": client_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "visibility_scores": scores,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def format_summary(scores: dict, client_name: str) -> str:
    lines = [
        f"\n{'='*50}",
        f"  GEO Visibility Report: {client_name}",
        f"{'='*50}",
    ]
    for engine, engine_scores in scores["per_engine"].items():
        mention = engine_scores["mention_rate"]
        citation = engine_scores["citation_rate"]
        lines.append(f"  {engine:<15} mention: {mention:>6.0%}   cited: {citation:>6.0%}")
    lines.append(f"{'─'*50}")
    agg_mention = scores["aggregate_mention_rate"]
    agg_citation = scores["aggregate_citation_rate"]
    lines.append(f"  {'AGGREGATE':<15} mention: {agg_mention:>6.0%}   cited: {agg_citation:>6.0%}")
    lines.append(f"{'='*50}\n")
    return "\n".join(lines)
