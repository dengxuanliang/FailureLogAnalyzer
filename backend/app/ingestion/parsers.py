from __future__ import annotations
import logging
from collections.abc import Iterator
import orjson
import ijson
import chardet

logger = logging.getLogger(__name__)

_ENCODING_SAMPLE_BYTES = 65_536  # 64 KB for chardet detection


def _detect_encoding(file_path: str) -> str:
    """Return best-guess encoding for file, falling back to utf-8."""
    try:
        with open(file_path, "rb") as fh:
            sample = fh.read(_ENCODING_SAMPLE_BYTES)
        # Strip BOM if present
        if sample.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        result = chardet.detect(sample)
        return result.get("encoding") or "utf-8"
    except OSError:
        return "utf-8"


def parse_jsonl(file_path: str) -> Iterator[dict]:
    """
    Stream-parse a JSONL file line by line.
    Memory: O(1) — only one decoded line in memory at a time.
    Corrupt lines are logged and skipped.
    """
    encoding = _detect_encoding(file_path)
    line_number = 0
    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as fh:
            for raw_line in fh:
                line_number += 1
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    yield orjson.loads(stripped)
                except orjson.JSONDecodeError as exc:
                    logger.warning(
                        "parse_jsonl: skipping corrupt line %d in %s — %s",
                        line_number, file_path, exc,
                    )
    except OSError as exc:
        logger.error("parse_jsonl: cannot open %s — %s", file_path, exc)
        raise


def parse_large_json(file_path: str) -> Iterator[dict]:
    """
    Stream-parse a JSON file that contains a top-level array.
    Memory: O(1) — items yielded one at a time via ijson.
    Reports parse errors and yields successfully-parsed items up to the error.
    """
    try:
        with open(file_path, "rb") as fh:
            try:
                for item in ijson.items(fh, "item"):
                    yield item
            except ijson.JSONError as exc:
                logger.error(
                    "parse_large_json: JSON parse error in %s — %s (partial data yielded)",
                    file_path, exc,
                )
    except OSError as exc:
        logger.error("parse_large_json: cannot open %s — %s", file_path, exc)
        raise
