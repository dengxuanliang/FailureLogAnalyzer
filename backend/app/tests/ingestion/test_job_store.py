import orjson
import pytest
from unittest.mock import AsyncMock

from app.ingestion.job_store import (
    create_job,
    get_job_status,
    list_jobs,
    update_job_from_event,
)


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


@pytest.mark.asyncio
async def test_list_jobs_filters_by_status_and_session_id_and_sorts_by_created_at():
    redis = AsyncMock()

    async def _scan_iter(_match):
        for key in [b"ingest_job:1", b"ingest_job:2", b"ingest_job:3"]:
            yield key

    jobs = {
        "ingest_job:1": {
            "job_id": "1",
            "session_id": "sess-a",
            "status": "pending",
            "created_at": 10.0,
        },
        "ingest_job:2": {
            "job_id": "2",
            "session_id": "sess-b",
            "status": "done",
            "created_at": 30.0,
        },
        "ingest_job:3": {
            "job_id": "3",
            "session_id": "sess-a",
            "status": "done",
            "created_at": 20.0,
        },
    }

    redis.scan_iter = _scan_iter
    redis.get.side_effect = lambda key: orjson.dumps(jobs[key.decode() if isinstance(key, bytes) else key])

    items, total = await list_jobs(redis, limit=10, offset=0, status="done", session_id="sess-a")

    assert total == 1
    assert [item["job_id"] for item in items] == ["3"]


@pytest.mark.asyncio
async def test_list_jobs_applies_offset_and_limit_after_sorting():
    redis = AsyncMock()

    async def _scan_iter(_match):
        for key in [b"ingest_job:1", b"ingest_job:2", b"ingest_job:3"]:
            yield key

    redis.scan_iter = _scan_iter
    redis.get.side_effect = [
        orjson.dumps({"job_id": "1", "status": "done", "created_at": 10.0}),
        orjson.dumps({"job_id": "2", "status": "done", "created_at": 30.0}),
        orjson.dumps({"job_id": "3", "status": "done", "created_at": 20.0}),
    ]

    items, total = await list_jobs(redis, limit=1, offset=1)

    assert total == 3
    assert len(items) == 1
    assert items[0]["job_id"] == "3"
