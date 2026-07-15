import os
from datetime import datetime, timezone

from src.improvement.community import select_community_opportunities
from src.technical_audit.collector import collect_site
from src.technical_audit.evidence.performance import collect_integrations
from src.technical_audit.lifecycle import classify_lifecycle, group_findings
from src.technical_audit.runner import run_technical_audit
from src.technical_audit.site import SiteIdentity
from src.technical_audit.workflow import build_cards, persist_cards


FOUNDATION_CHECK_SETS = ("foundation",)
DEFAULT_CHECK_SETS = ("foundation", "protocol", "site_integrity", "performance")


def _get_supabase():
    from supabase import create_client

    return create_client(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
    )


def _previous_completed_results(sb, client_id: str, current_run_id: str) -> list[dict]:
    runs = (
        sb.table("technical_audit_runs")
        .select("id")
        .eq("client_id", client_id)
        .eq("status", "completed")
        .neq("id", current_run_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    if not runs.data or runs.data[0]["id"] == current_run_id:
        return []
    previous = (
        sb.table("technical_audit_results")
        .select("check_id,check_version,subject,status,observed")
        .eq("audit_run_id", runs.data[0]["id"])
        .execute()
    )
    return [row for row in (previous.data or []) if row.get("check_id")]


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
        collected = collect_site(identity)
        integrations = collect_integrations(
            collected, config.get("gsc_site_url") or ""
        ) if "performance" in enabled_check_sets else None
        report = run_technical_audit(
            client_id,
            identity,
            collected,
            enabled_check_sets=enabled_check_sets,
            integrations=integrations,
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

        previous_results = _previous_completed_results(sb, client_id, audit_run_id)
        annotated = classify_lifecycle(client_id, report["results"], previous_results)
        report["results"] = annotated
        groups = group_findings(annotated)

        result_rows = [
            {"audit_run_id": audit_run_id, **result}
            for result in annotated
        ]
        result_ids: list[str] = []
        if result_rows:
            inserted = sb.table("technical_audit_results").insert(result_rows).execute()
            result_ids = [row["id"] for row in (inserted.data or [])]

        if groups:
            group_rows = [
                {
                    "audit_run_id": audit_run_id,
                    "group_key": group["group_key"],
                    "check_id": group["check_id"],
                    "remediation_id": group["remediation_id"],
                    "summary": group["summary"],
                    "status": group["status"],
                    "subjects": group["subjects"],
                }
                for group in groups
            ]
            sb.table("technical_audit_finding_groups").insert(group_rows).execute()

        if groups and len(result_ids) == len(annotated):
            fingerprints = {
                observation["subject"]: observation["fingerprint"]
                for observation in report["observations"]
                if observation["kind"] == "page"
            }
            cards = build_cards(
                client_id=client_id,
                audit_run_id=audit_run_id,
                platform=config.get("site_platform") or "other",
                implementation_mode=config.get("implementation_mode") or "copy_paste",
                results=annotated,
                groups=groups,
                result_ids=result_ids,
                observation_fingerprints=fingerprints,
            )
            persist_cards(sb, cards)

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
    check_sets: tuple[str, ...] = DEFAULT_CHECK_SETS,
) -> dict:
    del queries
    client_id = state["client_id"]
    sb = _get_supabase()

    run_resp = sb.table("improvement_runs").insert(
        {
            "client_id": client_id,
            "status": "running",
            "thread_id": state.get("thread_id"),
        }
    ).execute()
    improvement_run_id = run_resp.data[0]["id"]

    audit = _run_and_persist_technical_audit(
        sb,
        state,
        improvement_run_id,
        check_sets,
    )
    selection = select_community_opportunities(competitive_gaps, limit=5)
    completed_at = datetime.now(timezone.utc).isoformat()
    completion = {
        "status": "error" if audit["error"] else "completed",
        "competitive_gaps_found": selection.competitor_lead_count,
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
