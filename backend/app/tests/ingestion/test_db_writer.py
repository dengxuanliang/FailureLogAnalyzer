import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.ingestion.db_writer import BatchWriter, DuplicateSkippedError


@pytest.mark.asyncio
async def test_batch_writer_flushes_at_batch_size():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    writer = BatchWriter(session=mock_session, batch_size=3)

    from app.ingestion.schemas import NormalizedRecord
    records = [
        NormalizedRecord(session_id="s", benchmark="b", model="m",
                         model_version="v", question_id=f"q{i}",
                         question="x", expected_answer="y",
                         model_answer="z", is_correct=False)
        for i in range(3)
    ]
    for r in records:
        await writer.add(r)

    # After 3 records, flush should have been called once
    assert writer.flush_count == 1


@pytest.mark.asyncio
async def test_batch_writer_final_flush():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    writer = BatchWriter(session=mock_session, batch_size=10)
    from app.ingestion.schemas import NormalizedRecord
    r = NormalizedRecord(session_id="s", benchmark="b", model="m",
                         model_version="v", question_id="q1",
                         question="x", expected_answer="y",
                         model_answer="z", is_correct=False)
    await writer.add(r)
    await writer.flush()

    assert writer.flush_count == 1


@pytest.mark.asyncio
async def test_batch_writer_dedup_skips_seen_hash():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    writer = BatchWriter(session=mock_session, batch_size=100)
    from app.ingestion.schemas import NormalizedRecord
    r = NormalizedRecord(session_id="s", benchmark="b", model="m",
                         model_version="v", question_id="q1",
                         question="x", expected_answer="y",
                         model_answer="z", is_correct=False)
    await writer.add(r)
    await writer.add(r)  # exact duplicate

    assert writer.total_written == 1
    assert writer.total_skipped == 1
