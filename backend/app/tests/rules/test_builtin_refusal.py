import pytest
from app.rules.builtin.refusal import RefusalRule
from app.rules.base import RuleContext


@pytest.fixture
def rule():
    return RefusalRule()


def _ctx(answer: str) -> RuleContext:
    return RuleContext(
        record_id="r1", model_answer=answer, expected_answer="",
        question="q", extracted_code=None, metadata={},
    )


def test_sorry_pattern_fires(rule):
    results = rule.evaluate(_ctx("I'm sorry, but I can't help with that."))
    assert len(results) == 1
    assert results[0].tag_path == "生成质量问题.过度对齐"


def test_cannot_assist_fires(rule):
    assert len(rule.evaluate(_ctx("I cannot assist with this request."))) == 1


def test_chinese_refusal_fires(rule):
    assert len(rule.evaluate(_ctx("非常抱歉，我无法回答此类问题。"))) == 1


def test_normal_answer_silent(rule):
    assert rule.evaluate(_ctx("The answer is 42.")) == []
