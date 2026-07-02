import argparse
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.tracker import load_client_config, run_tracker
from src.output import write_csv, write_json, write_html, format_summary
from supabase import create_client


def fetch_config_from_supabase(client_id: str) -> dict:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
    supabase = create_client(url, key)
    result = supabase.table("clients").select("*").eq("id", client_id).single().execute()
    row = result.data

    queries_resp = supabase.table("queries").select("prompt_text").eq("client_id", client_id).eq("status", "active").execute()
    target_queries = [q["prompt_text"] for q in queries_resp.data] if queries_resp.data else []

    return {
        "client_name": row["brand_name"],
        "brand_name": row["brand_name"],
        "website_domain": row["website_domain"],
        "brand_variations": row["brand_variations"] or [],
        "target_queries": target_queries,
        "competitors": row["competitors"] or [],
    }


def write_results_to_supabase(client_id: str, scores: dict, results: list) -> str:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
    supabase = create_client(url, key)

    run_row = supabase.table("tracker_runs").insert({
        "client_id": client_id,
        "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
        "aggregate_citation_rate": scores.get("aggregate_citation_rate", 0),
        "per_engine_scores": scores.get("per_engine", {}),
        "competitor_scores": scores.get("competitor_scores", {}),
    }).execute()

    run_id = run_row.data[0]["id"]

    result_rows = [{
        "run_id": run_id,
        "query": r["query"],
        "engine": r["engine"],
        "model": r.get("model", ""),
        "brand_mentioned": r["brand_mentioned"],
        "brand_cited": r["brand_cited"],
        "citation_url": r.get("citation_url"),
        "competitor_mentions": r.get("competitor_mentions", []),
        "response_text": r.get("response_text", ""),
    } for r in results]

    supabase.table("tracker_results").insert(result_rows).execute()
    return run_id


def main():
    parser = argparse.ArgumentParser(description="GEO Tracker Agent")
    parser.add_argument("config", nargs="?", help="Path to client config JSON file")
    parser.add_argument("--client-id", help="Supabase client UUID (fetches config from DB)")
    parser.add_argument(
        "--output-dir",
        default="../output",
        help="Directory for output files (default: ../output)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload results to Supabase after run",
    )
    args = parser.parse_args()

    if not args.client_id and not args.config:
        print("No CLIENT_ID set — waiting for next trigger. Exiting.")
        raise SystemExit(0)

    if args.client_id:
        config = fetch_config_from_supabase(args.client_id)
    else:
        config = load_client_config(args.config)
    client_name = config["client_name"]

    print(f"\n  GEO Tracker — {client_name}")
    print(f"  Queries: {len(config['target_queries'])}")
    print(f"  Brand: {config['brand_name']}")
    print()

    results, scores = run_tracker(config)

    if args.client_id:
        run_id = write_results_to_supabase(args.client_id, scores, results)
        print(f"Results written to Supabase. Run ID: {run_id}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%b-%d-%Y_%I-%M%p").lower()
    slug = client_name.lower().replace(" ", "_")

    csv_path = output_dir / f"{slug}_{timestamp}.csv"
    json_path = output_dir / f"{slug}_{timestamp}.json"
    html_path = output_dir / f"{slug}_{timestamp}.html"

    write_csv(results, csv_path)
    write_json(results, scores, client_name, json_path)
    write_html(results, scores, client_name, html_path)

    print(format_summary(scores, client_name))
    print(f"  HTML: {html_path}")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")

    if args.upload:
        supabase_client_id = config.get("supabase_client_id")
        if not supabase_client_id:
            print("\n  ⚠ No supabase_client_id in config — skipping upload")
        else:
            from src.upload import upload_run

            print()
            upload_run(supabase_client_id, results, scores)


if __name__ == "__main__":
    main()
