import os
from src.graph.state import GEOState


def load_config(state: GEOState) -> dict:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    result = sb.table("clients").select("*").eq("id", state["client_id"]).single().execute()
    row = result.data
    config = {
        "client_name": row["brand_name"],
        "brand_name": row["brand_name"],
        "website_domain": row["website_domain"],
        "brand_variations": row["brand_variations"] or [],
        "target_queries": row["target_queries"] or [],
        "competitors": row["competitors"] or [],
        "gsc_site_url": row.get("gsc_site_url", ""),
        "cms_type": row.get("cms_type", "copy_paste"),
        "cms_config": row.get("cms_config", {}),
    }
    return {"client_config": config}


def _get_supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def run_tracker_node(state: GEOState) -> dict:
    from src.tracker import run_tracker
    try:
        results, scores = run_tracker(state["client_config"])

        sb = _get_supabase()
        run_row = sb.table("tracker_runs").insert({
            "client_id": state["client_id"],
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "aggregate_citation_rate": scores.get("aggregate_citation_rate", 0),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
        }).execute()

        result_rows = [{
            "run_id": run_row.data[0]["id"],
            "query": r["query"],
            "engine": r["engine"],
            "model": r.get("model", ""),
            "brand_mentioned": r["brand_mentioned"],
            "brand_cited": r["brand_cited"],
            "citation_url": r.get("citation_url"),
            "competitor_mentions": r.get("competitor_mentions", []),
            "response_text": r.get("response_text", ""),
        } for r in results]
        sb.table("tracker_results").insert(result_rows).execute()

        return {"tracker_results": results, "tracker_scores": scores}
    except Exception as e:
        print(f"  Tracker failed: {e}")
        return {"tracker_results": [], "tracker_scores": {}, "error": str(e)}


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


def run_audit_node(state: GEOState) -> dict:
    from src.auditor import run_audit
    try:
        pages, summary = run_audit(state["client_config"])

        sb = _get_supabase()
        run_row = sb.table("audit_runs").insert({
            "client_id": state["client_id"],
            "pages_audited": summary["pages_audited"],
            "site_score": summary["site_score"],
            "pillar_averages": summary["pillar_averages"],
            "weakest_pillar": summary["weakest_pillar"],
        }).execute()

        audit_run_id = run_row.data[0]["id"]
        page_rows = [{
            "run_id": audit_run_id,
            "url": p["url"],
            "title": p["title"],
            "word_count": p["word_count"],
            "total_score": p["total_score"],
            "pillar_scores": p["pillars"],
        } for p in pages]
        sb.table("page_scores").insert(page_rows).execute()

        return {"audit_pages": pages, "audit_summary": summary, "audit_run_id": audit_run_id}
    except Exception as e:
        print(f"  Audit failed: {e}")
        return {"audit_pages": [], "audit_summary": {}, "error": str(e)}


def run_recommender_node(state: GEOState) -> dict:
    from src.recommender import run_recommender
    try:
        run_id = state.get("audit_run_id") or state["thread_id"]
        cards = run_recommender(run_id, state["audit_pages"])

        sb = _get_supabase()
        sb.table("action_cards").insert(cards).execute()

        return {"action_cards": cards}
    except Exception as e:
        print(f"  Recommender failed: {e}")
        return {"action_cards": [], "error": str(e)}


def run_reddit_scout_node(state: GEOState) -> dict:
    from src.reddit_scout import run_scout
    try:
        posts = run_scout(state["client_config"])
        return {"reddit_posts": posts}
    except Exception as e:
        print(f"  Reddit scout failed: {e}")
        return {"reddit_posts": []}


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
    for card in state["action_cards"]:
        card_id = card.get("id", "")
        if card_id not in state["approved_card_ids"]:
            continue

        print(f"  Implementing card {card_id} via {cms_type}...")
        try:
            result = route_card(card, cms_type, cms_config)
            result["card_id"] = card_id

            new_status = "implemented" if result.get("status") == "implemented" else "approved"
            sb.table("action_cards").update({"status": new_status}).eq("id", card_id).execute()

            if result.get("status") == "error":
                print(f"    Failed: {result.get('error')}")
            else:
                print(f"    Done: {result.get('status')}")

            results.append(result)
        except Exception as e:
            print(f"    Exception: {e}")
            results.append({"card_id": card_id, "status": "error", "error": str(e)})

    return {"implementation_results": results}
