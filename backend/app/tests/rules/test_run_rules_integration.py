"""Integration test for run_rules Celery task with a real (test) DB session."""
import pytest
import uuid


@pytest.mark.integration
def test_run_rules_writes_analysis_result_and_tags(db_session):
    """Full round-trip: insert a record, run rules, verify DB writes."""
    from app.tasks.analysis import _run_rules_for_session_async
    from app.db.models.eval_record import EvalRecord
    from app.db.models.analysis_result import AnalysisResult
    from app.db.models.error_tag import ErrorTag

    session_id = str(uuid.uuid4())
    record = EvalRecord(
        session_id=session_id,
        benchmark="test",
        model_answer="",
        expected_answer="42",
        question="What is 6×7?",
        is_correct=False,
        score=0.0,
        metadata_={},
        raw_json={},
    )
    db_session.add(record)
    db_session.commit()

    import asyncio
    asyncio.run(_run_rules_for_session_async(session_id=session_id, rule_ids=None))
