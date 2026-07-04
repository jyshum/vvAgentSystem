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
