"""Tests for the query subgraph node."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.nodes.query_node import query_node
from app.agent.state import create_initial_state


async def _run_query(state: dict, config: dict) -> dict:
    return await query_node(state, config)


def test_query_node_returns_summary() -> None:
    state = create_initial_state(user_input="查看分析概览")
    state["target_filters"] = {"query_type": "summary"}

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.query_node.get_analysis_summary", new_callable=AsyncMock) as mock_summary:
        mock_summary.return_value = {
            "total_sessions": 5,
            "total_records": 1000,
            "total_errors": 300,
            "accuracy": 0.7,
            "llm_analysed_count": 50,
            "llm_total_cost": 1.23,
        }
        updates = asyncio.run(_run_query(state, config))

    assert updates["current_step"] == "query_done"
    assert any(m["role"] == "assistant" for m in updates["conversation_history"])
    mock_summary.assert_awaited_once()


def test_query_node_returns_distribution() -> None:
    state = create_initial_state(user_input="错误分布")
    state["target_filters"] = {"query_type": "distribution", "group_by": "error_type"}

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.query_node.get_error_distribution", new_callable=AsyncMock) as mock_dist:
        mock_dist.return_value = [
            {"label": "推理性错误", "count": 100, "percentage": 33.3},
            {"label": "知识性错误", "count": 80, "percentage": 26.7},
        ]
        updates = asyncio.run(_run_query(state, config))

    assert updates["current_step"] == "query_done"
    mock_dist.assert_awaited_once()


def test_query_node_defaults_to_summary() -> None:
    state = create_initial_state(user_input="查看结果")
    state["target_filters"] = {}

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.query_node.get_analysis_summary", new_callable=AsyncMock) as mock_summary:
        mock_summary.return_value = {
            "total_sessions": 0,
            "total_records": 0,
            "total_errors": 0,
            "accuracy": 0.0,
            "llm_analysed_count": 0,
            "llm_total_cost": 0.0,
        }
        updates = asyncio.run(_run_query(state, config))

    assert updates["current_step"] == "query_done"


def test_query_node_does_not_mutate_input_state() -> None:
    state = create_initial_state(user_input="查看结果")
    state["target_filters"] = {}
    original_step = state["current_step"]

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.query_node.get_analysis_summary", new_callable=AsyncMock) as mock_summary:
        mock_summary.return_value = {
            "total_sessions": 0,
            "total_records": 0,
            "total_errors": 0,
            "accuracy": 0.0,
            "llm_analysed_count": 0,
            "llm_total_cost": 0.0,
        }
        asyncio.run(_run_query(state, config))

    assert state["current_step"] == original_step
