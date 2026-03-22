"""Tests for intent classification from user input."""
import pytest

from app.agent.intent_router import classify_intent


@pytest.mark.parametrize(
    "user_input,expected_intent",
    [
        ("上传文件 mmlu_results.jsonl", "ingest"),
        ("导入这个评测数据", "ingest"),
        ("upload this file", "ingest"),
        ("解析 /data/results/ 目录", "ingest"),
        ("分析一下这批数据的错因", "analyze"),
        ("帮我看看错题原因", "analyze"),
        ("run error analysis", "analyze"),
        ("触发 LLM 分析", "analyze"),
        ("规则分析 session abc", "analyze"),
        ("对比 v1 和 v2", "compare"),
        ("版本对比", "compare"),
        ("compare v2.0 with v2.1", "compare"),
        ("v1 vs v2 有什么变化", "compare"),
        ("查看错误分布", "query"),
        ("展示 mmlu 的分析结果", "query"),
        ("show me the error summary", "query"),
        ("错误率趋势", "query"),
        ("跨 benchmark 分析", "query"),
        ("生成报告", "report"),
        ("generate a report", "report"),
        ("导出分析报告", "report"),
    ],
)
def test_classify_intent(user_input: str, expected_intent: str) -> None:
    intent = classify_intent(user_input)
    assert intent == expected_intent


def test_classify_intent_unknown_defaults_to_query() -> None:
    assert classify_intent("你好") == "query"


def test_classify_intent_empty_string() -> None:
    assert classify_intent("") == "query"
