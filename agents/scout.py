import argparse
import json
import os
from dotenv import load_dotenv
load_dotenv()

from src.tracker import load_client_config
from src.reddit_scout import run_scout


def upload_opportunities(client_id: str, posts: list[dict]):
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    rows = [{
        "client_id": client_id,
        "title": p["title"],
        "url": p["url"],
        "subreddit": p["subreddit"],
        "score": p["score"],
        "num_comments": p["num_comments"],
        "relevance_score": p["relevance_score"],
        "selftext_preview": p["selftext"],
        "status": "new",
    } for p in posts]
    sb.table("reddit_opportunities").insert(rows).execute()
    print(f"  {len(rows)} opportunities uploaded")


def main():
    parser = argparse.ArgumentParser(description="GEO Reddit Scout")
    parser.add_argument("config", nargs="?", help="Path to client config JSON")
    parser.add_argument("--client-id", help="Supabase client UUID")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--top", type=int, default=20, help="Number of results to show")
    args = parser.parse_args()

    if args.client_id:
        from run import fetch_config_from_supabase
        config = fetch_config_from_supabase(args.client_id)
        config["supabase_client_id"] = args.client_id
    elif args.config:
        config = load_client_config(args.config)
    else:
        raise SystemExit("Provide a config file or --client-id")

    print(f"\n  GEO Reddit Scout — {config['client_name']}\n")

    posts = run_scout(config)
    top_posts = posts[:args.top]

    print(f"\n  Found {len(posts)} unique posts (showing top {len(top_posts)})\n")
    for p in top_posts:
        relevance = f"{p['relevance_score']:.2f}"
        print(f"  [{relevance}] r/{p['subreddit']} — {p['title'][:70]}")
        print(f"         {p['url']}")
        print()

    if args.upload:
        client_id = config.get("supabase_client_id")
        if not client_id:
            print("  No supabase_client_id — skipping upload")
        else:
            upload_opportunities(client_id, top_posts)


if __name__ == "__main__":
    main()
