from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.graph.state import GEOState
from src.graph.nodes import (
    load_config,
    run_tracker_node,
    run_gsc_node,
    run_technical_pipeline_node,
)


def route_after_config(state: GEOState) -> str:
    if state.get("run_type") == "technical_only":
        return "run_technical_pipeline"
    return "run_tracker"


def route_after_gsc(state: GEOState) -> str:
    if state.get("run_type") == "tracker_only":
        return END
    return "run_technical_pipeline"


def build_graph(checkpointer=None):
    graph = StateGraph(GEOState)

    graph.add_node("load_config", load_config)
    graph.add_node("run_tracker", run_tracker_node)
    graph.add_node("run_gsc", run_gsc_node)
    graph.add_node("run_technical_pipeline", run_technical_pipeline_node)

    graph.set_entry_point("load_config")

    graph.add_conditional_edges("load_config", route_after_config, {
        "run_tracker": "run_tracker",
        "run_technical_pipeline": "run_technical_pipeline",
    })

    graph.add_edge("run_tracker", "run_gsc")

    graph.add_conditional_edges("run_gsc", route_after_gsc, {
        END: END,
        "run_technical_pipeline": "run_technical_pipeline",
    })
    graph.add_edge("run_technical_pipeline", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
