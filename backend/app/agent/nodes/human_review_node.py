"""Human-in-the-loop resume node."""
from __future__ import annotations

from typing import Any

from app.agent.state import OrchestratorState


def human_review_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """Mark human review complete after LangGraph resume."""
    _ = (state, config)
    return {
        "needs_human_input": False,
        "current_step": "human_review_done",
        "conversation_history": [
            {"role": "assistant", "content": "人工审核已完成，分析流程继续。"}
        ],
    }
