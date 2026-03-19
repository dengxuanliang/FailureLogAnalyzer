import pytest
from app.rules.builtin.extraction_mismatch import ExtractionMismatchRule
from app.rules.base import RuleContext


@pytest.fixture
def rule():
    return ExtractionMismatchRule()


def _ctx(extracted: str, answer: str) -> RuleContext:
    return RuleContext(
        record_id="r1", model_answer=answer, expected_answer="",
        question="q", extracted_code=extracted, metadata={},
    )


def test_extracted_not_substring_fires(rule):
    results = rule.evaluate(_ctx(
        extracted="def bar(): pass",
        answer="def foo(): return 42\n\nThe function above solves the problem.",
    ))
    assert len(results) == 1
    assert results[0].tag_path == "解析类错误.答案提取错误"


def test_extracted_is_substring_silent(rule):
    answer = "Here is the code:\ndef foo(): return 42"
    assert rule.evaluate(_ctx("def foo(): return 42", answer)) == []


def test_both_empty_silent(rule):
    assert rule.evaluate(_ctx("", "")) == []
