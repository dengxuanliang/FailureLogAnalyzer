"""Compare subgraph node — calls version comparison services."""
from __future__ import annotations

from typing import Any

from app.agent.state import OrchestratorState
from app.services.compare import compare_versions, get_version_diff


async def compare_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """Run version comparison and summarize response."""
    filters = state.get("target_filters", {})
    version_a = filters.get("version_a")
    version_b = filters.get("version_b")

    if not version_a or not version_b:
        return {
            "errors": [
                "Compare failed: version_a and version_b required in target_filters"
            ],
            "current_step": "error",
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": "请指定要对比的两个模型版本（如 v1 和 v2）。",
                }
                ],
            }

    db = config.get("configurable", {}).get("db")
    if db is None:
        return {
            "errors": ["Compare failed: db session is required in config.configurable.db"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "对比失败：服务暂时不可用，请稍后重试。"}
            ],
        }
    benchmark = filters.get("benchmark")
    comparison = await compare_versions(db, version_a, version_b, benchmark)
    diff = await get_version_diff(db, version_a, version_b, benchmark)

    summary = (
        f"版本对比结果 ({version_a} vs {version_b}):\n"
        f"- {version_a}: 准确率 {comparison.get('accuracy_a', 0):.1%}, "
        f"错误率 {comparison.get('error_rate_a', 0):.1%}\n"
        f"- {version_b}: 准确率 {comparison.get('accuracy_b', 0):.1%}, "
        f"错误率 {comparison.get('error_rate_b', 0):.1%}\n"
        f"- 准确率变化: {comparison.get('accuracy_delta', 0):+.1%}, "
        f"错误率变化: {comparison.get('error_rate_delta', 0):+.1%}\n"
        f"- 退化: {len(diff.get('regressed', []))} 题, "
        f"进步: {len(diff.get('improved', []))} 题"
    )

    return {
        "current_step": "compare_done",
        "conversation_history": [{"role": "assistant", "content": summary}],
    }
