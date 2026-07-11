"""CLI entry point: python -m src.tracker --client-id <uuid>"""

import argparse
import asyncio
import os
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client


def main():
    parser = argparse.ArgumentParser(description="Run AI visibility tracker for a client")
    parser.add_argument("--client-id", required=True, help="Client UUID")
    parser.add_argument("--runs-per-paraphrase", type=int, default=1, help="Runs per paraphrase (default 1)")
    args = parser.parse_args()

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    client_resp = sb.table("clients").select("*").eq("id", args.client_id).single().execute()
    client = client_resp.data
    print(f"Client: {client['brand_name']} ({client['website_domain']})")

    queries_resp = sb.table("queries").select("*").eq("client_id", args.client_id).execute()
    queries = queries_resp.data
    print(f"Queries: {len(queries)} intents loaded")

    target_queries = []
    for q in queries:
        target_queries.append({
            "prompt_text": q["prompt_text"],
            "bucket": q.get("bucket", "consideration"),
            "paraphrases": q.get("paraphrases") or [],
        })

    config = {
        "target_queries": target_queries,
        "brand_variations": client.get("brand_variations") or [],
        "website_domain": client["website_domain"],
        "competitors": client.get("competitors") or [],
        "runs_per_paraphrase": args.runs_per_paraphrase,
    }

    from src.tracker import run_tracker
    print(f"\nStarting tracker run...")
    print(f"  {len(target_queries)} intents × {sum(1 + len(q.get('paraphrases', [])) for q in target_queries)} total wordings")
    print(f"  runs_per_paraphrase: {args.runs_per_paraphrase}")
    print()

    results, scores = run_tracker(config)

    print(f"\n--- Results ---")
    print(f"Total results: {len(results)}")
    print(f"Non-branded mention rate: {scores.get('non_branded_mention_rate', 0):.1%}")
    print(f"Aggregate mention rate: {scores.get('aggregate_mention_rate', 0):.1%}")

    bucket_scores = scores.get("bucket_scores", {})
    for bucket, bs in bucket_scores.items():
        print(f"  [{bucket}] mention_rate={bs['mention_rate']:.1%} citation_rate={bs['citation_rate']:.1%} intents={bs['intent_count']}")

    run_row = sb.table("tracker_runs").insert({
        "client_id": args.client_id,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "aggregate_mention_rate": scores.get("aggregate_mention_rate"),
        "non_branded_mention_rate": scores.get("non_branded_mention_rate"),
        "bucket_scores": bucket_scores,
        "competitor_scores": scores.get("competitor_scores", {}),
    }).execute()

    run_id = run_row.data[0]["id"]
    print(f"\nTracker run saved: {run_id}")

    if results:
        result_rows = []
        for r in results:
            result_rows.append({
                "run_id": run_id,
                "client_id": args.client_id,
                "query": r.get("query") or r.get("prompt_text", ""),
                "bucket": r.get("bucket", "consideration"),
                "llm": r.get("engine", ""),
                "wording": r.get("wording", ""),
                "response_text": r.get("response_text", ""),
                "brand_mentioned": r.get("brand_mentioned", False),
                "brand_cited": r.get("brand_cited", False),
                "citation_url": r.get("citation_url"),
                "mention_level": r.get("mention_level", 0),
                "mention_level_label": r.get("mention_level_label", ""),
                "competitor_mentions": r.get("competitor_mentions", {}),
            })
        sb.table("prompt_scores").insert(result_rows).execute()
        print(f"Saved {len(result_rows)} prompt scores")

    print("\nDone!")


if __name__ == "__main__":
    main()
