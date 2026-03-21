import time
from unittest.mock import MagicMock

from app.ingestion.directory_watcher import DirectoryWatcher, IngestFileHandler


def test_handler_triggers_on_new_jsonl_file(tmp_path):
    mock_task = MagicMock()
    handler = IngestFileHandler(
        dispatch_fn=mock_task,
        benchmark="auto",
        model="unknown",
        model_version="unknown",
        adapter_name=None,
    )

    from watchdog.events import FileCreatedEvent

    event = FileCreatedEvent(str(tmp_path / "results.jsonl"))
    handler.on_created(event)

    mock_task.assert_called_once()
    args, kwargs = mock_task.call_args
    assert args[0] == str(tmp_path / "results.jsonl")
    assert "job_id" in kwargs
    assert "session_id" in kwargs


def test_handler_ignores_non_json_files(tmp_path):
    mock_task = MagicMock()
    handler = IngestFileHandler(
        dispatch_fn=mock_task,
        benchmark="auto",
        model="unknown",
        model_version="unknown",
    )

    from watchdog.events import FileCreatedEvent

    handler.on_created(FileCreatedEvent(str(tmp_path / "data.csv")))
    handler.on_created(FileCreatedEvent(str(tmp_path / "readme.txt")))
    handler.on_created(FileCreatedEvent(str(tmp_path / "image.png")))

    mock_task.assert_not_called()


def test_handler_triggers_on_json_file(tmp_path):
    mock_task = MagicMock()
    handler = IngestFileHandler(
        dispatch_fn=mock_task,
        benchmark="auto",
        model="unknown",
        model_version="unknown",
    )

    from watchdog.events import FileCreatedEvent

    handler.on_created(FileCreatedEvent(str(tmp_path / "eval.json")))

    mock_task.assert_called_once()


def test_handler_debounces_rapid_events(tmp_path):
    mock_task = MagicMock()
    handler = IngestFileHandler(
        dispatch_fn=mock_task,
        benchmark="auto",
        model="unknown",
        model_version="unknown",
        debounce_seconds=2.0,
    )

    from watchdog.events import FileCreatedEvent

    event = FileCreatedEvent(str(tmp_path / "results.jsonl"))
    handler.on_created(event)
    handler.on_created(event)

    assert mock_task.call_count == 1


def test_handler_processes_move_event(tmp_path):
    mock_task = MagicMock()
    handler = IngestFileHandler(
        dispatch_fn=mock_task,
        benchmark="auto",
        model="unknown",
        model_version="unknown",
    )

    from watchdog.events import FileMovedEvent

    handler.on_moved(FileMovedEvent("/tmp/a.tmp", str(tmp_path / "eval.jsonl")))

    mock_task.assert_called_once()


def test_watcher_creates_directory_if_missing(tmp_path):
    watch_dir = tmp_path / "nonexistent" / "subdir"
    DirectoryWatcher(
        watch_dir=str(watch_dir),
        benchmark="auto",
        model="unknown",
        model_version="unknown",
    )
    assert watch_dir.exists()


def test_watcher_start_stop(tmp_path):
    watcher = DirectoryWatcher(
        watch_dir=str(tmp_path),
        benchmark="auto",
        model="unknown",
        model_version="unknown",
    )
    watcher.start()
    assert watcher.is_running

    # Give observer thread a brief moment to start before stopping.
    time.sleep(0.05)
    watcher.stop()
    assert not watcher.is_running
