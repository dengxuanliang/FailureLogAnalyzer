import pytest
from unittest.mock import AsyncMock, patch, call
from app.ingestion.progress import ProgressPublisher, ProgressEvent


@pytest.mark.asyncio
async def test_publish_sends_to_redis_channel():
    mock_redis = AsyncMock()
    pub = ProgressPublisher(redis=mock_redis, job_id="job-123")

    await pub.update(processed=500, total=1000, speed_rps=2500.0)

    mock_redis.publish.assert_called_once()
    channel, payload = mock_redis.publish.call_args[0]
    assert channel == "progress:job-123"

    import orjson
    data = orjson.loads(payload)
    assert data["processed"] == 500
    assert data["total"] == 1000
    assert data["percent"] == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_publish_complete_sets_status_done():
    mock_redis = AsyncMock()
    with patch("app.ingestion.progress.update_job_from_event", new=AsyncMock(), create=True) as mock_update_job:
        pub = ProgressPublisher(redis=mock_redis, job_id="job-456")
        await pub.complete(total_written=800, total_skipped=200)

    import orjson
    channel, payload = mock_redis.publish.call_args[0]
    data = orjson.loads(payload)
    assert data["status"] == "done"
    assert data["total_written"] == 800
    mock_update_job.assert_awaited_once_with(
        mock_redis,
        "job-456",
        {
            "status": "done",
            "processed": 1000,
            "total": 1000,
            "total_written": 800,
            "total_skipped": 200,
        },
    )


@pytest.mark.asyncio
async def test_publish_error_sets_status_failed():
    mock_redis = AsyncMock()
    with patch("app.ingestion.progress.update_job_from_event", new=AsyncMock(), create=True) as mock_update_job:
        pub = ProgressPublisher(redis=mock_redis, job_id="job-789")
        await pub.fail(reason="File not found")

    import orjson
    _, payload = mock_redis.publish.call_args[0]
    data = orjson.loads(payload)
    assert data["status"] == "failed"
    assert "File not found" in data["reason"]
    mock_update_job.assert_awaited_once_with(
        mock_redis,
        "job-789",
        {
            "status": "failed",
            "reason": "File not found",
            "processed": 0,
            "total": None,
            "total_written": 0,
            "total_skipped": 0,
        },
    )


@pytest.mark.asyncio
async def test_publish_methods_do_not_fail_when_redis_has_no_key_value_api():
    class PublishOnlyRedis:
        def __init__(self) -> None:
            self.publish = AsyncMock()

    redis = PublishOnlyRedis()
    pub = ProgressPublisher(redis=redis, job_id="job-publish-only")

    await pub.update(processed=1, total=10, speed_rps=2.0)
    await pub.complete(total_written=1, total_skipped=0)
    await pub.fail(reason="boom")

    assert redis.publish.await_count == 3
