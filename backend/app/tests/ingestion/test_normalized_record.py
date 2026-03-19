import pytest
from pydantic import ValidationError
from app.ingestion.schemas import NormalizedRecord

def test_required_fields_present():
    r = NormalizedRecord(
        session_id="550e8400-e29b-41d4-a716-446655440000",
        benchmark="mmlu",
        model="model-v1",
        model_version="v1",
        question_id="q_001",
        question="What is 2+2?",
        expected_answer="4",
        model_answer="4",
        is_correct=True,
    )
    assert r.score == 0.0  # default
    assert r.metadata == {}
    assert r.raw_json == {}

def test_is_correct_required():
    with pytest.raises(ValidationError):
        NormalizedRecord(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            benchmark="mmlu",
            model="model-v1",
            model_version="v1",
            question_id="q_001",
            question="What is 2+2?",
            expected_answer="4",
            model_answer="4",
            # is_correct missing
        )

def test_sha256_computed_from_session_and_question_id():
    r = NormalizedRecord(
        session_id="550e8400-e29b-41d4-a716-446655440000",
        benchmark="mmlu",
        model="model-v1",
        model_version="v1",
        question_id="q_001",
        question="x",
        expected_answer="y",
        model_answer="z",
        is_correct=False,
    )
    import hashlib
    expected = hashlib.sha256(
        b"550e8400-e29b-41d4-a716-446655440000:q_001"
    ).hexdigest()
    assert r.dedup_hash == expected
