import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock, call
from app.tasks.ingest import parse_file, _run_parse


@pytest.fixture
def sample_jsonl(tmp_path):
    lines = [
        {"question_id": f"q{i}", "question": f"Q{i}", "expected_answer": "A",
         "model_answer": "B", "is_correct": False}
        for i in range(5)
    ]
    p = tmp_path / "test.jsonl"
    p.write_text("\n".join(json.dumps(l) for l in lines))
    return str(p)


def test_parse_file_task_is_registered():
    from celery import current_app
    # Task must be discoverable
    assert "app.tasks.ingest.parse_file" in parse_file.name or \
           parse_file.name.endswith("parse_file")


def test_parse_file_runs_synchronously(sample_jsonl):
    """Integration smoke test using task's .apply() (no broker needed)."""
    from unittest.mock import patch, AsyncMock, call

    # Mock the DB session and Redis
    mock_writer = MagicMock()
    mock_writer.__aenter__ = AsyncMock(return_value=mock_writer)
    mock_writer.__aexit__ = AsyncMock(return_value=False)
    mock_writer.add = AsyncMock()
    mock_writer.flush = AsyncMock()
    mock_writer.total_written = 5
    mock_writer.total_skipped = 0
    mock_writer.flush_count = 1

    with patch("app.tasks.ingest.BatchWriter", return_value=mock_writer), \
         patch("app.tasks.ingest.get_async_session") as mock_sess, \
         patch("app.tasks.ingest.get_redis") as mock_redis:

        mock_sess.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_sess.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_redis.return_value = AsyncMock()

        result = parse_file.apply(
            args=[sample_jsonl],
            kwargs={
                "adapter_name": "generic_jsonl",
                "job_id": "test-job-1",
                "session_id": "sess-abc",
                "benchmark": "generic",
                "model": "test-model",
                "model_version": "v1",
            }
        )
        assert result.state in ("SUCCESS", "PENDING")


@pytest.mark.asyncio
async def test_run_parse_updates_ingest_metrics_for_write_skip_and_normalize_failure(tmp_path):
    input_file = tmp_path / "input.jsonl"
    input_file.write_text('{"k":"v"}\n')

    parser_records = [{"id": 1}, {"id": 2}, {"id": 3}]

    def fake_parser(_path):
        for item in parser_records:
            yield item

    adapter = MagicMock()
    adapter.normalize.side_effect = [
        {"normalized": 1},
        None,
        ValueError("bad row"),
    ]

    writer = MagicMock()
    writer.__aenter__ = AsyncMock(return_value=writer)
    writer.__aexit__ = AsyncMock(return_value=False)
    writer.add = AsyncMock()
    writer.total_written = 1
    writer.total_skipped = 1

    db_session_ctx = MagicMock()
    db_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
    db_session_ctx.__aexit__ = AsyncMock(return_value=False)

    publisher = AsyncMock()

    with (
        patch("app.tasks.ingest._get_parser", return_value=fake_parser),
        patch("app.tasks.ingest.get_adapter", return_value=adapter),
        patch("app.tasks.ingest.get_async_session", return_value=db_session_ctx),
        patch("app.tasks.ingest.BatchWriter", return_value=writer),
        patch("app.tasks.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())),
        patch("app.tasks.ingest.ProgressPublisher", return_value=publisher),
        patch("app.tasks.ingest.INGEST_RECORDS_TOTAL") as mock_records,
        patch("app.tasks.ingest.INGEST_FAILURES_TOTAL") as mock_failures,
        patch("app.tasks.ingest.INGEST_BYTES_TOTAL") as mock_bytes,
    ):
        result = await _run_parse(
            file_path=str(input_file),
            adapter_name="generic_jsonl",
            job_id="job-1",
            session_id="session-1",
            benchmark="mmlu",
            model="model-x",
            model_version="v1",
        )

    assert result["status"] == "done"
    assert writer.add.await_count == 1
    assert mock_records.labels.call_args_list == [
        call(status="written"),
        call(status="skipped"),
        call(status="normalize_error"),
    ]
    assert mock_failures.inc.call_count == 1
    mock_bytes.labels.assert_called_once_with(benchmark="mmlu")
    mock_bytes.labels.return_value.inc.assert_called_once_with(input_file.stat().st_size)


@pytest.mark.asyncio
async def test_run_parse_marks_failure_metric_on_fatal_error(tmp_path):
    input_file = tmp_path / "fatal.jsonl"
    input_file.write_text('{"k":"v"}\n')

    writer = MagicMock()
    writer.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
    writer.__aexit__ = AsyncMock(return_value=False)

    db_session_ctx = MagicMock()
    db_session_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
    db_session_ctx.__aexit__ = AsyncMock(return_value=False)

    publisher = AsyncMock()
    adapter = MagicMock()
    adapter.normalize.return_value = {"ok": True}

    with (
        patch("app.tasks.ingest._get_parser", return_value=lambda _: iter([{"id": 1}])),
        patch("app.tasks.ingest.get_adapter", return_value=adapter),
        patch("app.tasks.ingest.get_async_session", return_value=db_session_ctx),
        patch("app.tasks.ingest.BatchWriter", return_value=writer),
        patch("app.tasks.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())),
        patch("app.tasks.ingest.ProgressPublisher", return_value=publisher),
        patch("app.tasks.ingest.INGEST_FAILURES_TOTAL") as mock_failures,
    ):
        with pytest.raises(RuntimeError, match="db down"):
            await _run_parse(
                file_path=str(input_file),
                adapter_name="generic_jsonl",
                job_id="job-fail",
                session_id="session-1",
                benchmark="mmlu",
                model="model-x",
                model_version="v1",
            )

    assert mock_failures.inc.call_count >= 1
    publisher.fail.assert_awaited_once()
