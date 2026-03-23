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
    getter = getattr(redis, "get", None)
    if not callable(getter):
        return None
    raw = await getter(_key(job_id))
    if raw is None:
        return None
    if not isinstance(raw, (bytes, bytearray, memoryview, str)):
        return None
    try:
        decoded = orjson.loads(raw)
    except orjson.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


async def update_job_from_event(redis, job_id: str, event: dict) -> None:
    """Merge a progress event dict into the stored job status."""
    getter = getattr(redis, "get", None)
    setter = getattr(redis, "set", None)
    if not callable(getter) or not callable(setter):
        return

    raw = await getter(_key(job_id))
    if raw is None:
        return
    if not isinstance(raw, (bytes, bytearray, memoryview, str)):
        return
    try:
        current = orjson.loads(raw)
    except orjson.JSONDecodeError:
        return
    current.update({k: v for k, v in event.items() if k in (
        "status", "processed", "total", "total_written", "total_skipped", "reason"
    )})
    await setter(_key(job_id), orjson.dumps(current), ex=_JOB_TTL_SECONDS)
