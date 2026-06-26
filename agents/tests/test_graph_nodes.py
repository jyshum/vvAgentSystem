from src.graph.state import GEOState


def test_geo_state_has_required_keys():
    state = GEOState(
        client_id="test-uuid",
        client_config={},
        tracker_results=[],
        tracker_scores={},
        audit_pages=[],
        audit_summary={},
        action_cards=[],
        approved_card_ids=[],
        implementation_results=[],
        reddit_posts=[],
        run_type="full",
        thread_id="test-thread",
        error=None,
    )
    assert state["client_id"] == "test-uuid"
    assert state["run_type"] == "full"


def test_geo_state_accepts_partial_data():
    state = GEOState(
        client_id="abc",
        client_config={"brand_name": "Test"},
        tracker_results=[{"query": "test", "engine": "chatgpt"}],
        tracker_scores={"aggregate_mention_rate": 50},
        audit_pages=[],
        audit_summary={},
        action_cards=[],
        approved_card_ids=[],
        implementation_results=[],
        reddit_posts=[],
        run_type="tracker_only",
        thread_id="thread-1",
        error=None,
    )
    assert state["tracker_results"][0]["query"] == "test"
    assert state["run_type"] == "tracker_only"
