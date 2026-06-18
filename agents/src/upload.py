import os
from datetime import datetime, timezone


def create_client():
    from supabase import create_client as sb_create

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return sb_create(url, key)


def upload_run(
    client_id: str,
    results: list[dict],
    scores: dict,
) -> str | None:
    try:
        sb = create_client()
    except Exception as e:
        print(f"  Supabase upload skipped: {e}")
        return None

    try:
        run_row = {
            "client_id": client_id,
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "aggregate_citation_rate": scores.get("aggregate_citation_rate", 0),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
        }

        run_resp = sb.from_("tracker_runs").insert(run_row).select().single().execute()
        run_id = run_resp.data["id"]

        result_rows = []
        for r in results:
            result_rows.append({
                "run_id": run_id,
                "query": r["query"],
                "engine": r["engine"],
                "model": r.get("model", ""),
                "brand_mentioned": r.get("brand_mentioned", False),
                "brand_cited": r.get("brand_cited", False),
                "citation_url": r.get("citation_url", ""),
                "competitor_mentions": r.get("competitor_mentions", []),
                "response_text": r.get("response_text", ""),
                "queried_at": r.get("timestamp", datetime.now(timezone.utc).isoformat()),
            })

        if result_rows:
            sb.from_("tracker_results").insert(result_rows).execute()

        print(f"  Uploaded to Supabase: run {run_id} ({len(result_rows)} results)")
        return run_id

    except Exception as e:
        print(f"  Supabase upload failed: {e}")
        return None
