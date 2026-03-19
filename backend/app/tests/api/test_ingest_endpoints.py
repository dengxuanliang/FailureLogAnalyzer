import pytest
import io
import json
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_upload_returns_job_id(async_client):
    content = b'{"question_id":"q1","question":"x","expected_answer":"a","model_answer":"b","is_correct":false}\n'

    with patch("app.api.v1.ingest.parse_file") as mock_task, \
         patch("app.api.v1.ingest.save_upload_file", new=AsyncMock(return_value="/tmp/upload/test.jsonl")), \
         patch("app.api.v1.ingest.create_job", new=AsyncMock(return_value=None)), \
         patch("app.api.v1.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())):
        mock_task.delay.return_value = MagicMock(id="celery-task-1")

        resp = await async_client.post(
            "/api/v1/ingest/upload",
            files={"file": ("test.jsonl", io.BytesIO(content), "application/octet-stream")},
            data={
                "benchmark": "generic",
                "model": "test-model",
                "model_version": "v1",
            },
        )

    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert "session_id" in body


@pytest.mark.asyncio
async def test_upload_rejects_non_json_file(async_client):
    content = b"this is not json at all"
    resp = await async_client.post(
        "/api/v1/ingest/upload",
        files={"file": ("data.csv", io.BytesIO(content), "text/csv")},
        data={"benchmark": "generic", "model": "m", "model_version": "v"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_job_status_returns_progress(async_client):
    with patch("app.api.v1.ingest.get_job_status", new=AsyncMock(return_value={
        "job_id": "job-123",
        "status": "running",
        "processed": 500,
        "total": 1000,
    })), \
    patch("app.api.v1.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())):
        resp = await async_client.get("/api/v1/ingest/job-123/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"


@pytest.mark.asyncio
async def test_job_status_404_for_unknown_job(async_client):
    with patch("app.api.v1.ingest.get_job_status", new=AsyncMock(return_value=None)), \
         patch("app.api.v1.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())):
        resp = await async_client.get("/api/v1/ingest/unknown-job/status")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_directory_ingest_queues_multiple_jobs(async_client, tmp_path):
    # Create two jsonl files
    for i in range(2):
        f = tmp_path / f"file{i}.jsonl"
        f.write_text('{"question_id":"q1","question":"x","expected_answer":"a","model_answer":"b","is_correct":false}\n')

    with patch("app.api.v1.ingest.parse_file") as mock_task, \
         patch("app.api.v1.ingest.create_job", new=AsyncMock(return_value=None)), \
         patch("app.api.v1.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())):
        mock_task.delay.return_value = MagicMock(id="celery-task-x")

        resp = await async_client.post(
            "/api/v1/ingest/directory",
            json={
                "directory_path": str(tmp_path),
                "benchmark": "generic",
                "model": "test-model",
                "model_version": "v1",
            },
        )

    assert resp.status_code == 202
    body = resp.json()
    assert len(body["jobs"]) == 2
