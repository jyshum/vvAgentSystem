import os
import threading
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from src.graph.pipeline import build_graph

API_KEY = os.environ.get("API_KEY", "dev-key")

def _build_checkpointer():
    """Build the Postgres-backed graph checkpointer when configured.

    Requires DATABASE_URL (Supabase direct connection string, port 5432).
    Returns None when unset — build_graph falls back to MemorySaver (local dev).
    """
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return None
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres import PostgresSaver
    min_size = int(os.environ.get("DB_POOL_MIN_SIZE", "4"))
    max_size = int(os.environ.get("DB_POOL_MAX_SIZE", "4"))
    # Pool intentionally lives for the process lifetime — no close handler.
    pool = ConnectionPool(
        db_url,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        open=True,
        min_size=min_size,
        max_size=max_size,
    )
    saver = PostgresSaver(pool)
    print("  [Checkpointer] Connecting to Postgres...")
    saver.setup()
    print("  [Checkpointer] PostgresSaver enabled")
    return saver


graph = build_graph(checkpointer=_build_checkpointer())


def _get_supabase():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


@asynccontextmanager
async def lifespan(app):
    if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
        print(
            "  [Tracing] LangSmith enabled — project: "
            f"{os.environ.get('LANGCHAIN_PROJECT', 'default')}"
        )
    yield


app = FastAPI(title="GEO Agent API", lifespan=lifespan)


def verify_auth(authorization: str | None = None):
    if not authorization or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API key")


class RunRequest(BaseModel):
    client_id: str
    run_type: str = "full"


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
                "competitive_gaps": [],
                "improvement_run_id": None,
                "technical_audit_run_id": None,
                "technical_audit_summary": {},
                "technical_audit_results": [],
                "technical_audit_error": None,
                "community_opportunities": [],
                "error": None,
            },
            config=config,
        )

        state = graph.get_state(config=config)
        state_error = (state.values or {}).get("error")
        if state_error:
            sb.table("pipeline_runs").update({
                "status": "error",
                "error_message": str(state_error)[:500],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("thread_id", thread_id).execute()
            print(f"  [Pipeline] Finished with error for {client_id}: {state_error}")
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


@app.get("/api/status/{thread_id}")
async def get_status(thread_id: str, authorization: str | None = Header(None)):
    verify_auth(authorization)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = graph.get_state(config=config)
        return {
            "next": list(state.next) if state.next else [],
            "has_pending_approval": False,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
