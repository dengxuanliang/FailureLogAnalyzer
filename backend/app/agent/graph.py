"""Build and compile the Orchestrator Agent LangGraph StateGraph."""
from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.agent.checkpointer import create_checkpointer
from app.agent.intent_router import classify_intent
from app.agent.nodes.analyze_node import analyze_node
from app.agent.nodes.compare_node import compare_node
from app.agent.nodes.human_review_node import human_review_node
from app.agent.nodes.ingest_node import ingest_node
from app.agent.nodes.query_node import query_node
from app.agent.nodes.report_node import report_node
from app.agent.state import OrchestratorState


def route_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """Classify intent and record user message."""
    _ = config
    intent = classify_intent(state["user_input"])
    return {
        "intent": intent,
        "conversation_history": [{"role": "user", "content": state["user_input"]}],
    }


def route_by_intent(
    state: OrchestratorState,
) -> Literal["ingest", "analyze", "compare", "query", "report"]:
    intent = state.get("intent", "query")
    if intent in {"ingest", "analyze", "compare", "query", "report"}:
        return intent
    return "query"


def check_human_review(state: OrchestratorState) -> Literal["human_review", "end"]:
    if state.get("needs_human_input", False):
        return "human_review"
    return "end"


_compiled_graph = None


def build_graph(checkpointer: Any | None = None):
    """Build and compile singleton orchestrator graph."""
    global _compiled_graph
    if _compiled_graph is not None and checkpointer is None:
        return _compiled_graph

    graph = StateGraph(OrchestratorState)
    graph.add_node("route", route_node)
    graph.add_node("ingest", ingest_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("compare", compare_node)
    graph.add_node("query", query_node)
    graph.add_node("report", report_node)
    graph.add_node("human_review", human_review_node)

    graph.set_entry_point("route")

    graph.add_conditional_edges(
        "route",
        route_by_intent,
        {
            "ingest": "ingest",
            "analyze": "analyze",
            "compare": "compare",
            "query": "query",
            "report": "report",
        },
    )

    graph.add_edge("ingest", END)
    graph.add_edge("compare", END)
    graph.add_edge("query", END)
    graph.add_edge("report", END)

    graph.add_conditional_edges(
        "analyze",
        check_human_review,
        {"human_review": "human_review", "end": END},
    )
    graph.add_edge("human_review", END)

    if checkpointer is None:
        checkpointer = create_checkpointer()

    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )

    if checkpointer is not None:
        _compiled_graph = compiled

    return compiled
