from __future__ import annotations
import time
import logging
import orjson
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

_PROGRESS_CHANNEL_PREFIX = "progress"


@dataclass
class ProgressEvent:
    job_id: str
    processed: int
    total: int | None
    speed_rps: float
    status: Literal["running", "done", "failed"] = "running"
    total_written: int = 0
    total_skipped: int = 0
    reason: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def percent(self) -> float:
        if self.total and self.total > 0:
            return round(self.processed / self.total * 100, 1)
        return 0.0

    def to_json(self) -> bytes:
        return orjson.dumps({
            "job_id": self.job_id,
            "processed": self.processed,
            "total": self.total,
            "percent": self.percent,
            "speed_rps": round(self.speed_rps, 1),
            "status": self.status,
            "total_written": self.total_written,
            "total_skipped": self.total_skipped,
            "reason": self.reason,
            "timestamp": self.timestamp,
        })


class ProgressPublisher:
    """Publishes progress events to a Redis channel for a given job_id."""

    def __init__(self, redis, job_id: str) -> None:
        self._redis = redis
        self._job_id = job_id
        self._channel = f"{_PROGRESS_CHANNEL_PREFIX}:{job_id}"

    async def update(
        self,
        processed: int,
        total: int | None = None,
        speed_rps: float = 0.0,
    ) -> None:
        event = ProgressEvent(
            job_id=self._job_id,
            processed=processed,
            total=total,
            speed_rps=speed_rps,
        )
        await self._redis.publish(self._channel, event.to_json())

    async def complete(self, total_written: int, total_skipped: int) -> None:
        event = ProgressEvent(
            job_id=self._job_id,
            processed=total_written + total_skipped,
            total=total_written + total_skipped,
            speed_rps=0.0,
            status="done",
            total_written=total_written,
            total_skipped=total_skipped,
        )
        await self._redis.publish(self._channel, event.to_json())

    async def fail(self, reason: str) -> None:
        event = ProgressEvent(
            job_id=self._job_id,
            processed=0,
            total=None,
            speed_rps=0.0,
            status="failed",
            reason=reason,
        )
        await self._redis.publish(self._channel, event.to_json())
