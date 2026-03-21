from __future__ import annotations

import asyncio
import uuid

import orjson
from celery import shared_task

from app.core.redis import get_redis
from app.db.models.enums import ReportStatus, ReportType
from app.db.models.report import Report
from app.db.session import get_async_session
from app.services.report_builder import build_report

_PROGRESS_CHANNEL_PREFIX = "report_progress"


async def _publish_progress(report_id: str, payload: dict) -> None:
    redis = await get_redis()
    await redis.publish(f"{_PROGRESS_CHANNEL_PREFIX}:{report_id}", orjson.dumps(payload))


async def _generate_report_async(report_id: str, report_type: str, config: dict) -> dict:
    async with get_async_session() as db:
        report_uuid = uuid.UUID(str(report_id))
        report = await db.get(Report, report_uuid)
        if report is None:
            return {"status": "failed", "report_id": report_id, "reason": "report not found"}

        report.status = ReportStatus.generating
        await db.commit()
        await _publish_progress(report_id, {"status": "generating", "report_id": report_id})

        try:
            payload = await build_report(
                db=db,
                report_type=ReportType(report_type),
                config=config,
            )
            report.content = payload
            report.status = ReportStatus.done
            report.error_message = None
            await db.commit()
            await _publish_progress(report_id, {"status": "done", "report_id": report_id})
            return {"status": "done", "report_id": report_id}
        except Exception as exc:  # pragma: no cover - defensive task failure path
            report.status = ReportStatus.failed
            report.error_message = str(exc)
            await db.commit()
            await _publish_progress(
                report_id,
                {"status": "failed", "report_id": report_id, "error": str(exc)},
            )
            return {"status": "failed", "report_id": report_id, "error": str(exc)}


@shared_task(name="tasks.report.generate_report", bind=True, max_retries=3, default_retry_delay=10)
def generate_report(self, report_id: str, report_type: str, config: dict) -> dict:
    try:
        return asyncio.run(_generate_report_async(report_id=report_id, report_type=report_type, config=config))
    except Exception as exc:  # pragma: no cover - Celery retry wrapper
        raise self.retry(exc=exc)
