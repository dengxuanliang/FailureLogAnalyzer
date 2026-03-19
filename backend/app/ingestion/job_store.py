"""
Lightweight job status store backed by Redis hashes.
Keys expire after 24h to avoid Redis bloat.
"""
from __future__ import annotations
import time
import orjson
from typing import Literal

_JOB_TTL_SECONDS = 86_400  # 24 hours
_KEY_PREFIX = "ingest_job"


def _key(job_id: str) -> str:
    return f"{_KEY_PREFIX}:{job_id}"


async def create_job(redis, job_id: str, session_id: str, file_path: str) -> None:
    payload = orjson.dumps({
        "job_id": job_id,
        "session_id": session_id,
        "file_path": file_path,
        "status": "pending",
        "processed": 0,
        "total": None,
        "total_written": 0,
        "total_skipped": 0,
        "created_at": time.time(),
    })
    await redis.set(_key(job_id), payload, ex=_JOB_TTL_SECONDS)


async def get_job_status(redis, job_id: str) -> dict | None:
    raw = await redis.get(_key(job_id))
    if raw is None:
        return None
    return orjson.loads(raw)


async def update_job_from_event(redis, job_id: str, event: dict) -> None:
    """Merge a progress event dict into the stored job status."""
    raw = await redis.get(_key(job_id))
    if raw is None:
        return
    current = orjson.loads(raw)
    current.update({k: v for k, v in event.items() if k in (
        "status", "processed", "total", "total_written", "total_skipped", "reason"
    )})
    await redis.set(_key(job_id), orjson.dumps(current), ex=_JOB_TTL_SECONDS)
