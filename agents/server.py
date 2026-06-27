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

graph = build_graph()
scheduler = BackgroundScheduler()


def trigger_scheduled_run(client_id: str):
    thread_id = f"{client_id}-scheduled-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}
    print(f"  [Scheduler] Starting pipeline for {client_id} (thread: {thread_id})")

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
                "audit_pages": [],
                "audit_summary": {},
                "audit_run_id": None,
                "action_cards": [],
                "approved_card_ids": [],
                "implementation_results": [],
                "reddit_posts": [],
                "error": None,
            },
            config=config,
        )
        print(f"  [Scheduler] Pipeline paused at approval for {client_id}")
    except Exception as e:
        print(f"  [Scheduler] Pipeline failed for {client_id}: {e}")


def load_schedules():
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        result = sb.table("clients").select("id, cycle_frequency, cycle_day").execute()

        day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        offset_minutes = 0

        for client in result.data:
            client_id = client["id"]
            cycle_day = day_map.get(client.get("cycle_day", 1), "mon")

            trigger = CronTrigger(
                day_of_week=cycle_day,
                hour=2,
                minute=offset_minutes,
            )

            scheduler.add_job(
                trigger_scheduled_run,
                trigger=trigger,
                args=[client_id],
                id=f"cycle-{client_id}",
                replace_existing=True,
            )
            print(f"  [Scheduler] Scheduled {client_id} for {cycle_day} 02:{offset_minutes:02d}")
            offset_minutes += 15

    except Exception as e:
        print(f"  [Scheduler] Failed to load schedules: {e}")


@asynccontextmanager
async def lifespan(app):
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
                "audit_pages": [],
                "audit_summary": {},
                "audit_run_id": None,
                "action_cards": [],
                "approved_card_ids": [],
                "implementation_results": [],
                "reddit_posts": [],
                "error": None,
            },
            config=config,
        )
        print(f"  [Pipeline] Completed {run_type} for {client_id} (thread: {thread_id})")
    except Exception as e:
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

    try:
        result = graph.invoke(
            Command(resume=req.approved_card_ids),
            config=config,
        )
        return {"status": "implementation_complete", "results": result.get("implementation_results", [])}
    except Exception as e:
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
