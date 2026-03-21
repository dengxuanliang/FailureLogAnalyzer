"""Ingest subgraph node — dispatches parse_file Celery task."""
from __future__ import annotations

import uuid
from typing import Any

from app.agent.state import OrchestratorState
from app.tasks.ingest import parse_file


def ingest_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """Dispatch parse_file task and return partial state updates."""
    filters = state.get("target_filters", {})
    file_path = filters.get("file_path")

    if not file_path:
        return {
            "errors": ["Ingest failed: no file_path specified in target_filters"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "请指定要导入的文件路径。"}
            ],
        }

    adapter_name = filters.get("adapter")
    session_id = (state.get("target_session_ids") or [None])[0] or str(uuid.uuid4())
    benchmark = filters.get("benchmark", "unknown")
    model = filters.get("model", "unknown")
    model_version = filters.get("model_version", "unknown")
    job_id = str(uuid.uuid4())

    result = parse_file.apply_async(
        kwargs={
            "file_path": file_path,
            "adapter_name": adapter_name,
            "job_id": job_id,
            "session_id": session_id,
            "benchmark": benchmark,
            "model": model,
            "model_version": model_version,
        }
    )

    return {
        "ingest_job_id": result.id,
        "ingest_status": "pending",
        "current_step": "ingest_dispatched",
        "conversation_history": [
            {
                "role": "assistant",
                "content": f"已开始导入文件 {file_path}（任务ID: {result.id}）。",
            }
        ],
    }
