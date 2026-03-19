import pytest
from app.rules.builtin.exact_match import ExactMatchRule
from app.rules.base import RuleContext


@pytest.fixture
def rule():
    return ExactMatchRule()


def _ctx(expected: str, answer: str) -> RuleContext:
    return RuleContext(
        record_id="r1", model_answer=answer, expected_answer=expected,
        question="q", extracted_code=None, metadata={},
    )


def test_exact_match_emits_tag(rule):
    results = rule.evaluate(_ctx("Paris", "Paris"))
    assert any("精确匹配" in r.tag_path for r in results)


def test_case_insensitive_match(rule):
    results = rule.evaluate(_ctx("paris", "Paris"))
    assert any("大小写匹配" in r.tag_path for r in results)


def test_no_match_silent(rule):
    assert rule.evaluate(_ctx("Paris", "London")) == []
