from typing import TypedDict


class GEOState(TypedDict):
    client_id: str
    client_config: dict
    tracker_results: list[dict]
    tracker_scores: dict
    gsc_metrics: dict
    run_type: str
    thread_id: str
    error: str | None

    # Improvement pipeline fields
    improvement_run_id: str | None
    crawlability_report: dict
    page_inventory: list[dict]
    query_matches: list[dict]
    citation_scores: list[dict]
    competitive_gap_data: list[dict]
    action_cards: list[dict]
    approved_card_ids: list[str]
    implementation_results: list[dict]
