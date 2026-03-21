"""Analyze subgraph node — dispatches rule analysis task."""
from __future__ import annotations

from typing import Any

from app.agent.state import OrchestratorState
from app.tasks.analysis import run_rules


def analyze_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """Dispatch rule analysis for the target session."""
    session_ids = state.get("target_session_ids", [])
    if not session_ids:
        return {
            "errors": ["Analyze failed: no target_session_ids specified"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "请先选择要分析的评测批次。"}
            ],
        }

    session_id = session_ids[0]
    result = run_rules.apply_async(kwargs={"session_id": session_id, "rule_ids": None})

    return {
        "rule_job_id": result.id,
        "current_step": "rule_analysis_dispatched",
        "conversation_history": [
            {
                "role": "assistant",
                "content": f"已开始规则分析（任务ID: {result.id}）。",
            }
        ],
    }
