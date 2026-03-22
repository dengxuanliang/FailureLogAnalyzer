"""Run ingestion directory watcher as a standalone process."""
from __future__ import annotations

import argparse
import logging
import signal

from app.ingestion.directory_watcher import DirectoryWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch a directory for eval log files")
    parser.add_argument("--dir", required=True, help="Directory to watch")
    parser.add_argument("--benchmark", default="auto", help="Benchmark name")
    parser.add_argument("--model", default="unknown", help="Model identifier")
    parser.add_argument("--model-version", default="unknown", help="Model version")
    parser.add_argument("--adapter", default=None, help="Adapter name (default: auto-detect)")
    parser.add_argument("--no-recursive", action="store_true", help="Disable recursive watching")
    args = parser.parse_args()

    watcher = DirectoryWatcher(
        watch_dir=args.dir,
        benchmark=args.benchmark,
        model=args.model,
        model_version=args.model_version,
        adapter_name=args.adapter,
        recursive=not args.no_recursive,
    )

    def _shutdown(signum: int, _frame: object) -> None:
        logger.info("Received signal %s; stopping watcher", signum)
        watcher.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    watcher.start()
    logger.info("Watcher started for %s", args.dir)

    # Block while signals drive shutdown.
    signal.pause()


if __name__ == "__main__":
    main()
