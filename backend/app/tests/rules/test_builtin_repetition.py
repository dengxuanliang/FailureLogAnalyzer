import pytest
from app.rules.builtin.repetition import RepetitionRule
from app.rules.base import RuleContext


@pytest.fixture
def rule():
    return RepetitionRule()


def _ctx(answer: str) -> RuleContext:
    return RuleContext(
        record_id="r1", model_answer=answer, expected_answer="",
        question="q", extracted_code=None, metadata={},
    )


def test_highly_repetitive_answer_fires(rule):
    # "abc " repeated 50 times → very high bigram repetition rate
    answer = "abc def " * 50
    results = rule.evaluate(_ctx(answer))
    assert len(results) == 1
    assert results[0].tag_path == "生成质量问题.重复生成"


def test_normal_answer_silent(rule):
    answer = "The quick brown fox jumps over the lazy dog. Python is a programming language."
    assert rule.evaluate(_ctx(answer)) == []


def test_short_answer_skipped(rule):
    assert rule.evaluate(_ctx("yes")) == []
