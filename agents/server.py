import os
import threading
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from src.graph.pipeline import build_graph
from langgraph.types import Command
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

API_KEY = os.environ.get("API_KEY", "dev-key")

def _build_checkpointer():
    """Postgres-backed checkpointer so paused approval threads survive restarts.

    Requires DATABASE_URL (Supabase direct connection string, port 5432).
    Returns None when unset — build_graph falls back to MemorySaver (local dev).
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return None
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres import PostgresSaver
    pool = ConnectionPool(db_url, kwargs={"autocommit": True, "prepare_threshold": 0}, open=True)
    saver = PostgresSaver(pool)
    saver.setup()
    print("  [Checkpointer] PostgresSaver enabled")
    return saver


graph = build_graph(checkpointer=_build_checkpointer())
scheduler = BackgroundScheduler()


def _get_supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def trigger_scheduled_run(client_id: str):
    thread_id = f"{client_id}-scheduled-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}
    sb = _get_supabase()
    print(f"  [Scheduler] Starting pipeline for {client_id} (thread: {thread_id})")

    sb.table("pipeline_runs").insert({
        "client_id": client_id,
        "thread_id": thread_id,
        "run_type": "full",
        "status": "running",
    }).execute()

    try:
        graph.invoke(
            {
                "client_id": client_id,
                "run_type": "full",
                "thread_id": thread_id,
                "client_config": {},
                "tracker_results": [],
                "tracker_scores": {},
                "gsc_metrics": {},
                "improvement_run_id": None,
                "crawlability_report": {},
                "page_inventory": [],
                "query_matches": [],
                "citation_scores": [],
                "competitive_gap_data": [],
                "reddit_scout_data": [],
                "action_cards": [],
                "approved_card_ids": [],
                "implementation_results": [],
                "error": None,
            },
            config=config,
        )

        state = graph.get_state(config=config)
        if state.next and "await_approval" in state.next:
            sb.table("pipeline_runs").update({
                "status": "awaiting_approval",
            }).eq("thread_id", thread_id).execute()
            print(f"  [Scheduler] Pipeline paused at approval for {client_id}")
        else:
            sb.table("pipeline_runs").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("thread_id", thread_id).execute()
            print(f"  [Scheduler] Pipeline completed for {client_id}")
    except Exception as e:
        sb.table("pipeline_runs").update({
            "status": "error",
            "error_message": str(e)[:500],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("thread_id", thread_id).execute()
        print(f"  [Scheduler] Pipeline failed for {client_id}: {e}")


def load_schedules():
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        result = sb.table("clients").select("id, cycle_frequency, cycle_day").execute()

        day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}

        # Remove all existing cycle jobs before re-adding
        for job in scheduler.get_jobs():
            if job.id.startswith("cycle-"):
                scheduler.remove_job(job.id)

        offset_minutes = 0

        for client in result.data:
            client_id = client["id"]
            frequency = client.get("cycle_frequency", "weekly")
            cycle_day = day_map.get(client.get("cycle_day", 1), "tue")

            if frequency == "monthly":
                trigger = CronTrigger(day="1", hour=2, minute=offset_minutes)
            elif frequency == "biweekly":
                trigger = CronTrigger(day_of_week=cycle_day, hour=2, minute=offset_minutes, week="*/2")
            else:
                trigger = CronTrigger(day_of_week=cycle_day, hour=2, minute=offset_minutes)

            scheduler.add_job(
                trigger_scheduled_run,
                trigger=trigger,
                args=[client_id],
                id=f"cycle-{client_id}",
                replace_existing=True,
            )
            label = f"{cycle_day} 02:{offset_minutes:02d}" if frequency != "monthly" else f"1st of month 02:{offset_minutes:02d}"
            print(f"  [Scheduler] Scheduled {client_id} ({frequency}) for {label}")
            offset_minutes += 15

    except Exception as e:
        print(f"  [Scheduler] Failed to load schedules: {e}")


@asynccontextmanager
async def lifespan(app):
    if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
        print(f"  [Tracing] LangSmith enabled — project: {os.environ.get('LANGCHAIN_PROJECT', 'default')}")
    load_schedules()
    scheduler.start()
    print("  [Scheduler] Started")
    yield
    scheduler.shutdown()
    print("  [Scheduler] Stopped")


app = FastAPI(title="GEO Agent API", lifespan=lifespan)


def verify_auth(authorization: str | None = None):
    if not authorization or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API key")


class RunRequest(BaseModel):
    client_id: str
    run_type: str = "full"


class ApproveRequest(BaseModel):
    thread_id: str
    approved_card_ids: list[str]


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


def _run_graph_background(client_id: str, run_type: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    sb = _get_supabase()

    sb.table("pipeline_runs").insert({
        "client_id": client_id,
        "thread_id": thread_id,
        "run_type": run_type,
        "status": "running",
    }).execute()

    try:
        graph.invoke(
            {
                "client_id": client_id,
                "run_type": run_type,
                "thread_id": thread_id,
                "client_config": {},
                "tracker_results": [],
                "tracker_scores": {},
                "gsc_metrics": {},
                "improvement_run_id": None,
                "crawlability_report": {},
                "page_inventory": [],
                "query_matches": [],
                "citation_scores": [],
                "competitive_gap_data": [],
                "reddit_scout_data": [],
                "action_cards": [],
                "approved_card_ids": [],
                "implementation_results": [],
                "error": None,
            },
            config=config,
        )

        state = graph.get_state(config=config)
        if state.next and "await_approval" in state.next:
            sb.table("pipeline_runs").update({
                "status": "awaiting_approval",
            }).eq("thread_id", thread_id).execute()
            print(f"  [Pipeline] Paused at approval for {client_id} (thread: {thread_id})")
        else:
            sb.table("pipeline_runs").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("thread_id", thread_id).execute()
            print(f"  [Pipeline] Completed {run_type} for {client_id} (thread: {thread_id})")
    except Exception as e:
        sb.table("pipeline_runs").update({
            "status": "error",
            "error_message": str(e)[:500],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("thread_id", thread_id).execute()
        print(f"  [Pipeline] Failed {run_type} for {client_id}: {e}")


@app.post("/api/run")
async def trigger_run(req: RunRequest, authorization: str | None = Header(None)):
    verify_auth(authorization)
    thread_id = f"{req.client_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    t = threading.Thread(
        target=_run_graph_background,
        args=(req.client_id, req.run_type, thread_id),
        daemon=True,
    )
    t.start()

    return {"thread_id": thread_id, "status": "started"}


@app.post("/api/approve")
async def approve_cards(req: ApproveRequest, authorization: str | None = Header(None)):
    verify_auth(authorization)
    config = {"configurable": {"thread_id": req.thread_id}}

    sb = _get_supabase()
    sb.table("pipeline_runs").update({
        "status": "implementing",
    }).eq("thread_id", req.thread_id).execute()

    try:
        result = graph.invoke(
            Command(resume=req.approved_card_ids),
            config=config,
        )
        sb.table("pipeline_runs").update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("thread_id", req.thread_id).execute()

        return {"status": "implementation_complete", "results": result.get("implementation_results", [])}
    except Exception as e:
        sb.table("pipeline_runs").update({
            "status": "error",
            "error_message": str(e)[:500],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("thread_id", req.thread_id).execute()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{thread_id}")
async def get_status(thread_id: str, authorization: str | None = Header(None)):
    verify_auth(authorization)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = graph.get_state(config=config)
        return {
            "next": list(state.next) if state.next else [],
            "has_pending_approval": "await_approval" in (state.next or []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reload-schedules")
async def reload_schedules(authorization: str | None = Header(None)):
    verify_auth(authorization)
    load_schedules()
    jobs = [{"id": j.id, "next_run": j.next_run_time.isoformat() if j.next_run_time else None} for j in scheduler.get_jobs() if j.id.startswith("cycle-")]
    return {"status": "reloaded", "jobs": jobs}


@app.get("/api/schedules")
async def get_schedules(authorization: str | None = Header(None)):
    verify_auth(authorization)
    sb = _get_supabase()

    clients_resp = sb.table("clients").select("id, brand_name, cycle_frequency, cycle_day").execute()
    client_map = {c["id"]: c for c in clients_resp.data}

    runs_resp = sb.table("pipeline_runs").select("client_id, status, started_at").order("started_at", desc=True).execute()
    latest_runs = {}
    for run in runs_resp.data:
        cid = run["client_id"]
        if cid not in latest_runs:
            latest_runs[cid] = run

    day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
    schedules = []
    for job in scheduler.get_jobs():
        if not job.id.startswith("cycle-"):
            continue
        client_id = job.id.replace("cycle-", "")
        client = client_map.get(client_id, {})
        last_run = latest_runs.get(client_id)

        schedules.append({
            "client_id": client_id,
            "client_name": client.get("brand_name", "Unknown"),
            "cycle_frequency": client.get("cycle_frequency", "weekly"),
            "cycle_day": day_map.get(client.get("cycle_day", 1), "tue"),
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "last_run_status": last_run["status"] if last_run else None,
            "last_run_at": last_run["started_at"] if last_run else None,
        })

    return {"schedules": schedules}


@app.post("/api/run-all")
async def run_all_clients(authorization: str | None = Header(None)):
    verify_auth(authorization)
    sb = _get_supabase()
    result = sb.table("clients").select("id").execute()
    threads = []
    for client in result.data:
        client_id = client["id"]
        thread_id = f"{client_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        t = threading.Thread(
            target=_run_graph_background,
            args=(client_id, "full", thread_id),
            daemon=True,
        )
        t.start()
        threads.append({"client_id": client_id, "thread_id": thread_id})
    return {"status": "started", "count": len(threads), "runs": threads}
