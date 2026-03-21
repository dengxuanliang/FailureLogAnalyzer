"""Report subgraph node — dispatches generate_report Celery task."""
from __future__ import annotations

import uuid
from typing import Any

from app.agent.state import OrchestratorState
from app.db.models.enums import ReportStatus, ReportType
from app.db.models.report import Report
from app.tasks.report import generate_report


def _parse_session_ids(raw_session_ids: list[str] | None) -> tuple[list[uuid.UUID], list[str]]:
    if not raw_session_ids:
        return [], []

    parsed: list[uuid.UUID] = []
    invalid: list[str] = []
    for sid in raw_session_ids:
        try:
            parsed.append(uuid.UUID(str(sid)))
        except (TypeError, ValueError):
            invalid.append(str(sid))
    return parsed, invalid


async def report_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """Dispatch report generation task and return partial updates."""
    filters = state.get("target_filters", {})
    report_type_value = filters.get("report_type", "summary")
    try:
        report_type = ReportType(str(report_type_value))
    except ValueError:
        return {
            "errors": [f"Report failed: unsupported report_type={report_type_value}"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "报告类型不支持，请使用 summary/comparison/cross_benchmark/custom。"}
            ],
        }

    parsed_session_ids, invalid_session_ids = _parse_session_ids(state.get("target_session_ids"))
    if invalid_session_ids:
        return {
            "errors": [f"Report failed: invalid session_ids={invalid_session_ids}"],
            "current_step": "error",
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": "报告失败：存在无效的评测批次 ID，请检查后重试。",
                }
            ],
        }

    if (
        report_type != ReportType.cross_benchmark
        and not filters.get("benchmark")
        and not parsed_session_ids
    ):
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

    if report_type == ReportType.comparison and (
        not filters.get("version_a") or not filters.get("version_b")
    ):
        return {
            "errors": ["Report failed: comparison report requires version_a and version_b"],
            "current_step": "error",
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": "生成对比报告时请同时提供 version_a 和 version_b。",
                }
            ],
        }

    db = config.get("configurable", {}).get("db")
    if db is None:
        return {
            "errors": ["Report failed: db session is required in config.configurable.db"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "报告失败：服务暂时不可用，请稍后重试。"}
            ],
        }

    report_config = {
        "title": filters.get("title", f"Agent-generated {report_type.value} report"),
        "benchmark": filters.get("benchmark"),
        "model_version": filters.get("model_version"),
        "session_ids": [str(sid) for sid in parsed_session_ids] or None,
        "time_range_start": filters.get("time_range_start"),
        "time_range_end": filters.get("time_range_end"),
    }
    if report_type == ReportType.comparison:
        report_config["version_a"] = filters.get("version_a")
        report_config["version_b"] = filters.get("version_b")

    report = Report(
        title=report_config["title"],
        report_type=report_type,
        benchmark=filters.get("benchmark"),
        model_version=filters.get("model_version"),
        session_ids=parsed_session_ids or None,
        time_range_start=filters.get("time_range_start"),
        time_range_end=filters.get("time_range_end"),
        status=ReportStatus.pending,
        created_by="agent",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    report_id = str(report.id)
    generate_report.apply_async(
        kwargs={
            "report_id": report_id,
            "report_type": report_type.value,
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
