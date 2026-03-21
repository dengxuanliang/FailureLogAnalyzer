"""Tests for report and human review nodes."""
from unittest.mock import MagicMock, patch

from app.agent.nodes.human_review_node import human_review_node
from app.agent.nodes.report_node import report_node
from app.agent.state import create_initial_state


def test_report_node_dispatches_generate_report() -> None:
    state = create_initial_state(user_input="生成报告")
    state["target_filters"] = {"benchmark": "mmlu", "report_type": "summary"}

    with patch("app.agent.nodes.report_node.generate_report") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "report-task-1"
        mock_task.apply_async.return_value = mock_result

        updates = report_node(state, config={})

    assert updates["current_step"] == "report_dispatched"
    assert updates["report_status"] == "pending"
    assert "report_id" in updates


def test_report_node_requires_benchmark_or_sessions() -> None:
    state = create_initial_state(user_input="生成报告")
    state["target_filters"] = {}

    updates = report_node(state, config={})

    assert updates["current_step"] == "error"
    assert len(updates["errors"]) > 0


def test_human_review_node_resets_flag() -> None:
    state = create_initial_state()
    state["needs_human_input"] = True

    updates = human_review_node(state, config={})

    assert updates["needs_human_input"] is False
    assert updates["current_step"] == "human_review_done"
