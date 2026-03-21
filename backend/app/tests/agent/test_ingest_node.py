"""Tests for the ingest subgraph node."""
from unittest.mock import MagicMock, patch

from app.agent.nodes.ingest_node import ingest_node
from app.agent.state import create_initial_state


def test_ingest_node_dispatches_celery_task() -> None:
    state = create_initial_state(user_input="上传 /data/mmlu.jsonl")
    state["target_filters"] = {"file_path": "/data/mmlu.jsonl", "adapter": "auto"}

    with patch("app.agent.nodes.ingest_node.parse_file") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "celery-ingest-123"
        mock_task.apply_async.return_value = mock_result

        updates = ingest_node(state, config={})

    assert updates["ingest_job_id"] == "celery-ingest-123"
    assert updates["ingest_status"] == "pending"
    assert updates["current_step"] == "ingest_dispatched"
    mock_task.apply_async.assert_called_once()
    assert "intent" not in updates


def test_ingest_node_records_error_on_missing_file_path() -> None:
    state = create_initial_state(user_input="上传文件")
    state["target_filters"] = {}

    updates = ingest_node(state, config={})

    assert len(updates["errors"]) > 0
    assert "file_path" in updates["errors"][0].lower() or "文件" in updates["errors"][0]
    assert updates["current_step"] == "error"


def test_ingest_node_appends_assistant_message() -> None:
    state = create_initial_state(user_input="上传 /data/test.jsonl")
    state["target_filters"] = {"file_path": "/data/test.jsonl"}

    with patch("app.agent.nodes.ingest_node.parse_file") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "job-456"
        mock_task.apply_async.return_value = mock_result

        updates = ingest_node(state, config={})

    assert any(m["role"] == "assistant" for m in updates["conversation_history"])


def test_ingest_node_does_not_mutate_input_state() -> None:
    state = create_initial_state(user_input="上传 /data/test.jsonl")
    state["target_filters"] = {"file_path": "/data/test.jsonl"}
    original_history_len = len(state["conversation_history"])

    with patch("app.agent.nodes.ingest_node.parse_file") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "job-789"
        mock_task.apply_async.return_value = mock_result

        ingest_node(state, config={})

    assert len(state["conversation_history"]) == original_history_len
    assert state["current_step"] == "start"
