from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.graph.state import GEOState
from src.graph.nodes import (
    load_config,
    run_tracker_node,
    run_gsc_node,
    run_audit_node,
    run_recommender_node,
    await_approval,
    run_implementation_node,
)


def route_after_config(state: GEOState) -> str:
    if state.get("run_type") == "audit_only":
        return "run_audit"
    return "run_tracker"


def route_after_tracker(state: GEOState) -> str:
    return "run_gsc"


def route_after_gsc(state: GEOState) -> str:
    if state.get("run_type") == "tracker_only":
        return END
    return "run_audit"


def build_graph(checkpointer=None):
    graph = StateGraph(GEOState)

    graph.add_node("load_config", load_config)
    graph.add_node("run_tracker", run_tracker_node)
    graph.add_node("run_gsc", run_gsc_node)
    graph.add_node("run_audit", run_audit_node)
    graph.add_node("run_recommender", run_recommender_node)
    graph.add_node("await_approval", await_approval)
    graph.add_node("run_implementation", run_implementation_node)

    graph.set_entry_point("load_config")

    graph.add_conditional_edges("load_config", route_after_config, {
        "run_tracker": "run_tracker",
        "run_audit": "run_audit",
    })

    graph.add_edge("run_tracker", "run_gsc")

    graph.add_conditional_edges("run_gsc", route_after_gsc, {
        END: END,
        "run_audit": "run_audit",
    })

    graph.add_edge("run_audit", "run_recommender")
    graph.add_edge("run_recommender", "await_approval")
    graph.add_edge("await_approval", "run_implementation")
    graph.add_edge("run_implementation", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
