import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.enums import ReportStatus


@pytest.mark.asyncio
async def test_generate_report_async_success():
    from app.tasks.report import _generate_report_async

    report_obj = SimpleNamespace(
        id=uuid.uuid4(),
        title="demo",
        report_type="summary",
        status=ReportStatus.pending,
        error_message=None,
        content={},
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=report_obj)

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = db
    session_cm.__aexit__.return_value = False

    redis = AsyncMock()

    with patch("app.tasks.report.get_async_session", return_value=session_cm), \
         patch("app.tasks.report.build_report", autospec=True) as mock_builder, \
         patch("app.tasks.report.get_redis", autospec=True) as mock_redis:
        mock_builder.return_value = {"ok": True}
        mock_redis.return_value = redis

        result = await _generate_report_async(
            report_id=str(report_obj.id),
            report_type="summary",
            config={"title": "demo"},
        )

    assert result["status"] == "done"
    assert report_obj.status == ReportStatus.done
    redis.publish.assert_awaited()


@pytest.mark.asyncio
async def test_generate_report_async_missing_report_returns_failed():
    from app.tasks.report import _generate_report_async

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = db
    session_cm.__aexit__.return_value = False

    with patch("app.tasks.report.get_async_session", return_value=session_cm):
        result = await _generate_report_async(
            report_id=str(uuid.uuid4()),
            report_type="summary",
            config={},
        )

    assert result["status"] == "failed"


def test_generate_report_task_apply_uses_async_runner():
    from app.tasks.report import generate_report

    def _fake_run(coro):
        coro.close()
        return {"status": "done"}

    with patch("app.tasks.report.asyncio.run", autospec=True) as mock_run:
        mock_run.side_effect = _fake_run
        result = generate_report.apply(kwargs={"report_id": str(uuid.uuid4()), "report_type": "summary", "config": {}})

    assert result.state in ("SUCCESS", "PENDING")
