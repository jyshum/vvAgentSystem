from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.graph.state import GEOState
from src.graph.nodes import (
    load_config,
    run_tracker_node,
    run_gsc_node,
    run_improvement_pipeline_node,
    await_approval,
    run_implementation_node,
)


def route_after_config(state: GEOState) -> str:
    if state.get("run_type") == "improvement_only":
        return "run_improvement_pipeline"
    return "run_tracker"


def route_after_gsc(state: GEOState) -> str:
    if state.get("run_type") == "tracker_only":
        return END
    return "run_improvement_pipeline"


def build_graph(checkpointer=None):
    graph = StateGraph(GEOState)

    graph.add_node("load_config", load_config)
    graph.add_node("run_tracker", run_tracker_node)
    graph.add_node("run_gsc", run_gsc_node)
    graph.add_node("run_improvement_pipeline", run_improvement_pipeline_node)
    graph.add_node("await_approval", await_approval)
    graph.add_node("run_implementation", run_implementation_node)

    graph.set_entry_point("load_config")

    graph.add_conditional_edges("load_config", route_after_config, {
        "run_tracker": "run_tracker",
        "run_improvement_pipeline": "run_improvement_pipeline",
    })

    graph.add_edge("run_tracker", "run_gsc")

    graph.add_conditional_edges("run_gsc", route_after_gsc, {
        END: END,
        "run_improvement_pipeline": "run_improvement_pipeline",
    })

    graph.add_edge("run_improvement_pipeline", "await_approval")
    graph.add_edge("await_approval", "run_implementation")
    graph.add_edge("run_implementation", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
