from src.graph.pipeline import build_graph


def test_build_graph_returns_compiled_graph():
    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_build_graph_has_only_manual_evidence_nodes():
    graph = build_graph()
    nodes = set(graph.get_graph().nodes)
    assert {"load_config", "run_tracker", "run_gsc", "run_technical_pipeline"} <= nodes
    assert "await_approval" not in nodes
    assert "run_implementation" not in nodes


def test_full_run_ends_after_technical_pipeline():
    from langgraph.graph import END
    from src.graph.pipeline import route_after_gsc

    assert route_after_gsc({"run_type": "full"}) == "run_technical_pipeline"
    assert route_after_gsc({"run_type": "tracker_only"}) == END
