"""Tests for the compare subgraph node."""
from unittest.mock import MagicMock, patch

from app.agent.nodes.compare_node import compare_node
from app.agent.state import create_initial_state


def test_compare_node_calls_service() -> None:
    state = create_initial_state(user_input="对比 v1 和 v2")
    state["target_filters"] = {
        "version_a": "v1",
        "version_b": "v2",
        "benchmark": None,
    }

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.compare_node.compare_versions") as mock_cmp:
        mock_cmp.return_value = {
            "version_a": "v1",
            "version_b": "v2",
            "benchmark": None,
            "metrics_a": {"total": 100, "errors": 30, "accuracy": 0.7},
            "metrics_b": {"total": 100, "errors": 20, "accuracy": 0.8},
        }
        with patch("app.agent.nodes.compare_node.get_version_diff") as mock_diff:
            mock_diff.return_value = {
                "regressed": [],
                "improved": [],
                "new_errors": [],
                "resolved_errors": [],
            }
            updates = compare_node(state, config)

    assert updates["current_step"] == "compare_done"
    assert any(m["role"] == "assistant" for m in updates["conversation_history"])


def test_compare_node_errors_on_missing_versions() -> None:
    state = create_initial_state(user_input="对比")
    state["target_filters"] = {}

    config = {"configurable": {"db": MagicMock()}}
    updates = compare_node(state, config)

    assert len(updates["errors"]) > 0
    assert updates["current_step"] == "error"


def test_compare_node_does_not_mutate_input_state() -> None:
    state = create_initial_state(user_input="对比")
    state["target_filters"] = {}
    original_step = state["current_step"]

    config = {"configurable": {"db": MagicMock()}}
    compare_node(state, config)

    assert state["current_step"] == original_step
