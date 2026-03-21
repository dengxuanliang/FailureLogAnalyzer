"""Redis-backed status store for LLM judge jobs."""
from __future__ import annotations

import time
from typing import Any

import orjson

_KEY_PREFIX = "llm_job"
_JOB_TTL_SECONDS = 86_400


def _key(job_id: str) -> str:
    return f"{_KEY_PREFIX}:{job_id}"


async def create_job(
    redis,
    *,
    job_id: str,
    session_id: str,
    strategy_id: str,
    manual_record_ids: list[str] | None = None,
    celery_task_id: str | None = None,
) -> None:
    now = time.time()
    payload: dict[str, Any] = {
        "job_id": job_id,
        "session_id": session_id,
        "strategy_id": strategy_id,
        "manual_record_ids": manual_record_ids or [],
        "celery_task_id": celery_task_id,
        "status": "queued",
        "processed": 0,
        "total": None,
        "succeeded": 0,
        "failed": 0,
        "total_cost": 0.0,
        "stop_reason": None,
        "reason": "",
        "created_at": now,
        "updated_at": now,
    }
    await redis.set(_key(job_id), orjson.dumps(payload), ex=_JOB_TTL_SECONDS)


async def get_job_status(redis, job_id: str) -> dict | None:
    raw = await redis.get(_key(job_id))
    if raw is None:
        return None
    return orjson.loads(raw)


async def update_job(redis, job_id: str, **updates: Any) -> dict | None:
    existing = await get_job_status(redis, job_id)
    if existing is None:
        return None
    existing.update({k: v for k, v in updates.items() if v is not None or k in {"stop_reason"}})
    existing["updated_at"] = time.time()
    await redis.set(_key(job_id), orjson.dumps(existing), ex=_JOB_TTL_SECONDS)
    return existing
