from typing import TypedDict


class GEOState(TypedDict):
    client_id: str
    client_config: dict
    tracker_results: list[dict]
    tracker_scores: dict
    gsc_metrics: dict
    competitive_gaps: list[dict]
    run_type: str
    thread_id: str
    improvement_run_id: str | None
    technical_audit_run_id: str | None
    technical_audit_summary: dict
    technical_audit_results: list[dict]
    technical_audit_error: str | None
    community_opportunities: list[dict]
    error: str | None
