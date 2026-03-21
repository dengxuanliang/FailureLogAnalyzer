"""Tests for the analyze subgraph node."""
from unittest.mock import MagicMock, patch

from app.agent.nodes.analyze_node import analyze_node
from app.agent.state import create_initial_state


def test_analyze_node_dispatches_rule_task() -> None:
    state = create_initial_state(user_input="分析错题")
    state["target_session_ids"] = ["session-uuid-1"]

    with patch("app.agent.nodes.analyze_node.run_rules") as mock_rules:
        mock_result = MagicMock()
        mock_result.id = "celery-rule-123"
        mock_rules.apply_async.return_value = mock_result

        updates = analyze_node(state, config={})

    assert updates["rule_job_id"] == "celery-rule-123"
    assert updates["current_step"] == "rule_analysis_dispatched"
    mock_rules.apply_async.assert_called_once()


def test_analyze_node_errors_on_no_session() -> None:
    state = create_initial_state(user_input="分析")
    state["target_session_ids"] = []

    updates = analyze_node(state, config={})

    assert len(updates["errors"]) > 0
    assert updates["current_step"] == "error"


def test_analyze_node_appends_message() -> None:
    state = create_initial_state(user_input="分析错题")
    state["target_session_ids"] = ["session-1"]

    with patch("app.agent.nodes.analyze_node.run_rules") as mock_rules:
        mock_result = MagicMock()
        mock_result.id = "job-789"
        mock_rules.apply_async.return_value = mock_result

        updates = analyze_node(state, config={})

    assert any(m["role"] == "assistant" for m in updates["conversation_history"])


def test_analyze_node_does_not_mutate_input_state() -> None:
    state = create_initial_state(user_input="分析错题")
    state["target_session_ids"] = ["session-1"]
    original_errors = list(state["errors"])

    with patch("app.agent.nodes.analyze_node.run_rules") as mock_rules:
        mock_result = MagicMock()
        mock_result.id = "job-999"
        mock_rules.apply_async.return_value = mock_result

        analyze_node(state, config={})

    assert state["errors"] == original_errors
    assert state["current_step"] == "start"
