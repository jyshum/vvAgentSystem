# agents/implement.py
import argparse
import os

from dotenv import load_dotenv
load_dotenv()


def fetch_card(card_id: str) -> dict:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    result = sb.table("action_cards").select("*").eq("id", card_id).single().execute()
    return result.data


def fetch_client_for_run(run_id: str) -> dict:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    run = sb.table("audit_runs").select("client_id").eq("id", run_id).single().execute()
    client = sb.table("clients").select("cms_type, cms_config").eq("id", run.data["client_id"]).single().execute()
    return client.data


def mark_implemented(card_id: str, result_url: str | None = None):
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    sb.table("action_cards").update({"status": "implemented"}).eq("id", card_id).execute()
    print(f"  Card {card_id} marked as implemented")
    if result_url:
        print(f"  Result: {result_url}")


def implement_card(card_id: str):
    card = fetch_card(card_id)
    client = fetch_client_for_run(card["run_id"])
    cms_type = client.get("cms_type", "copy_paste")
    cms_config = client.get("cms_config", {})

    print(f"  Card: {card['pillar']} on {card['page_url']}")
    print(f"  CMS:  {cms_type}")
    print(f"  Action: {card['cms_action']}")

    if card["cms_action"] == "none":
        print("  Authority signal card — suggestion only, no automated implementation")
        mark_implemented(card_id)
        return

    if cms_type == "github" and card["cms_action"] in ("github_pr", "copy_paste"):
        from src.implementors.github_impl import open_github_pr
        repo_name = cms_config.get("github_repo")
        file_path_map = cms_config.get("file_path_for_url", {})
        file_path = file_path_map.get(card["page_url"])
        if not repo_name or not file_path:
            print(f"  Missing github_repo or file_path in cms_config — cannot automate")
            return
        pr_url = open_github_pr(card, repo_name, file_path)
        mark_implemented(card_id, pr_url)
        return

    print(f"  No automated handler for cms_type='{cms_type}' — card ready for copy-paste in dashboard")


def main():
    parser = argparse.ArgumentParser(description="GEO Implementation Handler")
    parser.add_argument("--card-id", required=True, help="action_cards UUID to implement")
    args = parser.parse_args()

    print(f"\n  GEO Implementor — Card {args.card_id}\n")
    implement_card(args.card_id)


if __name__ == "__main__":
    main()
