import orjson
import pytest
from unittest.mock import AsyncMock

from app.ingestion.job_store import create_job, get_job_status, update_job_from_event


@pytest.mark.asyncio
async def test_update_job_from_event_merges_allowed_fields_and_preserves_existing_payload():
    redis = AsyncMock()
    redis.get.return_value = orjson.dumps(
        {
            "job_id": "job-1",
            "session_id": "session-1",
            "file_path": "/tmp/a.jsonl",
            "status": "pending",
            "processed": 0,
            "total": None,
            "total_written": 0,
            "total_skipped": 0,
            "created_at": 123.0,
        }
    )

    await update_job_from_event(
        redis,
        "job-1",
        {
            "status": "running",
            "processed": 50,
            "total": 100,
            "total_written": 20,
            "total_skipped": 5,
            "reason": "ignored if not failed",
            "unknown_field": "must-not-be-stored",
        },
    )

    redis.set.assert_awaited_once()
    key, payload = redis.set.await_args.args[:2]
    assert key == "ingest_job:job-1"
    decoded = orjson.loads(payload)
    assert decoded["status"] == "running"
    assert decoded["processed"] == 50
    assert decoded["total"] == 100
    assert decoded["total_written"] == 20
    assert decoded["total_skipped"] == 5
    assert decoded["session_id"] == "session-1"
    assert "unknown_field" not in decoded


@pytest.mark.asyncio
async def test_get_job_status_returns_none_for_non_json_payload():
    redis = AsyncMock()
    redis.get.return_value = b"not-json"

    status = await get_job_status(redis, "job-corrupt")

    assert status is None


@pytest.mark.asyncio
async def test_create_job_initializes_pending_status():
    redis = AsyncMock()

    await create_job(
        redis,
        job_id="job-2",
        session_id="session-2",
        file_path="/tmp/b.jsonl",
    )

    redis.set.assert_awaited_once()
    payload = redis.set.await_args.args[1]
    decoded = orjson.loads(payload)
    assert decoded["status"] == "pending"
    assert decoded["job_id"] == "job-2"
