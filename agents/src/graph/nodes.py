import os
from src.graph.state import GEOState


def load_config(state: GEOState) -> dict:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    result = sb.table("clients").select("*").eq("id", state["client_id"]).single().execute()
    row = result.data

    queries_resp = (
        sb.table("queries")
        .select("id,prompt_text,paraphrases,bucket,set_type,slug,version")
        .eq("client_id", state["client_id"])
        .eq("status", "active")
        .order("bucket")
        .order("created_at")
        .execute()
    )
    target_queries = queries_resp.data or []

    config = {
        "client_name": row["brand_name"],
        "brand_name": row["brand_name"],
        "website_domain": row["website_domain"],
        "site_platform": row.get("site_platform") or "other",
        "implementation_mode": row.get("implementation_mode") or "manual",
        "brand_variations": row["brand_variations"] or [],
        "target_queries": target_queries,
        "competitors": row["competitors"] or [],
        "gsc_site_url": row.get("gsc_site_url", ""),
    }
    return {"client_config": config}


def _get_supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def run_tracker_node(state: GEOState) -> dict:
    from datetime import datetime, timezone, timedelta
    from src.drift import compute_query_set_signature
    from src.tracker import run_tracker, compute_competitive_gaps

    sb = _get_supabase()
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent = sb.table("tracker_runs") \
        .select("id, aggregate_mention_rate, non_branded_mention_rate, bucket_scores, competitor_scores") \
        .eq("client_id", state["client_id"]) \
        .gte("ran_at", one_hour_ago) \
        .order("ran_at", desc=True) \
        .limit(1) \
        .execute()

    if recent.data:
        run_id = recent.data[0]["id"]
        print(f"  Tracker: recent run {run_id} found (< 1h old), skipping")
        results_resp = sb.table("tracker_results").select("*").eq("run_id", run_id).execute()
        results = results_resp.data or []
        competitors = state["client_config"].get("competitors", [])
        gaps_resp = sb.table("competitive_gaps").select("*").eq("run_id", run_id).execute()
        gaps = gaps_resp.data or []
        return {"tracker_results": results, "tracker_scores": recent.data[0], "competitive_gaps": gaps}

    try:
        results, scores = run_tracker(state["client_config"])
        competitors = state["client_config"].get("competitors", [])
        gaps = compute_competitive_gaps(results, competitors)

        sb = _get_supabase()
        intents = state["client_config"].get("target_queries", [])
        signature = compute_query_set_signature(intents)
        prev = (
            sb.table("tracker_runs")
            .select("query_set_signature")
            .eq("client_id", state["client_id"])
            .order("ran_at", desc=True)
            .limit(1)
            .execute()
        )
        prev_sig = prev.data[0]["query_set_signature"] if prev.data else None
        query_set_changed = prev_sig is not None and prev_sig != signature

        run_row = sb.table("tracker_runs").insert({
            "client_id": state["client_id"],
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "non_branded_mention_rate": scores.get("non_branded_mention_rate", scores.get("aggregate_mention_rate", 0)),
            "aggregate_avg_mention_level": scores.get("aggregate_avg_mention_level", 0),
            "bucket_scores": scores.get("bucket_scores", {}),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
            "discovered_competitors": [],
            "thread_id": state.get("thread_id"),
            "query_set_signature": signature,
            "query_set_changed": query_set_changed,
        }).execute()

        run_id = run_row.data[0]["id"]

        result_rows = [{
            "run_id": run_id,
            "query": r["query"],
            "query_id": r.get("query_id"),
            "bucket": r.get("bucket", "consideration"),
            "engine": r["engine"],
            "model": r.get("model", ""),
            "brand_mentioned": r["brand_mentioned"],
            "brand_cited": r["brand_cited"],
            "citation_url": r.get("citation_url"),
            "competitor_mentions": r.get("competitor_mentions", []),
            "response_text": r.get("response_text", ""),
            "run_number": r.get("run_number"),
            "mention_level": r.get("mention_level", 0),
            "mention_level_label": r.get("mention_level_label", "not_mentioned"),
        } for r in results]
        sb.table("tracker_results").insert(result_rows).execute()

        from src.upload import _compute_prompt_scores, _build_competitive_gap_rows
        prompt_scores = _compute_prompt_scores(state["client_id"], run_id, results)
        if prompt_scores:
            sb.table("prompt_scores").insert(prompt_scores).execute()

        gap_rows = _build_competitive_gap_rows(state["client_id"], run_id, gaps)
        if gap_rows:
            sb.table("competitive_gaps").insert(gap_rows).execute()

        return {"tracker_results": results, "tracker_scores": scores, "competitive_gaps": gaps}
    except Exception as e:
        print(f"  Tracker failed: {e}")
        return {"tracker_results": [], "tracker_scores": {}, "competitive_gaps": [], "error": str(e)}


def run_gsc_node(state: GEOState) -> dict:
    # Strip whitespace — GSC property IDs must match byte-for-byte, and the
    # config UI has accepted values with stray spaces.
    gsc_site_url = (state["client_config"].get("gsc_site_url") or "").strip()
    if not gsc_site_url:
        print("  GSC: no site URL configured, skipping")
        return {"gsc_metrics": {}}

    from src.gsc import fetch_gsc_metrics
    try:
        metrics = fetch_gsc_metrics(gsc_site_url)
        if metrics.get("error"):
            print(f"  GSC: {metrics['error']}")
        else:
            print(f"  GSC: {metrics['totals']['clicks']} clicks, {metrics['totals']['impressions']} impressions")

        sb = _get_supabase()
        latest = sb.table("tracker_runs") \
            .select("id") \
            .eq("client_id", state["client_id"]) \
            .order("ran_at", desc=True) \
            .limit(1) \
            .execute()

        if latest.data:
            sb.table("tracker_runs").update({
                "gsc_clicks": metrics["totals"]["clicks"],
                "gsc_impressions": metrics["totals"]["impressions"],
                "gsc_ctr": metrics["totals"]["ctr"],
                "gsc_position": metrics["totals"]["position"],
                "gsc_top_queries": metrics["queries"][:20],
            }).eq("id", latest.data[0]["id"]).execute()

        return {"gsc_metrics": metrics}
    except Exception as e:
        print(f"  GSC failed: {e}")
        return {"gsc_metrics": {}}


def run_technical_pipeline_node(state: GEOState) -> dict:
    from src.technical_audit.pipeline import run_technical_pipeline

    sb = _get_supabase()

    queries_resp = sb.table("queries").select("*").eq("client_id", state["client_id"]).eq("status", "active").execute()
    queries = queries_resp.data or []

    competitive_gaps = []
    latest_run = sb.table("tracker_runs") \
        .select("id") \
        .eq("client_id", state["client_id"]) \
        .order("ran_at", desc=True) \
        .limit(1) \
        .execute()
    if latest_run.data:
        run_id = latest_run.data[0]["id"]
        gaps_resp = sb.table("competitive_gaps") \
            .select("*") \
            .eq("run_id", run_id) \
            .execute()
        competitive_gaps = gaps_resp.data or []

    try:
        result = run_technical_pipeline(state, queries, competitive_gaps)
        return result
    except Exception as e:
        print(f"  Technical pipeline failed: {e}")
        return {
            "improvement_run_id": None,
            "technical_audit_run_id": None,
            "technical_audit_summary": {},
            "technical_audit_results": [],
            "technical_audit_error": str(e),
            "community_opportunities": [],
            "error": str(e),
        }
