"""Tests for report and human review nodes."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.nodes.human_review_node import human_review_node
from app.agent.nodes.report_node import report_node
from app.agent.state import create_initial_state


async def _run_report(state: dict, config: dict) -> dict:
    return await report_node(state, config)


def test_report_node_dispatches_generate_report() -> None:
    state = create_initial_state(user_input="生成报告")
    state["target_filters"] = {"benchmark": "mmlu", "report_type": "summary"}

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    expected_id = uuid.uuid4()

    async def _refresh(report_obj):
        report_obj.id = expected_id

    mock_db.refresh.side_effect = _refresh

    with patch("app.agent.nodes.report_node.generate_report") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "report-task-1"
        mock_task.apply_async.return_value = mock_result

        updates = asyncio.run(_run_report(state, config={"configurable": {"db": mock_db}}))

    assert updates["current_step"] == "report_dispatched"
    assert updates["report_status"] == "pending"
    assert updates["report_id"] == str(expected_id)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited()
    mock_db.refresh.assert_awaited()
    mock_task.apply_async.assert_called_once()


def test_report_node_requires_benchmark_or_sessions() -> None:
    state = create_initial_state(user_input="生成报告")
    state["target_filters"] = {}

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    updates = asyncio.run(_run_report(state, config={"configurable": {"db": mock_db}}))

    assert updates["current_step"] == "error"
    assert len(updates["errors"]) > 0


def test_report_node_errors_without_db() -> None:
    state = create_initial_state(user_input="生成报告")
    state["target_filters"] = {"benchmark": "mmlu"}

    updates = asyncio.run(_run_report(state, config={}))

    assert updates["current_step"] == "error"
    assert "db session" in updates["errors"][0].lower()


def test_human_review_node_resets_flag() -> None:
    state = create_initial_state()
    state["needs_human_input"] = True

    updates = human_review_node(state, config={})

    assert updates["needs_human_input"] is False
    assert updates["current_step"] == "human_review_done"
