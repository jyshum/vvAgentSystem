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
def test_tracker_run_insert_includes_thread_id(mock_sb):
    """tracker_runs insert must carry the pipeline thread_id so the approvals
    inbox and run-detail page can join back to the originating thread."""
    mock_table = MagicMock()
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


@patch("src.graph.nodes._get_supabase")
def test_implementation_skips_auto_approved_card_without_id(mock_sb):
    """Id-less cards (partial insert) must never reach route_card — no audit trail."""
    mock_sb.return_value.table.return_value = MagicMock()

    from src.graph.nodes import run_implementation_node

    with patch("src.implementors.router.route_card") as mock_route:
        state = {
            "client_config": {"cms_type": "wordpress", "cms_config": {}},
            "action_cards": [
                {"action_type": "add_faq_schema", "status": "approved", "auto_approved": True},  # no id
            ],
            "approved_card_ids": [],
        }
        result = run_implementation_node(state)

        mock_route.assert_not_called()
        assert result["implementation_results"] == []


@patch("src.graph.nodes._get_supabase")
def test_implementation_runs_auto_approved_card_with_id(mock_sb):
    mock_sb.return_value.table.return_value = MagicMock()

    from src.graph.nodes import run_implementation_node

    with patch("src.implementors.router.route_card") as mock_route:
        mock_route.return_value = {"status": "implemented"}
        state = {
            "client_config": {"cms_type": "wordpress", "cms_config": {}},
            "action_cards": [
                {"id": "card-1", "action_type": "add_faq_schema", "status": "approved", "auto_approved": True},
            ],
            "approved_card_ids": [],
        }
        result = run_implementation_node(state)

        mock_route.assert_called_once()
        assert result["implementation_results"][0]["card_id"] == "card-1"


@patch("src.improvement.verifier.verify_implementation")
@patch("src.implementors.router.route_card")
@patch("src.graph.nodes._get_supabase")
def test_implementation_node_verifies_implemented_cards(mock_sb, mock_route, mock_verify):
    mock_table = MagicMock()
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_sb.return_value.table.return_value = mock_table

    mock_route.return_value = {"status": "implemented"}
    mock_verify.return_value = {"verified": True, "skipped": False,
                                "checks": {"page_renders": True, "change_present": True},
                                "error": None, "checked_at": "2026-07-04T00:00:00Z"}

    from src.graph.nodes import run_implementation_node
    state = {
        "client_config": {"cms_type": "wordpress", "cms_config": {}},
        "action_cards": [{"id": "card-1", "page_url": "https://x.com/p1",
                          "action_type": "add_faq_schema", "code_block": "{}", "after_text": ""}],
        "approved_card_ids": ["card-1"],
    }
    result = run_implementation_node(state)

    mock_verify.assert_called_once()
    assert result["implementation_results"][0]["verification"]["verified"] is True
    # verification persisted to the card row
    update_payload = mock_table.update.call_args[0][0]
    assert "verification" in update_payload


@patch("src.improvement.verifier.verify_implementation")
@patch("src.implementors.router.route_card")
@patch("src.graph.nodes._get_supabase")
def test_implementation_node_skips_verification_for_non_implemented_status(mock_sb, mock_route, mock_verify):
    mock_table = MagicMock()
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_sb.return_value.table.return_value = mock_table

    mock_route.return_value = {"status": "approved"}

    from src.graph.nodes import run_implementation_node
    state = {
        "client_config": {"cms_type": "copy_paste", "cms_config": {}},
        "action_cards": [{"id": "card-1", "page_url": "https://x.com/p1",
                          "action_type": "restructure_intro", "code_block": "", "after_text": "x"}],
        "approved_card_ids": ["card-1"],
    }
    result = run_implementation_node(state)

    mock_verify.assert_not_called()
    assert "verification" not in result["implementation_results"][0]
    update_payload = mock_table.update.call_args[0][0]
    assert "verification" not in update_payload


@patch("src.improvement.verifier.verify_implementation")
@patch("src.implementors.router.route_card")
@patch("src.graph.nodes._get_supabase")
def test_implementation_persists_pr_url(mock_sb, mock_route, mock_verify):
    mock_table = MagicMock()
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_sb.return_value.table.return_value = mock_table

    mock_route.return_value = {"status": "implemented", "pr_url": "https://github.com/x/y/pull/1"}
    mock_verify.return_value = {"verified": True, "skipped": False,
                                "checks": {}, "error": None, "checked_at": "2026-07-04T00:00:00Z"}

    from src.graph.nodes import run_implementation_node
    state = {
        "client_config": {"cms_type": "github", "cms_config": {}},
        "action_cards": [{"id": "card-1", "page_url": "https://x.com/p1",
                          "action_type": "add_faq_schema", "code_block": "{}", "after_text": ""}],
        "approved_card_ids": ["card-1"],
    }
    run_implementation_node(state)

    update_payload = mock_table.update.call_args[0][0]
    assert update_payload["preview_url"] == "https://github.com/x/y/pull/1"


@patch("src.improvement.verifier.verify_implementation")
@patch("src.implementors.router.route_card")
@patch("src.graph.nodes._get_supabase")
def test_implementation_persists_webflow_preview_url(mock_sb, mock_route, mock_verify):
    mock_table = MagicMock()
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_sb.return_value.table.return_value = mock_table

    mock_route.return_value = {"status": "implemented", "preview_url": "https://site.webflow.io/page"}
    mock_verify.return_value = {"verified": True, "skipped": False,
                                "checks": {}, "error": None, "checked_at": "2026-07-04T00:00:00Z"}

    from src.graph.nodes import run_implementation_node
    state = {
        "client_config": {"cms_type": "webflow", "cms_config": {}},
        "action_cards": [{"id": "card-1", "page_url": "https://x.com/p1",
                          "action_type": "add_faq_schema", "code_block": "{}", "after_text": ""}],
        "approved_card_ids": ["card-1"],
    }
    run_implementation_node(state)

    update_payload = mock_table.update.call_args[0][0]
    assert update_payload["preview_url"] == "https://site.webflow.io/page"


@patch("src.improvement.verifier.verify_implementation")
@patch("src.implementors.router.route_card")
@patch("src.graph.nodes._get_supabase")
def test_no_preview_url_key_when_absent(mock_sb, mock_route, mock_verify):
    mock_table = MagicMock()
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_sb.return_value.table.return_value = mock_table

    mock_route.return_value = {"status": "implemented"}
    mock_verify.return_value = {"verified": True, "skipped": False,
                                "checks": {}, "error": None, "checked_at": "2026-07-04T00:00:00Z"}

    from src.graph.nodes import run_implementation_node
    state = {
        "client_config": {"cms_type": "copy_paste", "cms_config": {}},
        "action_cards": [{"id": "card-1", "page_url": "https://x.com/p1",
                          "action_type": "add_faq_schema", "code_block": "{}", "after_text": ""}],
        "approved_card_ids": ["card-1"],
    }
    run_implementation_node(state)

    update_payload = mock_table.update.call_args[0][0]
    assert "preview_url" not in update_payload
