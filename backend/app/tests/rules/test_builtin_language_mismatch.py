import pytest
from app.rules.builtin.language_mismatch import LanguageMismatchRule
from app.rules.base import RuleContext


@pytest.fixture
def rule():
    return LanguageMismatchRule()


def _ctx(question: str, answer: str) -> RuleContext:
    return RuleContext(
        record_id="r1", model_answer=answer, expected_answer="",
        question=question, extracted_code=None, metadata={},
    )


def test_chinese_required_english_answer_fires(rule):
    results = rule.evaluate(_ctx("请用中文回答：什么是机器学习？", "Machine learning is a subset of AI."))
    assert len(results) == 1
    assert results[0].tag_path == "格式与规范错误.语言不匹配"


def test_english_question_english_answer_silent(rule):
    results = rule.evaluate(_ctx("What is AI?", "Artificial intelligence is..."))
    assert results == []


def test_short_answer_skipped(rule):
    # Too short to detect reliably
    results = rule.evaluate(_ctx("请用中文回答", "OK"))
    assert results == []
