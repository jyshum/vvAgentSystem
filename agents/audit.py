import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from src.tracker import load_client_config
from src.auditor import run_audit


def upload_audit_to_supabase(client_id: str, pages: list[dict], summary: dict) -> str:
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    sb = create_client(url, key)

    run_row = sb.table("audit_runs").insert({
        "client_id": client_id,
        "pages_audited": summary["pages_audited"],
        "site_score": summary["site_score"],
        "pillar_averages": summary["pillar_averages"],
        "weakest_pillar": summary["weakest_pillar"],
    }).execute()
    run_id = run_row.data[0]["id"]

    page_rows = [{
        "run_id": run_id,
        "url": p["url"],
        "title": p["title"],
        "word_count": p["word_count"],
        "total_score": p["total_score"],
        "pillar_scores": p["pillars"],
    } for p in pages]
    sb.table("page_scores").insert(page_rows).execute()

    return run_id


def main():
    parser = argparse.ArgumentParser(description="GEO Audit Agent")
    parser.add_argument("config", nargs="?", help="Path to client config JSON")
    parser.add_argument("--client-id", help="Supabase client UUID")
    parser.add_argument("--output-dir", default="../output")
    parser.add_argument("--upload", action="store_true")
    args = parser.parse_args()

    if args.client_id:
        from run import fetch_config_from_supabase
        config = fetch_config_from_supabase(args.client_id)
        config["supabase_client_id"] = args.client_id
    elif args.config:
        config = load_client_config(args.config)
    else:
        raise SystemExit("Provide a config file or --client-id")

    print(f"\n  GEO Audit — {config['client_name']}")
    print(f"  Domain: {config['website_domain']}")

    pages, summary = run_audit(config)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%b-%d-%Y_%I-%M%p").lower()
    slug = config["client_name"].lower().replace(" ", "_")
    out_path = output_dir / f"{slug}_audit_{timestamp}.json"
    out_path.write_text(json.dumps({"summary": summary, "pages": pages}, indent=2))

    print(f"\n  Site Score:     {summary.get('site_score', 0)}/100")
    print(f"  Pages Audited:  {summary.get('pages_audited', 0)}")
    print(f"  Weakest Pillar: {summary.get('weakest_pillar', 'N/A')}")
    print(f"\n  Weakest Pages:")
    for p in summary.get("weakest_pages", []):
        print(f"    {p['score']}/100  {p['url']}")
    print(f"\n  Output: {out_path}")

    if args.upload:
        client_id = config.get("supabase_client_id")
        if not client_id:
            print("\n  No supabase_client_id — skipping upload")
        else:
            run_id = upload_audit_to_supabase(client_id, pages, summary)
            print(f"  Uploaded. Run ID: {run_id}")


if __name__ == "__main__":
    main()
