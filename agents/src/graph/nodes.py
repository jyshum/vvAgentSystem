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
        "brand_variations": row["brand_variations"] or [],
        "target_queries": target_queries,
        "competitors": row["competitors"] or [],
        "gsc_site_url": row.get("gsc_site_url", ""),
        "cms_type": row.get("cms_type", "copy_paste"),
        "cms_config": row.get("cms_config", {}),
        "auto_approve_action_types": row.get("auto_approve_action_types") or [],
    }
    return {"client_config": config}


def _get_supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def run_tracker_node(state: GEOState) -> dict:
    from src.drift import compute_query_set_signature
    from src.tracker import run_tracker, compute_competitive_gaps
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
    gsc_site_url = state["client_config"].get("gsc_site_url", "")
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


def run_improvement_pipeline_node(state: GEOState) -> dict:
    from src.improvement.pipeline import run_improvement_pipeline
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
        result = run_improvement_pipeline(state, queries, competitive_gaps)
        return result
    except Exception as e:
        print(f"  Improvement pipeline failed: {e}")
        return {
            "improvement_run_id": None,
            "crawlability_report": {},
            "page_inventory": [],
            "query_matches": [],
            "citation_scores": [],
            "competitive_gap_data": [],
            "action_cards": [],
            "error": str(e),
        }


def await_approval(state: GEOState) -> dict:
    from langgraph.types import interrupt
    approved = interrupt({
        "action": "approve_cards",
        "pending_cards": state["action_cards"],
    })
    return {"approved_card_ids": approved}


def run_implementation_node(state: GEOState) -> dict:
    from src.implementors.router import route_card

    cms_type = state["client_config"].get("cms_type", "copy_paste")
    cms_config = state["client_config"].get("cms_config", {})
    sb = _get_supabase()

    results = []
    approved_ids = set(state.get("approved_card_ids") or [])
    for card in state["action_cards"]:
        card_id = card.get("id", "")
        if not card_id:
            print(f"    Skipping card with no id (insert may have partially failed): {card.get('action_type')}")
            continue
        if not (card.get("auto_approved") or card_id in approved_ids):
            continue

        print(f"  Implementing card {card_id} via {cms_type}...")
        try:
            result = route_card(card, cms_type, cms_config)
            result["card_id"] = card_id

            new_status = "implemented" if result.get("status") == "implemented" else "approved"

            verification = None
            if result.get("status") == "implemented":
                from src.improvement.verifier import verify_implementation
                verification = verify_implementation(card)
                result["verification"] = verification
                if verification["verified"]:
                    print(f"    Verified live: {card.get('page_url')}")
                else:
                    print(f"    NOT verified: {verification.get('error') or verification['checks']}")

            update_fields = {"status": new_status}
            preview = result.get("preview_url") or result.get("pr_url")
            if preview:
                update_fields["preview_url"] = preview
            if verification is not None:
                update_fields["verification"] = verification
            sb.table("action_cards").update(update_fields).eq("id", card_id).execute()

            if result.get("status") == "error":
                print(f"    Failed: {result.get('error')}")
            else:
                print(f"    Done: {result.get('status')}")

            results.append(result)
        except Exception as e:
            print(f"    Exception: {e}")
            results.append({"card_id": card_id, "status": "error", "error": str(e)})

    return {"implementation_results": results}
