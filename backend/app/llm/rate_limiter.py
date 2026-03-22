"""Async request pacing helpers for provider limits."""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable


SleepFunc = Callable[[float], Awaitable[None]]


class AsyncRateLimiter:
    """Enforce a max requests/second rate in-process."""

    def __init__(self, requests_per_second: float | None, sleep_func: SleepFunc = asyncio.sleep) -> None:
        self._rps = requests_per_second if requests_per_second and requests_per_second > 0 else None
        self._sleep = sleep_func
        self._lock = asyncio.Lock()
        self._last_request_monotonic: float | None = None

    async def acquire(self) -> None:
        if self._rps is None:
            return

        min_interval = 1.0 / self._rps
        async with self._lock:
            now = time.monotonic()
            if self._last_request_monotonic is None:
                self._last_request_monotonic = now
                return

            elapsed = now - self._last_request_monotonic
            wait_for = min_interval - elapsed
            if wait_for > 0:
                await self._sleep(wait_for)
                now = time.monotonic()

            self._last_request_monotonic = now
