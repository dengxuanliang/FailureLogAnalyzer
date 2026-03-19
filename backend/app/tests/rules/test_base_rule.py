import pytest
from app.rules.base import BaseRule, RuleResult, RuleContext


def test_rule_result_has_tag_and_confidence():
    r = RuleResult(tag_path="格式与规范错误.空回答/拒绝回答", confidence=0.95)
    assert r.tag_path == "格式与规范错误.空回答/拒绝回答"
    assert r.confidence == 0.95


def test_base_rule_is_abstract():
    with pytest.raises(TypeError):
        BaseRule()  # Cannot instantiate abstract class


def test_rule_context_fields():
    ctx = RuleContext(
        record_id="uuid-1",
        model_answer="hello",
        expected_answer="world",
        question="What?",
        extracted_code=None,
        metadata={},
    )
    assert ctx.model_answer == "hello"
