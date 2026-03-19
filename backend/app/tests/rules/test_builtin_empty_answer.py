import pytest
from app.rules.builtin.empty_answer import EmptyAnswerRule
from app.rules.base import RuleContext


@pytest.fixture
def rule():
    return EmptyAnswerRule()


def _ctx(answer: str) -> RuleContext:
    return RuleContext(
        record_id="r1", model_answer=answer, expected_answer="x",
        question="q", extracted_code=None, metadata={},
    )


def test_empty_string_fires(rule):
    results = rule.evaluate(_ctx(""))
    assert len(results) == 1
    assert results[0].tag_path == "格式与规范错误.空回答/拒绝回答"


def test_whitespace_only_fires(rule):
    assert len(rule.evaluate(_ctx("   \n\t"))) == 1


def test_normal_answer_silent(rule):
    assert rule.evaluate(_ctx("42")) == []
