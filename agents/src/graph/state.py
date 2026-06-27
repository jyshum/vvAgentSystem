from typing import TypedDict


class GEOState(TypedDict):
    client_id: str
    client_config: dict
    tracker_results: list[dict]
    tracker_scores: dict
    gsc_metrics: dict
    audit_pages: list[dict]
    audit_summary: dict
    audit_run_id: str | None
    action_cards: list[dict]
    approved_card_ids: list[str]
    implementation_results: list[dict]
    reddit_posts: list[dict]
    run_type: str
    thread_id: str
    error: str | None
