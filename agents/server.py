import os
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from src.graph.pipeline import build_graph
from langgraph.types import Command

API_KEY = os.environ.get("API_KEY", "dev-key")

app = FastAPI(title="GEO Agent API")
graph = build_graph()


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


@app.post("/api/run")
async def trigger_run(req: RunRequest, authorization: str | None = Header(None)):
    verify_auth(authorization)
    thread_id = f"{req.client_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        graph.invoke(
            {
                "client_id": req.client_id,
                "run_type": req.run_type,
                "thread_id": thread_id,
                "client_config": {},
                "tracker_results": [],
                "tracker_scores": {},
                "audit_pages": [],
                "audit_summary": {},
                "action_cards": [],
                "approved_card_ids": [],
                "implementation_results": [],
                "reddit_posts": [],
                "error": None,
            },
            config=config,
        )
        return {"thread_id": thread_id, "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
