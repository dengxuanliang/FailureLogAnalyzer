import pytest
from app.rules.builtin.format_mismatch import FormatMismatchRule
from app.rules.base import RuleContext


@pytest.fixture
def rule():
    return FormatMismatchRule()


def _ctx(question: str, answer: str) -> RuleContext:
    return RuleContext(
        record_id="r1", model_answer=answer, expected_answer="",
        question=question, extracted_code=None, metadata={},
    )


def test_json_required_but_plain_text(rule):
    results = rule.evaluate(_ctx("Reply in JSON.", "Sure, the answer is 42."))
    assert len(results) == 1
    assert results[0].tag_path == "格式与规范错误.输出格式不符"


def test_json_required_and_provided(rule):
    assert rule.evaluate(_ctx("Reply in JSON.", '{"answer": 42}')) == []


def test_no_format_requirement_silent(rule):
    assert rule.evaluate(_ctx("What is 2+2?", "4")) == []


def test_code_block_required_but_missing(rule):
    results = rule.evaluate(_ctx("Return ```python``` code block.", "x = 1"))
    assert len(results) == 1
