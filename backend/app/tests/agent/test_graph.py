"""Tests for the compiled LangGraph StateGraph."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.graph import build_graph
from app.agent.state import create_initial_state


def test_build_graph_returns_compiled_graph() -> None:
    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_graph_routes_to_query_for_summary_input() -> None:
    graph = build_graph()
    state = create_initial_state(user_input="查看分析概览")
    state["target_filters"] = {"query_type": "summary"}

    mock_db = MagicMock()
    with patch("app.agent.nodes.query_node.get_analysis_summary", new_callable=AsyncMock) as mock_summary:
        mock_summary.return_value = {
            "total_sessions": 5,
            "total_records": 1000,
            "total_errors": 300,
            "accuracy": 0.7,
            "llm_analysed_count": 50,
            "llm_total_cost": 1.23,
        }
        result = asyncio.run(
            graph.ainvoke(state, config={"configurable": {"thread_id": "t-query", "db": mock_db}})
        )

    assert result["intent"] == "query"
    assert result["current_step"] == "query_done"


def test_graph_routes_to_ingest() -> None:
    graph = build_graph()
    state = create_initial_state(user_input="上传 /data/test.jsonl")
    state["target_filters"] = {"file_path": "/data/test.jsonl"}

    with patch("app.agent.nodes.ingest_node.parse_file") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "job-1"
        mock_task.apply_async.return_value = mock_result

        result = asyncio.run(graph.ainvoke(state, config={"configurable": {"thread_id": "t-ingest"}}))

    assert result["intent"] == "ingest"
    assert result["current_step"] == "ingest_dispatched"


def test_graph_routes_to_analyze() -> None:
    graph = build_graph()
    state = create_initial_state(user_input="分析错题")
    state["target_session_ids"] = ["session-1"]

    with patch("app.agent.nodes.analyze_node.run_rules") as mock_rules:
        mock_result = MagicMock()
        mock_result.id = "rule-job-1"
        mock_rules.apply_async.return_value = mock_result

        result = asyncio.run(graph.ainvoke(state, config={"configurable": {"thread_id": "t-ingest"}}))

    assert result["intent"] == "analyze"
    assert result["current_step"] == "rule_analysis_dispatched"


def test_graph_routes_to_compare() -> None:
    graph = build_graph()
    state = create_initial_state(user_input="对比 v1 和 v2")
    state["target_filters"] = {
        "version_a": "v1",
        "version_b": "v2",
    }

    mock_db = MagicMock()
    with patch("app.agent.nodes.compare_node.compare_versions", new_callable=AsyncMock) as mock_cmp:
        mock_cmp.return_value = {
            "version_a": "v1",
            "version_b": "v2",
            "benchmark": None,
            "sessions_a": 2,
            "sessions_b": 2,
            "accuracy_a": 0.7,
            "accuracy_b": 0.8,
            "accuracy_delta": 0.1,
            "error_rate_a": 0.3,
            "error_rate_b": 0.2,
            "error_rate_delta": -0.1,
        }
        with patch("app.agent.nodes.compare_node.get_version_diff", new_callable=AsyncMock) as mock_diff:
            mock_diff.return_value = {
                "regressed": [],
                "improved": [],
                "new_errors": [],
                "fixed_errors": [],
            }
            result = asyncio.run(
                graph.ainvoke(state, config={"configurable": {"thread_id": "t-query", "db": mock_db}})
            )

    assert result["intent"] == "compare"
    assert result["current_step"] == "compare_done"
