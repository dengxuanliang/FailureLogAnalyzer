import pytest
from app.rules.builtin.length_anomaly import LengthAnomalyRule
from app.rules.base import RuleContext


@pytest.fixture
def rule():
    return LengthAnomalyRule()


def _ctx(answer: str, avg: float) -> RuleContext:
    return RuleContext(
        record_id="r1", model_answer=answer, expected_answer="",
        question="q", extracted_code=None, metadata={},
        session_avg_length=avg,
    )


def test_very_short_answer_fires_incomplete(rule):
    # answer length 5, avg 200 → ratio 0.025 < threshold 0.1
    results = rule.evaluate(_ctx("short", 200.0))
    assert any("不完整回答" in r.tag_path for r in results)


def test_very_long_answer_fires_repetition(rule):
    # answer length 2000, avg 50 → ratio 40 > threshold 5
    results = rule.evaluate(_ctx("x " * 1000, 50.0))
    assert any("重复生成" in r.tag_path for r in results)


def test_normal_length_silent(rule):
    assert rule.evaluate(_ctx("hello world", 10.0)) == []


def test_no_avg_length_silent(rule):
    ctx = RuleContext(
        record_id="r1", model_answer="hello", expected_answer="",
        question="q", extracted_code=None, metadata={},
    )
    assert rule.evaluate(ctx) == []
