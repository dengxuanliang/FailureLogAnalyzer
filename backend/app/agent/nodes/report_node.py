"""Report subgraph node — dispatches generate_report Celery task."""
from __future__ import annotations

import uuid
from typing import Any

from app.agent.state import OrchestratorState
from app.tasks.report import generate_report


def report_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """Dispatch report generation task and return partial updates."""
    _ = config
    filters = state.get("target_filters", {})
    report_type = filters.get("report_type", "summary")

    if not filters.get("benchmark") and not state.get("target_session_ids"):
        return {
            "errors": ["Report failed: specify benchmark or session_ids"],
            "current_step": "error",
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": "请指定要生成报告的 benchmark 或评测批次。",
                }
            ],
        }

    report_id = str(uuid.uuid4())
    report_config = {
        "title": filters.get("title", f"Agent-generated {report_type} report"),
        "benchmark": filters.get("benchmark"),
        "model_version": filters.get("model_version"),
        "session_ids": state.get("target_session_ids"),
    }
    if report_type == "comparison":
        report_config["version_a"] = filters.get("version_a")
        report_config["version_b"] = filters.get("version_b")

    generate_report.apply_async(
        kwargs={
            "report_id": report_id,
            "report_type": report_type,
            "config": report_config,
        }
    )

    return {
        "report_id": report_id,
        "report_status": "pending",
        "current_step": "report_dispatched",
        "conversation_history": [
            {
                "role": "assistant",
                "content": f"正在生成{report_type}报告（ID: {report_id}）...",
            }
        ],
    }
