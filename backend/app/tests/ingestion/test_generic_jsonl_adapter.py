import pytest
from app.ingestion.adapters.generic_jsonl import GenericJsonlAdapter


@pytest.fixture
def adapter():
    return GenericJsonlAdapter()


def test_detect_high_confidence_with_is_correct(adapter):
    line = '{"question": "x", "is_correct": false, "model_answer": "y"}'
    assert adapter.detect(line) >= 0.8


def test_detect_low_confidence_without_is_correct(adapter):
    line = '{"foo": "bar"}'
    assert adapter.detect(line) < 0.5


def test_normalize_minimal_record(adapter):
    raw = {
        "question_id": "q1",
        "question": "What is 2+2?",
        "expected_answer": "4",
        "model_answer": "4",
        "is_correct": True,
    }
    # normalize requires session_id injected externally
    record = adapter.normalize(raw, session_id="sess-1", benchmark="generic", model="m1", model_version="v1")
    assert record is not None
    assert record.is_correct is True
    assert record.question_id == "q1"


def test_normalize_skips_correct_when_errors_only_false(adapter):
    raw = {"question_id": "q1", "question": "x", "expected_answer": "y",
           "model_answer": "z", "is_correct": True}
    record = adapter.normalize(raw, session_id="s", benchmark="g", model="m", model_version="v")
    assert record is not None  # does NOT skip correct records


def test_normalize_captures_extra_fields_in_metadata(adapter):
    raw = {
        "question_id": "q2",
        "question": "q",
        "expected_answer": "a",
        "model_answer": "b",
        "is_correct": False,
        "custom_score": 0.3,
        "difficulty": "hard",
    }
    record = adapter.normalize(raw, session_id="s", benchmark="g", model="m", model_version="v")
    assert record.metadata["difficulty"] == "hard"
    assert record.metadata["custom_score"] == pytest.approx(0.3)
