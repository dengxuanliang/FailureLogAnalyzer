from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Callable, Any

from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".jsonl", ".json"}
_DEFAULT_DEBOUNCE_SECONDS = 5.0


class IngestFileHandler(FileSystemEventHandler):
    """Dispatch ingest jobs for newly created or moved-in JSON/JSONL files."""

    def __init__(
        self,
        dispatch_fn: Callable[..., Any],
        benchmark: str = "auto",
        model: str = "unknown",
        model_version: str = "unknown",
        adapter_name: str | None = None,
        debounce_seconds: float = _DEFAULT_DEBOUNCE_SECONDS,
    ) -> None:
        super().__init__()
        self._dispatch_fn = dispatch_fn
        self._benchmark = benchmark
        self._model = model
        self._model_version = model_version
        self._adapter_name = adapter_name
        self._debounce_seconds = debounce_seconds
        self._seen: dict[str, float] = {}
        self._lock = Lock()

    def _should_process(self, file_path: str) -> bool:
        if Path(file_path).suffix.lower() not in _ALLOWED_EXTENSIONS:
            return False

        now = time.monotonic()
        with self._lock:
            last_seen = self._seen.get(file_path, 0.0)
            if now - last_seen < self._debounce_seconds:
                logger.debug("Debounced duplicate watcher event for %s", file_path)
                return False
            self._seen[file_path] = now
        return True

    def _dispatch(self, file_path: str) -> None:
        job_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        logger.info("Detected file %s; dispatching ingest job %s", file_path, job_id)
        self._dispatch_fn(
            file_path,
            adapter_name=self._adapter_name,
            job_id=job_id,
            session_id=session_id,
            benchmark=self._benchmark,
            model=self._model,
            model_version=self._model_version,
        )

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            self._dispatch(event.src_path)

    def on_moved(self, event: FileMovedEvent) -> None:
        if event.is_directory:
            return
        if self._should_process(event.dest_path):
            self._dispatch(event.dest_path)


class DirectoryWatcher:
    """Manage watchdog Observer lifecycle for auto-ingestion."""

    def __init__(
        self,
        watch_dir: str,
        benchmark: str = "auto",
        model: str = "unknown",
        model_version: str = "unknown",
        adapter_name: str | None = None,
        recursive: bool = True,
        debounce_seconds: float = _DEFAULT_DEBOUNCE_SECONDS,
    ) -> None:
        self._watch_dir = Path(watch_dir)
        self._watch_dir.mkdir(parents=True, exist_ok=True)
        self._recursive = recursive

        self._handler = IngestFileHandler(
            dispatch_fn=self._default_dispatch,
            benchmark=benchmark,
            model=model,
            model_version=model_version,
            adapter_name=adapter_name,
            debounce_seconds=debounce_seconds,
        )
        self._observer = Observer()
        self._running = False

    @property
    def watch_dir(self) -> Path:
        return self._watch_dir

    @property
    def is_running(self) -> bool:
        return self._running

    @staticmethod
    def _default_dispatch(file_path: str, **kwargs: Any) -> None:
        from app.tasks.ingest import parse_file

        parse_file.delay(file_path, **kwargs)

    def start(self) -> None:
        if self._running:
            return

        self._observer.schedule(self._handler, str(self._watch_dir), recursive=self._recursive)
        self._observer.start()
        self._running = True
        logger.info("DirectoryWatcher started for %s", self._watch_dir)

    def stop(self) -> None:
        if not self._running:
            return

        self._observer.stop()
        self._observer.join(timeout=10)
        self._running = False
        logger.info("DirectoryWatcher stopped for %s", self._watch_dir)
