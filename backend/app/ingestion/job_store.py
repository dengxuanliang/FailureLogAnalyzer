"""
Lightweight job status store backed by Redis hashes.
Keys expire after 24h to avoid Redis bloat.
"""
from __future__ import annotations
import time
import orjson

_JOB_TTL_SECONDS = 86_400  # 24 hours
_KEY_PREFIX = "ingest_job"
_KEY_PREFIX_WITH_COLON = f"{_KEY_PREFIX}:"


def _key(job_id: str) -> str:
    return f"{_KEY_PREFIX_WITH_COLON}{job_id}"


def _decode_payload(raw) -> dict | None:
    if not isinstance(raw, (bytes, bytearray, memoryview, str)):
        return None
    try:
        decoded = orjson.loads(raw)
    except orjson.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


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
    return _decode_payload(raw)


async def update_job_from_event(redis, job_id: str, event: dict) -> None:
    """Merge a progress event dict into the stored job status."""
    getter = getattr(redis, "get", None)
    setter = getattr(redis, "set", None)
    if not callable(getter) or not callable(setter):
        return

    raw = await getter(_key(job_id))
    if raw is None:
        return
    current = _decode_payload(raw)
    if current is None:
        return
    current.update({k: v for k, v in event.items() if k in (
        "status", "processed", "total", "total_written", "total_skipped", "reason"
    )})
    await setter(_key(job_id), orjson.dumps(current), ex=_JOB_TTL_SECONDS)


async def list_jobs(
    redis,
    *,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    session_id: str | None = None,
) -> tuple[list[dict], int]:
    if limit <= 0:
        return [], 0

    getter = getattr(redis, "get", None)
    scanner = getattr(redis, "scan_iter", None)
    key_getter = getattr(redis, "keys", None)
    if not callable(getter):
        return [], 0

    job_keys: list[str] = []
    if callable(scanner):
        async for raw_key in scanner(f"{_KEY_PREFIX_WITH_COLON}*"):
            if isinstance(raw_key, bytes):
                raw_key = raw_key.decode()
            if isinstance(raw_key, str) and raw_key.startswith(_KEY_PREFIX_WITH_COLON):
                job_keys.append(raw_key)
    elif callable(key_getter):
        raw_keys = await key_getter(f"{_KEY_PREFIX_WITH_COLON}*")
        for raw_key in raw_keys:
            if isinstance(raw_key, bytes):
                raw_key = raw_key.decode()
            if isinstance(raw_key, str) and raw_key.startswith(_KEY_PREFIX_WITH_COLON):
                job_keys.append(raw_key)
    else:
        return [], 0

    jobs: list[dict] = []
    for key in job_keys:
        payload = _decode_payload(await getter(key))
        if payload is None:
            continue
        if status is not None and payload.get("status") != status:
            continue
        if session_id is not None and payload.get("session_id") != session_id:
            continue
        jobs.append(payload)

    jobs.sort(key=lambda item: float(item.get("created_at") or 0.0), reverse=True)
    total = len(jobs)
    return jobs[offset:offset + limit], total
