from unittest.mock import MagicMock, patch

from src.graph.state import GEOState


@patch("supabase.create_client")
def test_load_config_includes_unified_site_fields(mock_create_client, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-key")
    client_table = MagicMock()
    client_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={
            "brand_name": "Budget Your MD",
            "website_domain": "budgetyourmd.ca",
            "brand_variations": [],
            "competitors": [],
            "gsc_site_url": "",
            "site_platform": "squarespace",
            "implementation_mode": "copy_paste",
        }
    )
    query_table = MagicMock()
    query_table.select.return_value.eq.return_value.eq.return_value.order.return_value.order.return_value.execute.return_value = MagicMock(
        data=[]
    )
    sb = MagicMock()
    sb.table.side_effect = lambda name: {
        "clients": client_table,
        "queries": query_table,
    }[name]
    mock_create_client.return_value = sb

    from src.graph.nodes import load_config

    result = load_config({"client_id": "client-1"})

    assert result["client_config"]["site_platform"] == "squarespace"
    assert result["client_config"]["implementation_mode"] == "copy_paste"


def test_geo_state_has_required_keys():
    state = GEOState(
        client_id="test-uuid",
        client_config={},
        tracker_results=[],
        tracker_scores={},
        gsc_metrics={},
        competitive_gaps=[],
        run_type="full",
        thread_id="test-thread",
        improvement_run_id=None,
        technical_audit_run_id=None,
        technical_audit_summary={},
        technical_audit_results=[],
        technical_audit_error=None,
        community_opportunities=[],
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
        gsc_metrics={},
        competitive_gaps=[],
        run_type="tracker_only",
        thread_id="thread-1",
        improvement_run_id=None,
        technical_audit_run_id=None,
        technical_audit_summary={},
        technical_audit_results=[],
        technical_audit_error=None,
        community_opportunities=[],
        error=None,
    )
    assert state["tracker_results"][0]["query"] == "test"
    assert state["run_type"] == "tracker_only"


@patch("src.graph.nodes._get_supabase")
def test_tracker_run_insert_includes_thread_id(mock_sb):
    """tracker_runs insert must carry the pipeline thread_id so the approvals
    inbox and run-detail page can join back to the originating thread."""
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[])
    mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[])
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-1"}])
    mock_sb.return_value.table.return_value = mock_table

    from src.graph.nodes import run_tracker_node

    with patch("src.tracker.run_tracker") as mock_run_tracker, \
         patch("src.tracker.compute_competitive_gaps") as mock_gaps, \
         patch("src.upload._compute_prompt_scores") as mock_prompt_scores, \
         patch("src.upload._build_competitive_gap_rows") as mock_gap_rows:
        mock_run_tracker.return_value = ([], {"aggregate_mention_rate": 0, "aggregate_avg_mention_level": 0,
                                              "per_engine": {}, "competitor_scores": {}})
        mock_gaps.return_value = []
        mock_prompt_scores.return_value = []
        mock_gap_rows.return_value = []

        state = {
            "client_id": "c1",
            "client_config": {"competitors": []},
            "thread_id": "client-20260707-000000",
        }
        run_tracker_node(state)

        inserted = mock_table.insert.call_args_list[0][0][0]
        assert inserted["thread_id"] == "client-20260707-000000"


@patch("src.graph.nodes._get_supabase")
def test_run_tracker_node_writes_drift_signature(mock_sb):
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[])
    mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"query_set_signature": "previous-signature"}])
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "run-1"}])
    mock_sb.return_value.table.return_value = mock_table

    from src.drift import compute_query_set_signature
    from src.graph.nodes import run_tracker_node

    intents = [
        {"id": "q1", "slug": "awareness-budgeting", "version": 1,
         "prompt_text": "how to budget in medical school", "bucket": "awareness",
         "paraphrases": ["medical student budgeting tips"]},
    ]
    expected_signature = compute_query_set_signature(intents)

    with patch("src.tracker.run_tracker") as mock_run_tracker, \
         patch("src.tracker.compute_competitive_gaps") as mock_gaps, \
         patch("src.upload._compute_prompt_scores") as mock_prompt_scores, \
         patch("src.upload._build_competitive_gap_rows") as mock_gap_rows:
        mock_run_tracker.return_value = ([], {"aggregate_mention_rate": 0, "aggregate_avg_mention_level": 0,
                                              "per_engine": {}, "competitor_scores": {}})
        mock_gaps.return_value = []
        mock_prompt_scores.return_value = []
        mock_gap_rows.return_value = []

        state = {
            "client_id": "c1",
            "client_config": {"competitors": [], "target_queries": intents},
            "thread_id": "client-20260707-000000",
        }
        run_tracker_node(state)

    inserted = mock_table.insert.call_args_list[0][0][0]
    assert inserted["query_set_signature"] == expected_signature
    assert inserted["query_set_changed"] is True


@patch("src.graph.nodes._get_supabase")
def test_technical_node_fetches_gaps_without_tracker_results(mock_sb):
    """Technical-only runs must still load the most recently stored gaps."""
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

    from src.graph.nodes import run_technical_pipeline_node

    with patch("src.technical_audit.pipeline.run_technical_pipeline") as mock_run:
        mock_run.return_value = {
            "improvement_run_id": "r1",
            "community_opportunities": [],
        }
        state = {"client_id": "c1", "client_config": {"website_domain": "x.com"},
                 "tracker_results": []}
        run_technical_pipeline_node(state)

        # Third positional arg = competitive_gaps, must be the stored rows, not []
        passed_gaps = mock_run.call_args[0][2]
        assert passed_gaps == [{"query": "q1", "client_mention_rate": 0.1, "competitor_data": []}]


@patch("src.graph.nodes._get_supabase")
def test_technical_node_returns_evidence_only_error_state(mock_sb):
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[])
    mock_sb.return_value.table.return_value = mock_table

    from src.graph.nodes import run_technical_pipeline_node

    with patch(
        "src.technical_audit.pipeline.run_technical_pipeline",
        side_effect=RuntimeError("pipeline failed"),
    ):
        result = run_technical_pipeline_node({
            "client_id": "c1",
            "client_config": {"website_domain": "x.com"},
            "tracker_results": [],
        })

    assert result["technical_audit_run_id"] is None
    assert result["technical_audit_summary"] == {}
    assert result["technical_audit_results"] == []
    assert result["technical_audit_error"] == "pipeline failed"
    assert result["community_opportunities"] == []
    assert result["error"] == "pipeline failed"
