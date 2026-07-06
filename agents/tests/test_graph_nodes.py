from unittest.mock import MagicMock, patch

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


@patch("src.graph.nodes._get_supabase")
def test_improvement_node_fetches_gaps_without_tracker_results(mock_sb):
    """improvement_only runs (no tracker_results in state) must still load stored gaps."""
    mock_table = MagicMock()
    # queries select: .select("*").eq(...).eq(...).execute()
    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    # tracker_runs latest: .select("id").eq(...).order(...).limit(1).execute()
    mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"id": "trun-1"}])
    # competitive_gaps: .select("*").eq("run_id", ...).execute()
    mock_table.select.return_value.eq.return_value.execute.return_value = \
        MagicMock(data=[{"query": "q1", "client_mention_rate": 0.1, "competitor_data": []}])
    mock_sb.return_value.table.return_value = mock_table

    from src.graph.nodes import run_improvement_pipeline_node

    with patch("src.improvement.pipeline.run_improvement_pipeline") as mock_run:
        mock_run.return_value = {"improvement_run_id": "r1", "action_cards": []}
        state = {"client_id": "c1", "client_config": {"website_domain": "x.com"},
                 "tracker_results": []}   # improvement_only: tracker never ran
        run_improvement_pipeline_node(state)

        # Third positional arg = competitive_gaps, must be the stored rows, not []
        passed_gaps = mock_run.call_args[0][2]
        assert passed_gaps == [{"query": "q1", "client_mention_rate": 0.1, "competitor_data": []}]
