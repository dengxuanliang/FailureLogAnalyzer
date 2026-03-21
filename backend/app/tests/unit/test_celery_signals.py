from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from app import celery_signals


def test_task_postrun_observes_duration_histogram() -> None:
    task = SimpleNamespace(name="app.tasks.ingest.parse_file")

    with (
        patch("app.celery_signals.time.monotonic", side_effect=[10.0, 13.25]),
        patch("app.celery_signals.CELERY_TASK_DURATION_SECONDS") as mock_histogram,
    ):
        celery_signals._TASK_START_TIMES.clear()
        celery_signals.on_task_prerun(task_id="task-1", task=task)
        celery_signals.on_task_postrun(task_id="task-1", task=task, state="SUCCESS")

    mock_histogram.labels.assert_called_once_with(
        task_name="app.tasks.ingest.parse_file",
        status="success",
    )
    mock_histogram.labels.return_value.observe.assert_called_once_with(3.25)


def test_task_postrun_without_prerun_does_not_observe() -> None:
    task = SimpleNamespace(name="tasks.analysis.run_rules")

    with patch("app.celery_signals.CELERY_TASK_DURATION_SECONDS") as mock_histogram:
        celery_signals._TASK_START_TIMES.clear()
        celery_signals.on_task_postrun(task_id="missing", task=task, state="FAILURE")

    mock_histogram.labels.assert_not_called()


def test_update_worker_online_metrics_counts_per_queue() -> None:
    active_queues = {
        "worker-a@node": [{"name": "celery"}, {"name": "rule"}],
        "worker-b@node": [{"name": "rule"}],
    }

    with patch("app.celery_signals.CELERY_WORKERS_ONLINE") as mock_workers_online:
        counts = celery_signals.update_worker_online_metrics(
            active_queues=active_queues,
            queue_names={"celery", "rule", "llm"},
        )

    assert counts == {"celery": 1, "rule": 2, "llm": 0}
    assert mock_workers_online.labels.call_args_list == [
        call(queue="celery"),
        call(queue="llm"),
        call(queue="rule"),
    ]
    assert mock_workers_online.labels.return_value.set.call_args_list == [
        call(1),
        call(0),
        call(2),
    ]
