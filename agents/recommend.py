import argparse
import json
import os
from dotenv import load_dotenv
load_dotenv()

from src.recommender import run_recommender


def fetch_run_and_pages(run_id: str) -> list[dict]:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    pages_result = sb.table("page_scores").select("*").eq("run_id", run_id).execute()
    pages = []
    for row in pages_result.data:
        pages.append({
            "url": row["url"],
            "title": row["title"],
            "total_score": row["total_score"],
            "pillars": row["pillar_scores"],
        })
    return pages


def upload_cards(cards: list[dict]):
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    sb.table("action_cards").insert(cards).execute()
    print(f"  {len(cards)} action card(s) uploaded to Supabase")


def main():
    parser = argparse.ArgumentParser(description="GEO Recommendation Engine")
    parser.add_argument("--run-id", required=True, help="audit_runs UUID to generate cards for")
    parser.add_argument("--upload", action="store_true")
    args = parser.parse_args()

    print(f"\n  GEO Recommender — Run {args.run_id}\n")

    pages = fetch_run_and_pages(args.run_id)
    cards = run_recommender(args.run_id, pages)

    print(f"\n  Total cards generated: {len(cards)}")

    if args.upload:
        upload_cards(cards)
    else:
        print(json.dumps(cards, indent=2))


if __name__ == "__main__":
    main()
