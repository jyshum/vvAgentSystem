import os
from datetime import datetime, timezone

from src.improvement.community import select_community_opportunities
from src.technical_audit.collector import collect_foundation
from src.technical_audit.runner import run_technical_audit
from src.technical_audit.site import SiteIdentity


FOUNDATION_CHECK_SETS = ("foundation",)


def _get_supabase():
    from supabase import create_client

    return create_client(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
    )


def _run_and_persist_technical_audit(
    sb,
    state: dict,
    improvement_run_id: str,
    enabled_check_sets: tuple[str, ...],
) -> dict:
    client_id = state["client_id"]
    config = state["client_config"]

    pipeline_run_id = None
    thread_id = state.get("thread_id")
    if thread_id:
        pipeline_resp = (
            sb.table("pipeline_runs")
            .select("id")
            .eq("client_id", client_id)
            .eq("thread_id", thread_id)
            .maybe_single()
            .execute()
        )
        if pipeline_resp.data:
            pipeline_run_id = pipeline_resp.data["id"]

    run_resp = sb.table("technical_audit_runs").insert(
        {
            "client_id": client_id,
            "improvement_run_id": improvement_run_id,
            "pipeline_run_id": pipeline_run_id,
            "audit_version": 1,
            "status": "running",
            "scope": {
                "check_sets": list(enabled_check_sets),
                "max_pages": 20,
            },
        }
    ).execute()
    audit_run_id = run_resp.data[0]["id"]

    try:
        identity = SiteIdentity.from_domain(
            config["website_domain"], config.get("site_platform") or "other"
        )
        collected = collect_foundation(identity)
        report = run_technical_audit(
            client_id,
            identity,
            collected,
            enabled_check_sets=enabled_check_sets,
        )

        observations = [
            {
                "audit_run_id": audit_run_id,
                "observation_ref": observation["id"],
                "kind": observation["kind"],
                "subject": observation["subject"],
                "retrieved_at": observation["retrieved_at"],
                "fingerprint": observation["fingerprint"],
                "data": observation["data"],
            }
            for observation in report["observations"]
        ]
        if observations:
            sb.table("technical_audit_observations").insert(observations).execute()

        result_rows = [
            {"audit_run_id": audit_run_id, **result}
            for result in report["results"]
        ]
        if result_rows:
            sb.table("technical_audit_results").insert(result_rows).execute()

        sb.table("technical_audit_runs").update(
            {
                "status": "completed",
                "scope": {
                    "observations": len(observations),
                    "check_sets": list(enabled_check_sets),
                    **report["scope"],
                },
                "summary": report["summary"],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", audit_run_id).execute()
        return {
            "run_id": audit_run_id,
            "summary": report["summary"],
            "results": report["results"],
            "error": None,
        }
    except Exception as exc:
        sb.table("technical_audit_runs").update(
            {
                "status": "error",
                "error_message": str(exc)[:500],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", audit_run_id).execute()
        return {
            "run_id": audit_run_id,
            "summary": {},
            "results": [],
            "error": str(exc),
        }


def run_technical_pipeline(
    state: dict,
    queries: list[dict],
    competitive_gaps: list[dict],
) -> dict:
    del queries
    client_id = state["client_id"]
    sb = _get_supabase()

    run_resp = sb.table("improvement_runs").insert(
        {
            "client_id": client_id,
            "status": "running",
            "thread_id": state.get("thread_id"),
            "run_mode": "technical_v1",
            "effective_check_sets": list(FOUNDATION_CHECK_SETS),
        }
    ).execute()
    improvement_run_id = run_resp.data[0]["id"]

    audit = _run_and_persist_technical_audit(
        sb,
        state,
        improvement_run_id,
        FOUNDATION_CHECK_SETS,
    )
    selection = select_community_opportunities(competitive_gaps, limit=5)
    completed_at = datetime.now(timezone.utc).isoformat()
    completion = {
        "status": "error" if audit["error"] else "completed",
        "competitive_gaps_found": selection.competitor_lead_count,
        "cards_generated": 0,
        "completed_at": completed_at,
    }
    if audit["error"]:
        completion["error_message"] = audit["error"][:500]
    sb.table("improvement_runs").update(completion).eq(
        "id", improvement_run_id
    ).execute()

    result = {
        "improvement_run_id": improvement_run_id,
        "technical_audit_run_id": audit["run_id"],
        "technical_audit_summary": audit["summary"],
        "technical_audit_results": audit["results"],
        "technical_audit_error": audit["error"],
        "community_opportunities": [
            item.to_gap_dict() for item in selection.opportunities
        ],
    }
    if audit["error"]:
        result["error"] = audit["error"]
    return result
