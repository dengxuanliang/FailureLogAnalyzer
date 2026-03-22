"""Tests for the compare subgraph node."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.nodes.compare_node import compare_node
from app.agent.state import create_initial_state


async def _run_compare(state: dict, config: dict) -> dict:
    return await compare_node(state, config)


def test_compare_node_calls_service() -> None:
    state = create_initial_state(user_input="对比 v1 和 v2")
    state["target_filters"] = {
        "version_a": "v1",
        "version_b": "v2",
        "benchmark": None,
    }

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
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
            updates = asyncio.run(_run_compare(state, config))

    assert updates["current_step"] == "compare_done"
    assert any(m["role"] == "assistant" for m in updates["conversation_history"])
    mock_cmp.assert_awaited_once()
    mock_diff.assert_awaited_once()


def test_compare_node_errors_on_missing_versions() -> None:
    state = create_initial_state(user_input="对比")
    state["target_filters"] = {}

    config = {"configurable": {"db": MagicMock()}}
    updates = asyncio.run(_run_compare(state, config))

    assert len(updates["errors"]) > 0
    assert updates["current_step"] == "error"


def test_compare_node_does_not_mutate_input_state() -> None:
    state = create_initial_state(user_input="对比")
    state["target_filters"] = {}
    original_step = state["current_step"]

    config = {"configurable": {"db": MagicMock()}}
    asyncio.run(_run_compare(state, config))

    assert state["current_step"] == original_step
