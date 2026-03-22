"""Query subgraph node — calls analysis query services."""
from __future__ import annotations

from typing import Any

from app.agent.state import OrchestratorState
from app.services.analysis_query import get_analysis_summary, get_error_distribution


async def query_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """Run query action and return a formatted assistant message."""
    filters = state.get("target_filters", {})
    query_type = filters.get("query_type", "summary")
    benchmark = filters.get("benchmark")
    model_version = filters.get("model_version")
    db = config.get("configurable", {}).get("db")
    if db is None:
        return {
            "errors": ["Query failed: db session is required in config.configurable.db"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "查询失败：服务暂时不可用，请稍后重试。"}
            ],
        }

    if query_type == "distribution":
        group_by = filters.get("group_by", "error_type")
        try:
            result = await get_error_distribution(
                db=db,
                group_by=group_by,
                benchmark=benchmark,
                model_version=model_version,
            )
        except ValueError as exc:
            return {
                "errors": [f"Query failed: {exc}"],
                "current_step": "error",
                "conversation_history": [
                    {"role": "assistant", "content": f"查询参数错误：{exc}"}
                ],
            }
        if result:
            lines = [f"错误分布 (按 {group_by}):"]
            for item in result[:10]:
                lines.append(
                    f"  - {item['label']}: {item['count']} ({item['percentage']:.1f}%)"
                )
            content = "\n".join(lines)
        else:
            content = "当前没有错误分布数据。"
    else:
        result = await get_analysis_summary(
            db=db,
            benchmark=benchmark,
            model_version=model_version,
            time_range_start=None,
            time_range_end=None,
        )
        content = (
            "分析概览:\n"
            f"- 评测批次: {result['total_sessions']}\n"
            f"- 总记录数: {result['total_records']}\n"
            f"- 错题数: {result['total_errors']}\n"
            f"- 准确率: {result['accuracy']:.1%}\n"
            f"- LLM 已分析: {result['llm_analysed_count']}\n"
            f"- LLM 总成本: ${result['llm_total_cost']:.4f}"
        )

    return {
        "current_step": "query_done",
        "conversation_history": [{"role": "assistant", "content": content}],
    }
