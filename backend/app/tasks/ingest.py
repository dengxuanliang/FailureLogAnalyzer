from __future__ import annotations
import logging
import time
from pathlib import Path

from celery import shared_task

from app.ingestion.adapters.registry import get_adapter, auto_detect_adapter
from app.ingestion.db_writer import BatchWriter
from app.ingestion.parsers import parse_jsonl, parse_large_json
from app.ingestion.progress import ProgressPublisher
from app.ingestion.session_store import ensure_eval_session
from app.db.session import get_async_session
from app.core.redis import get_redis
from app.core.metrics import (
    INGEST_BYTES_TOTAL,
    INGEST_FAILURES_TOTAL,
    INGEST_RECORDS_TOTAL,
)
from app.tasks.async_runner import run_async_in_worker

logger = logging.getLogger(__name__)

_PROGRESS_EVERY_N = 500  # publish progress every N records


def _get_parser(file_path: str):
    """Choose parser based on file extension."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".jsonl":
        return parse_jsonl
    elif suffix == ".json":
        return parse_large_json
    else:
        # Try JSONL first (most common), fall back to large JSON
        return parse_jsonl


async def _run_parse(
    file_path: str,
    adapter_name: str | None,
    job_id: str,
    session_id: str,
    benchmark: str,
    model: str,
    model_version: str,
) -> dict:
    # Resolve adapter
    if adapter_name:
        adapter = get_adapter(adapter_name)
        if adapter is None:
            raise ValueError(f"Unknown adapter: {adapter_name!r}")
    else:
        adapter = auto_detect_adapter(file_path)
        if adapter is None:
            raise ValueError(
                f"Could not auto-detect adapter for {file_path}. "
                "Specify adapter_name explicitly."
            )

    parser = _get_parser(file_path)
    redis = await get_redis()
    publisher = ProgressPublisher(redis=redis, job_id=job_id)
    try:
        file_size = Path(file_path).stat().st_size
    except OSError:
        file_size = 0
    INGEST_BYTES_TOTAL.labels(benchmark=benchmark).inc(file_size)

    processed = 0
    start_time = time.monotonic()

    try:
        async with get_async_session() as db_session:
            await ensure_eval_session(
                session=db_session,
                session_id=session_id,
                benchmark=benchmark,
                model=model,
                model_version=model_version,
            )
            async with BatchWriter(session=db_session) as writer:
                for raw in parser(file_path):
                    try:
                        record = adapter.normalize(
                            raw,
                            session_id=session_id,
                            benchmark=benchmark,
                            model=model,
                            model_version=model_version,
                        )
                    except Exception as exc:
                        logger.warning(
                            "parse_file[%s]: adapter.normalize failed at record %d — %s",
                            job_id, processed, exc,
                        )
                        INGEST_RECORDS_TOTAL.labels(status="normalize_error").inc()
                        INGEST_FAILURES_TOTAL.inc()
                        continue

                    if record is None:
                        INGEST_RECORDS_TOTAL.labels(status="skipped").inc()
                        continue

                    await writer.add(record)
                    processed += 1
                    INGEST_RECORDS_TOTAL.labels(status="written").inc()

                    if processed % _PROGRESS_EVERY_N == 0:
                        elapsed = time.monotonic() - start_time
                        speed = processed / elapsed if elapsed > 0 else 0.0
                        await publisher.update(
                            processed=processed,
                            speed_rps=speed,
                        )

            # Writer flushed in __aexit__
            await publisher.complete(
                total_written=writer.total_written,
                total_skipped=writer.total_skipped,
            )

        return {
            "job_id": job_id,
            "status": "done",
            "total_written": writer.total_written,
            "total_skipped": writer.total_skipped,
        }

    except Exception as exc:
        INGEST_FAILURES_TOTAL.inc()
        await publisher.fail(reason=str(exc))
        logger.exception("parse_file[%s] failed: %s", job_id, exc)
        raise


@shared_task(
    name="app.tasks.ingest.parse_file",
    bind=True,
    max_retries=0,          # No automatic retry — caller decides
    acks_late=True,         # Ack after task completes (survive worker restart)
    reject_on_worker_lost=True,
)
def parse_file(
    self,
    file_path: str,
    *,
    adapter_name: str | None = None,
    job_id: str,
    session_id: str,
    benchmark: str,
    model: str,
    model_version: str,
) -> dict:
    """
    Celery task: stream-parse a file and write normalized records to PostgreSQL.

    Args:
        file_path: Absolute path to the file (JSONL or JSON).
        adapter_name: Registered adapter name, or None for auto-detect.
        job_id: UUID for progress tracking via WebSocket.
        session_id: eval_sessions.id this ingest run belongs to.
        benchmark: Benchmark identifier (e.g. "mmlu").
        model: Model identifier.
        model_version: Model version string.
    """
    return run_async_in_worker(
        _run_parse(
            file_path=file_path,
            adapter_name=adapter_name,
            job_id=job_id,
            session_id=session_id,
            benchmark=benchmark,
            model=model,
            model_version=model_version,
        )
    )
