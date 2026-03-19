import pytest
from app.rules.builtin.extracted_field_empty import ExtractedFieldEmptyRule
from app.rules.base import RuleContext


@pytest.fixture
def rule():
    return ExtractedFieldEmptyRule()


def _ctx(extracted: str | None, answer: str) -> RuleContext:
    return RuleContext(
        record_id="r1", model_answer=answer, expected_answer="",
        question="q", extracted_code=extracted, metadata={},
    )


def test_empty_extracted_with_nonempty_answer_fires(rule):
    results = rule.evaluate(_ctx(None, "def foo(): return 1"))
    assert len(results) == 1
    assert results[0].tag_path == "解析类错误.代码提取为空"


def test_empty_extracted_empty_answer_silent(rule):
    assert rule.evaluate(_ctx(None, "")) == []
    assert rule.evaluate(_ctx("", "")) == []


def test_nonempty_extracted_silent(rule):
    assert rule.evaluate(_ctx("def foo(): pass", "def foo(): pass")) == []
