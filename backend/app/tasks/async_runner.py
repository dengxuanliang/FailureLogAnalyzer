from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

_T = TypeVar("_T")
_worker_loop: asyncio.AbstractEventLoop | None = None


def run_async_in_worker(awaitable: Awaitable[_T]) -> _T:
    """
    Run async task code on a persistent event loop inside the worker process.

    Our Celery task entrypoints are synchronous, but the async SQLAlchemy engine
    is process-global and its pooled asyncpg connections are loop-bound. Reusing
    one loop per worker process prevents cross-loop connection reuse between
    tasks.
    """

    global _worker_loop

    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()

    asyncio.set_event_loop(_worker_loop)
    return _worker_loop.run_until_complete(awaitable)
