from src.graph.pipeline import build_graph


def test_build_graph_returns_compiled_graph():
    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_build_graph_has_expected_nodes():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "load_config" in node_names
    assert "run_tracker" in node_names
    assert "run_improvement_pipeline" in node_names
    assert "await_approval" in node_names
    assert "run_audit" not in node_names
    assert "run_recommender" not in node_names
    assert "run_implementation" in node_names


def test_route_after_improvement_skips_approval_when_all_auto_approved():
    from src.graph.pipeline import route_after_improvement
    state = {"action_cards": [
        {"status": "approved", "auto_approved": True},
        {"status": "approved", "auto_approved": True},
    ]}
    assert route_after_improvement(state) == "run_implementation"


def test_route_after_improvement_awaits_when_pending_cards_exist():
    from src.graph.pipeline import route_after_improvement
    state = {"action_cards": [
        {"status": "approved", "auto_approved": True},
        {"status": "pending"},
    ]}
    assert route_after_improvement(state) == "await_approval"


def test_route_after_improvement_ends_when_no_cards():
    from langgraph.graph import END
    from src.graph.pipeline import route_after_improvement
    assert route_after_improvement({"action_cards": []}) == END
