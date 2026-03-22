"""Celery signal hooks for task duration and worker observability metrics."""

from __future__ import annotations

import time
from typing import Any

from celery import signals

from app.core.metrics import CELERY_TASK_DURATION_SECONDS, CELERY_WORKERS_ONLINE

DEFAULT_QUEUE_NAMES: tuple[str, ...] = ("celery", "rule", "llm", "report")
_TASK_START_TIMES: dict[str, float] = {}


def _normalise_task_status(state: str | None) -> str:
    if not state:
        return "unknown"
    return str(state).strip().lower()


def on_task_prerun(task_id: str | None = None, task=None, **_: Any) -> None:
    if task_id is None:
        return
    _TASK_START_TIMES[task_id] = time.monotonic()


def on_task_postrun(
    task_id: str | None = None,
    task=None,
    state: str | None = None,
    **_: Any,
) -> None:
    if task_id is None:
        return

    started = _TASK_START_TIMES.pop(task_id, None)
    if started is None:
        return

    task_name = getattr(task, "name", "unknown")
    duration = max(0.0, time.monotonic() - started)

    CELERY_TASK_DURATION_SECONDS.labels(
        task_name=task_name,
        status=_normalise_task_status(state),
    ).observe(duration)


def update_worker_online_metrics(
    active_queues: dict[str, list[dict[str, Any]]] | None,
    queue_names: set[str] | tuple[str, ...] = DEFAULT_QUEUE_NAMES,
) -> dict[str, int]:
    queue_set = set(queue_names)
    workers_per_queue: dict[str, int] = {queue: 0 for queue in queue_set}

    for worker_queues in (active_queues or {}).values():
        for queue_entry in worker_queues or []:
            queue_name = queue_entry.get("name")
            if queue_name in workers_per_queue:
                workers_per_queue[queue_name] += 1

    for queue in sorted(queue_set):
        CELERY_WORKERS_ONLINE.labels(queue=queue).set(workers_per_queue[queue])

    return workers_per_queue


signals.task_prerun.connect(on_task_prerun, weak=False)
signals.task_postrun.connect(on_task_postrun, weak=False)
