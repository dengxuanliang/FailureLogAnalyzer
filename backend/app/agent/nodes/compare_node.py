"""Compare subgraph node — calls version comparison services."""
from __future__ import annotations

from typing import Any

from app.agent.state import OrchestratorState
from app.services.compare import compare_versions, get_version_diff


def compare_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
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
    benchmark = filters.get("benchmark")
    comparison = compare_versions(db, version_a, version_b, benchmark)
    diff = get_version_diff(db, version_a, version_b, benchmark)

    metrics_a = comparison.get("metrics_a", {})
    metrics_b = comparison.get("metrics_b", {})

    summary = (
        f"版本对比结果 ({version_a} vs {version_b}):\n"
        f"- {version_a}: 准确率 {metrics_a.get('accuracy', 0):.1%}, "
        f"{metrics_a.get('errors', 0)} 道错题\n"
        f"- {version_b}: 准确率 {metrics_b.get('accuracy', 0):.1%}, "
        f"{metrics_b.get('errors', 0)} 道错题\n"
        f"- 退化: {len(diff.get('regressed', []))} 题, "
        f"进步: {len(diff.get('improved', []))} 题"
    )

    return {
        "current_step": "compare_done",
        "conversation_history": [{"role": "assistant", "content": summary}],
    }
