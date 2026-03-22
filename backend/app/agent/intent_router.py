"""Rule-based intent classification for user input."""
from __future__ import annotations

import re

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "ingest",
        [
            r"上传",
            r"导入",
            r"upload",
            r"import",
            r"解析",
            r"ingest",
            r"文件",
            r"file",
            r"目录",
            r"directory",
            r"parse",
        ],
    ),
    (
        "analyze",
        [
            r"分析.*错",
            r"错因",
            r"错题",
            r"analyze",
            r"analysis",
            r"规则分析",
            r"rule",
            r"llm.*分析",
            r"触发.*分析",
            r"trigger.*analy",
        ],
    ),
    (
        "compare",
        [
            r"对比",
            r"比较",
            r"compare",
            r"\bvs\b",
            r"diff",
            r"版本.*对比",
            r"version.*compar",
            r"变化",
        ],
    ),
    (
        "report",
        [
            r"报告",
            r"report",
            r"导出",
            r"export",
            r"生成.*报告",
            r"generate.*report",
        ],
    ),
    (
        "query",
        [
            r"查看",
            r"展示",
            r"show",
            r"display",
            r"分布",
            r"distribution",
            r"趋势",
            r"trend",
            r"统计",
            r"summary",
            r"概览",
            r"overview",
            r"跨.*benchmark",
            r"cross.?bench",
        ],
    ),
]

_COMPILED: list[tuple[str, list[re.Pattern[str]]]] = [
    (intent, [re.compile(pattern, re.IGNORECASE) for pattern in patterns])
    for intent, patterns in _INTENT_PATTERNS
]


_VALID_INTENTS = {"ingest", "analyze", "compare", "query", "report"}


def classify_intent(user_input: str) -> str:
    """Classify user input into one of orchestrator intents."""
    normalized = user_input.strip()
    if not normalized:
        return "query"

    scores: dict[str, int] = {}
    for intent, patterns in _COMPILED:
        score = sum(1 for pattern in patterns if pattern.search(normalized))
        if score > 0:
            scores[intent] = score

    if not scores:
        return "query"

    winner = max(scores, key=scores.get)
    if winner not in _VALID_INTENTS:
        return "query"
    return winner
