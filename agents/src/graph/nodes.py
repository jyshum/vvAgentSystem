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
    }
    return {"client_config": config}


def run_tracker_node(state: GEOState) -> dict:
    from src.tracker import run_tracker
    try:
        results, scores = run_tracker(state["client_config"])
        return {"tracker_results": results, "tracker_scores": scores}
    except Exception as e:
        print(f"  Tracker failed: {e}")
        return {"tracker_results": [], "tracker_scores": {}, "error": str(e)}


def run_audit_node(state: GEOState) -> dict:
    from src.auditor import run_audit
    try:
        pages, summary = run_audit(state["client_config"])
        return {"audit_pages": pages, "audit_summary": summary}
    except Exception as e:
        print(f"  Audit failed: {e}")
        return {"audit_pages": [], "audit_summary": {}, "error": str(e)}


def run_recommender_node(state: GEOState) -> dict:
    from src.recommender import generate_action_cards
    try:
        cards = generate_action_cards(state["audit_pages"], state["client_config"])
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
    results = []
    for card in state["action_cards"]:
        card_id = card.get("id", "")
        if card_id not in state["approved_card_ids"]:
            continue
        try:
            results.append({"card_id": card_id, "status": "implemented"})
        except Exception as e:
            results.append({"card_id": card_id, "status": "error", "error": str(e)})
    return {"implementation_results": results}
