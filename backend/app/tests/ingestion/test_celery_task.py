import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from app.tasks.ingest import parse_file


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
