# Ingestion Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Ingestion Agent — a streaming file-parsing pipeline with pluggable benchmark adapters, Celery-backed async processing, WebSocket progress reporting, three REST endpoints for triggering and monitoring ingestion jobs, and a watchdog-based directory watcher for production auto-ingest.

**Architecture:** Files are uploaded or discovered via REST endpoints; a Celery task (`tasks.ingest.parse_file`) streams each file through a benchmark-specific adapter that maps raw records to `NormalizedRecord`, buffering 1000 records per batch before writing to PostgreSQL. Progress events are published to Redis and broadcast over a FastAPI WebSocket endpoint, keeping peak memory below 256 MB regardless of file size.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 (async), Celery 5 + Redis, ijson, orjson, chardet, pytest + pytest-asyncio, factory-boy, httpx (AsyncClient for tests).

---

## Prerequisites (Plan 1 must be complete)

Plan 1 provides:
- `/backend/` — FastAPI app factory at `backend/app/main.py`
- `/backend/app/db/` — SQLAlchemy async engine, `Base`, Alembic config
- `/backend/app/models/` — `EvalSession`, `EvalRecord` ORM models
- `/backend/app/core/config.py` — `Settings` (DATABASE_URL, REDIS_URL, CELERY_BROKER_URL)
- `/backend/celery_app.py` — Celery application instance
- `/backend/tests/conftest.py` — `async_db_session`, `async_client` fixtures
- Docker Compose with `postgres`, `redis`, `api`, `worker` services

---

## Task List

### TASK 1 — NormalizedRecord data structure

- [ ] **1.1 Write failing test**

  File: `backend/tests/ingestion/test_normalized_record.py` (Create)

  ```python
  import pytest
  from pydantic import ValidationError
  from app.ingestion.schemas import NormalizedRecord

  def test_required_fields_present():
      r = NormalizedRecord(
          session_id="550e8400-e29b-41d4-a716-446655440000",
          benchmark="mmlu",
          model="model-v1",
          model_version="v1",
          question_id="q_001",
          question="What is 2+2?",
          expected_answer="4",
          model_answer="4",
          is_correct=True,
      )
      assert r.score == 0.0  # default
      assert r.metadata == {}
      assert r.raw_json == {}

  def test_is_correct_required():
      with pytest.raises(ValidationError):
          NormalizedRecord(
              session_id="550e8400-e29b-41d4-a716-446655440000",
              benchmark="mmlu",
              model="model-v1",
              model_version="v1",
              question_id="q_001",
              question="What is 2+2?",
              expected_answer="4",
              model_answer="4",
              # is_correct missing
          )

  def test_sha256_computed_from_session_and_question_id():
      r = NormalizedRecord(
          session_id="550e8400-e29b-41d4-a716-446655440000",
          benchmark="mmlu",
          model="model-v1",
          model_version="v1",
          question_id="q_001",
          question="x",
          expected_answer="y",
          model_answer="z",
          is_correct=False,
      )
      import hashlib
      expected = hashlib.sha256(
          b"550e8400-e29b-41d4-a716-446655440000:q_001"
      ).hexdigest()
      assert r.dedup_hash == expected
  ```

  Run: `cd backend && pytest tests/ingestion/test_normalized_record.py -x`
  Expected: `FAILED` (ImportError — module does not exist yet)

- [ ] **1.2 Implement `NormalizedRecord`**

  File: `backend/app/ingestion/__init__.py` (Create — empty)

  File: `backend/app/ingestion/schemas.py` (Create)

  ```python
  from __future__ import annotations
  import hashlib
  from typing import Any
  from pydantic import BaseModel, Field, model_validator

  class NormalizedRecord(BaseModel):
      """Standard representation of one evaluation record across all benchmarks."""
      session_id: str
      benchmark: str
      model: str
      model_version: str
      task_category: str = ""
      question_id: str
      question: str
      expected_answer: str
      model_answer: str
      is_correct: bool
      score: float = 0.0
      extracted_code: str = ""
      metadata: dict[str, Any] = Field(default_factory=dict)
      raw_json: dict[str, Any] = Field(default_factory=dict)

      # Computed on construction — NOT a constructor argument
      dedup_hash: str = Field(default="", init=False)

      @model_validator(mode="after")
      def _compute_dedup_hash(self) -> NormalizedRecord:
          key = f"{self.session_id}:{self.question_id}".encode()
          self.dedup_hash = hashlib.sha256(key).hexdigest()
          return self
  ```

  Run: `cd backend && pytest tests/ingestion/test_normalized_record.py -x`
  Expected: `3 passed`

- [ ] **1.3 Commit**

  ```bash
  git add backend/app/ingestion/ backend/tests/ingestion/
  git commit -m "feat(ingestion): add NormalizedRecord pydantic schema with dedup_hash"
  ```

---

### TASK 2 — BaseAdapter + `@register_adapter` plugin mechanism

- [ ] **2.1 Write failing test**

  File: `backend/tests/ingestion/test_adapter_registry.py` (Create)

  ```python
  import pytest
  from app.ingestion.adapters.registry import register_adapter, get_adapter, AdapterRegistry

  def test_register_and_retrieve():
      @register_adapter("test_bench")
      class _Adapter:
          def detect(self, first_line: str) -> float:
              return 0.9
          def normalize(self, raw: dict) -> dict:
              return raw
      
      adapter = get_adapter("test_bench")
      assert adapter is not None
      assert adapter.__class__.__name__ == "_Adapter"

  def test_unknown_adapter_returns_none():
      assert get_adapter("does_not_exist_xyz") is None

  def test_auto_detect_returns_highest_confidence(tmp_path):
      from app.ingestion.adapters.registry import auto_detect_adapter
      
      @register_adapter("low_conf")
      class _Low:
          def detect(self, line: str) -> float: return 0.2
          def normalize(self, r: dict) -> dict: return r
      
      @register_adapter("high_conf")
      class _High:
          def detect(self, line: str) -> float: return 0.95
          def normalize(self, r: dict) -> dict: return r
      
      f = tmp_path / "sample.jsonl"
      f.write_text('{"is_correct": true}\n')
      result = auto_detect_adapter(str(f))
      assert result is not None
      assert result.__class__.__name__ == "_High"
  ```

  Run: `cd backend && pytest tests/ingestion/test_adapter_registry.py -x`
  Expected: `FAILED` (ImportError)

- [ ] **2.2 Implement registry**

  File: `backend/app/ingestion/adapters/__init__.py` (Create — empty)

  File: `backend/app/ingestion/adapters/registry.py` (Create)

  ```python
  from __future__ import annotations
  import logging
  from typing import Protocol, runtime_checkable

  logger = logging.getLogger(__name__)

  @runtime_checkable
  class AdapterProtocol(Protocol):
      def detect(self, first_line: str) -> float:
          """Return confidence 0.0-1.0 that this adapter handles the file."""
          ...
      def normalize(self, raw: dict) -> dict:
          """Map raw record dict to NormalizedRecord field dict."""
          ...

  # Module-level registry: name → adapter instance
  _REGISTRY: dict[str, AdapterProtocol] = {}

  def register_adapter(name: str):
      """Class decorator that registers an adapter under `name`."""
      def decorator(cls):
          instance = cls()
          _REGISTRY[name] = instance
          logger.debug("Registered adapter %r as %r", cls.__name__, name)
          return cls
      return decorator

  def get_adapter(name: str) -> AdapterProtocol | None:
      return _REGISTRY.get(name)

  def auto_detect_adapter(file_path: str) -> AdapterProtocol | None:
      """Read first non-empty line and return adapter with highest detect() score."""
      first_line = ""
      try:
          with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
              for raw in fh:
                  stripped = raw.strip()
                  if stripped:
                      first_line = stripped
                      break
      except OSError as exc:
          logger.warning("auto_detect_adapter: cannot open %s — %s", file_path, exc)
          return None

      best_name, best_score = None, 0.0
      for name, adapter in _REGISTRY.items():
          try:
              score = adapter.detect(first_line)
          except Exception:
              score = 0.0
          if score > best_score:
              best_score = score
              best_name = name

      if best_name is None or best_score == 0.0:
          return None
      return _REGISTRY[best_name]
  ```

- [ ] **2.3 Implement BaseAdapter**

  File: `backend/app/ingestion/adapters/base.py` (Create)

  ```python
  from __future__ import annotations
  import orjson
  from abc import ABC, abstractmethod
  from app.ingestion.schemas import NormalizedRecord


  class BaseAdapter(ABC):
      """
      Subclass this and decorate with @register_adapter("name").
      Subclasses must implement `detect` and `normalize`.
      """

      @abstractmethod
      def detect(self, first_line: str) -> float:
          """Return confidence 0.0–1.0 that this adapter handles the data."""

      @abstractmethod
      def normalize(self, raw: dict) -> NormalizedRecord | None:
          """
          Convert a raw parsed dict to NormalizedRecord.
          Return None to skip the record (e.g. correct answers when loading errors-only).
          """

      def safe_normalize(self, raw: dict) -> NormalizedRecord | None:
          """Call normalize; log and return None on any exception."""
          try:
              return self.normalize(raw)
          except Exception as exc:
              import logging
              logging.getLogger(__name__).warning(
                  "Adapter %s failed on record: %s — %s",
                  self.__class__.__name__,
                  orjson.dumps(raw)[:200].decode(),
                  exc,
              )
              return None
  ```

  Run: `cd backend && pytest tests/ingestion/test_adapter_registry.py -x`
  Expected: `3 passed`

- [ ] **2.4 Commit**

  ```bash
  git add backend/app/ingestion/adapters/
  git commit -m "feat(ingestion): add BaseAdapter and @register_adapter plugin registry"
  ```

---

### TASK 3 — Example adapter: `generic_jsonl`

- [ ] **3.1 Write failing test**

  File: `backend/tests/ingestion/test_generic_jsonl_adapter.py` (Create)

  ```python
  import pytest
  from app.ingestion.adapters.generic_jsonl import GenericJsonlAdapter

  @pytest.fixture
  def adapter():
      return GenericJsonlAdapter()

  def test_detect_high_confidence_with_is_correct(adapter):
      line = '{"question": "x", "is_correct": false, "model_answer": "y"}'
      assert adapter.detect(line) >= 0.8

  def test_detect_low_confidence_without_is_correct(adapter):
      line = '{"foo": "bar"}'
      assert adapter.detect(line) < 0.5

  def test_normalize_minimal_record(adapter):
      raw = {
          "question_id": "q1",
          "question": "What is 2+2?",
          "expected_answer": "4",
          "model_answer": "4",
          "is_correct": True,
      }
      # normalize requires session_id injected externally
      record = adapter.normalize(raw, session_id="sess-1", benchmark="generic", model="m1", model_version="v1")
      assert record is not None
      assert record.is_correct is True
      assert record.question_id == "q1"

  def test_normalize_skips_correct_when_errors_only_false(adapter):
      raw = {"question_id": "q1", "question": "x", "expected_answer": "y",
             "model_answer": "z", "is_correct": True}
      record = adapter.normalize(raw, session_id="s", benchmark="g", model="m", model_version="v")
      assert record is not None  # does NOT skip correct records

  def test_normalize_captures_extra_fields_in_metadata(adapter):
      raw = {
          "question_id": "q2",
          "question": "q",
          "expected_answer": "a",
          "model_answer": "b",
          "is_correct": False,
          "custom_score": 0.3,
          "difficulty": "hard",
      }
      record = adapter.normalize(raw, session_id="s", benchmark="g", model="m", model_version="v")
      assert record.metadata["difficulty"] == "hard"
      assert record.metadata["custom_score"] == pytest.approx(0.3)
  ```

  Run: `cd backend && pytest tests/ingestion/test_generic_jsonl_adapter.py -x`
  Expected: `FAILED` (ImportError)

- [ ] **3.2 Implement `GenericJsonlAdapter`**

  File: `backend/app/ingestion/adapters/generic_jsonl.py` (Create)

  ```python
  from __future__ import annotations
  import orjson
  from app.ingestion.adapters.base import BaseAdapter
  from app.ingestion.adapters.registry import register_adapter
  from app.ingestion.schemas import NormalizedRecord

  _KNOWN_FIELDS = frozenset({
      "question_id", "question", "expected_answer", "model_answer",
      "is_correct", "score", "task_category", "extracted_code",
  })


  @register_adapter("generic_jsonl")
  class GenericJsonlAdapter(BaseAdapter):
      """
      Handles any JSONL file that contains at least an `is_correct` field.
      Unknown fields are preserved in `metadata`.
      """

      def detect(self, first_line: str) -> float:
          try:
              obj = orjson.loads(first_line)
          except Exception:
              return 0.0
          if "is_correct" in obj:
              return 0.9
          # Partial match: has question + model_answer
          if "question" in obj and "model_answer" in obj:
              return 0.4
          return 0.0

      def normalize(
          self,
          raw: dict,
          *,
          session_id: str,
          benchmark: str,
          model: str,
          model_version: str,
      ) -> NormalizedRecord | None:
          # Extract known fields; rest goes to metadata
          metadata = {k: v for k, v in raw.items() if k not in _KNOWN_FIELDS}
          return NormalizedRecord(
              session_id=session_id,
              benchmark=benchmark,
              model=model,
              model_version=model_version,
              task_category=raw.get("task_category", ""),
              question_id=str(raw.get("question_id", "")),
              question=str(raw.get("question", "")),
              expected_answer=str(raw.get("expected_answer", "")),
              model_answer=str(raw.get("model_answer", "")),
              is_correct=bool(raw.get("is_correct", False)),
              score=float(raw.get("score", 0.0)),
              extracted_code=str(raw.get("extracted_code", "")),
              metadata=metadata,
              raw_json=raw,
          )
  ```

  Note: `normalize()` on `BaseAdapter` takes only `self, raw`. The `GenericJsonlAdapter` overrides with extra keyword-only args for context; the streaming parser passes them explicitly. `safe_normalize` is not used here because we need the extra kwargs — the parser calls `adapter.normalize(raw, ...)` directly and wraps in try/except.

  Run: `cd backend && pytest tests/ingestion/test_generic_jsonl_adapter.py -x`
  Expected: `5 passed`

- [ ] **3.3 Commit**

  ```bash
  git add backend/app/ingestion/adapters/generic_jsonl.py backend/tests/ingestion/test_generic_jsonl_adapter.py
  git commit -m "feat(ingestion): add generic_jsonl adapter (detect + normalize)"
  ```

---

### TASK 4 — JSONL streaming parser (O(1) memory, readline)

- [ ] **4.1 Write failing test**

  File: `backend/tests/ingestion/test_parsers.py` (Create)

  ```python
  import json
  import pytest
  from pathlib import Path
  from app.ingestion.parsers import parse_jsonl, parse_large_json

  @pytest.fixture
  def jsonl_file(tmp_path):
      lines = [
          {"question_id": f"q{i}", "question": f"Q{i}", "expected_answer": "A",
           "model_answer": "B", "is_correct": i % 2 == 0}
          for i in range(5)
      ]
      p = tmp_path / "data.jsonl"
      p.write_text("\n".join(json.dumps(l) for l in lines))
      return str(p)

  def test_parse_jsonl_yields_all_records(jsonl_file):
      records = list(parse_jsonl(jsonl_file))
      assert len(records) == 5
      assert records[0]["question_id"] == "q0"

  def test_parse_jsonl_skips_blank_lines(tmp_path):
      p = tmp_path / "gaps.jsonl"
      p.write_text('\n{"question_id":"a","is_correct":true}\n\n{"question_id":"b","is_correct":false}\n')
      records = list(parse_jsonl(str(p)))
      assert len(records) == 2

  def test_parse_jsonl_skips_corrupt_lines(tmp_path):
      p = tmp_path / "bad.jsonl"
      p.write_text('{"question_id":"a","is_correct":true}\nNOT_JSON\n{"question_id":"b","is_correct":false}\n')
      records = list(parse_jsonl(str(p)))
      assert len(records) == 2  # corrupt line skipped

  @pytest.fixture
  def large_json_file(tmp_path):
      data = [
          {"question_id": f"q{i}", "question": f"Q{i}", "expected_answer": "A",
           "model_answer": "B", "is_correct": False}
          for i in range(4)
      ]
      p = tmp_path / "big.json"
      p.write_text(json.dumps(data))
      return str(p)

  def test_parse_large_json_yields_all_items(large_json_file):
      records = list(parse_large_json(large_json_file))
      assert len(records) == 4
      assert records[2]["question_id"] == "q2"
  ```

  Run: `cd backend && pytest tests/ingestion/test_parsers.py -x`
  Expected: `FAILED` (ImportError)

- [ ] **4.2 Implement parsers**

  File: `backend/app/ingestion/parsers.py` (Create)

  ```python
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
      encoding = _detect_encoding(file_path)
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
  ```

  Run: `cd backend && pytest tests/ingestion/test_parsers.py -x`
  Expected: `5 passed`

- [ ] **4.3 Commit**

  ```bash
  git add backend/app/ingestion/parsers.py backend/tests/ingestion/test_parsers.py
  git commit -m "feat(ingestion): add O(1) JSONL and large-JSON streaming parsers"
  ```

---

### TASK 5 — Duplicate detection (SHA256) + batch DB writer

- [ ] **5.1 Write failing test**

  File: `backend/tests/ingestion/test_db_writer.py` (Create)

  ```python
  import pytest
  import pytest_asyncio
  from unittest.mock import AsyncMock, MagicMock, patch
  from app.ingestion.db_writer import BatchWriter, DuplicateSkippedError

  @pytest.mark.asyncio
  async def test_batch_writer_flushes_at_batch_size():
      mock_session = AsyncMock()
      mock_session.execute = AsyncMock()
      mock_session.commit = AsyncMock()

      writer = BatchWriter(session=mock_session, batch_size=3)
      
      from app.ingestion.schemas import NormalizedRecord
      records = [
          NormalizedRecord(session_id="s", benchmark="b", model="m",
                           model_version="v", question_id=f"q{i}",
                           question="x", expected_answer="y",
                           model_answer="z", is_correct=False)
          for i in range(3)
      ]
      for r in records:
          await writer.add(r)
      
      # After 3 records, flush should have been called once
      assert writer.flush_count == 1

  @pytest.mark.asyncio
  async def test_batch_writer_final_flush():
      mock_session = AsyncMock()
      mock_session.execute = AsyncMock()
      mock_session.commit = AsyncMock()
      
      writer = BatchWriter(session=mock_session, batch_size=10)
      from app.ingestion.schemas import NormalizedRecord
      r = NormalizedRecord(session_id="s", benchmark="b", model="m",
                           model_version="v", question_id="q1",
                           question="x", expected_answer="y",
                           model_answer="z", is_correct=False)
      await writer.add(r)
      await writer.flush()
      
      assert writer.flush_count == 1

  @pytest.mark.asyncio
  async def test_batch_writer_dedup_skips_seen_hash():
      mock_session = AsyncMock()
      mock_session.execute = AsyncMock()
      mock_session.commit = AsyncMock()

      writer = BatchWriter(session=mock_session, batch_size=100)
      from app.ingestion.schemas import NormalizedRecord
      r = NormalizedRecord(session_id="s", benchmark="b", model="m",
                           model_version="v", question_id="q1",
                           question="x", expected_answer="y",
                           model_answer="z", is_correct=False)
      await writer.add(r)
      await writer.add(r)  # exact duplicate
      
      assert writer.total_written == 1
      assert writer.total_skipped == 1
  ```

  Run: `cd backend && pytest tests/ingestion/test_db_writer.py -x`
  Expected: `FAILED` (ImportError)

- [ ] **5.2 Implement BatchWriter**

  File: `backend/app/ingestion/db_writer.py` (Create)

  ```python
  from __future__ import annotations
  import logging
  from typing import TYPE_CHECKING
  import orjson
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy.dialects.postgresql import insert as pg_insert

  from app.ingestion.schemas import NormalizedRecord
  from app.models.eval_record import EvalRecord  # ORM model from Plan 1

  if TYPE_CHECKING:
      pass

  logger = logging.getLogger(__name__)

  _BATCH_SIZE = 1000


  class DuplicateSkippedError(Exception):
      pass


  class BatchWriter:
      """
      Buffers NormalizedRecord objects and flushes to PostgreSQL in batches.
      Deduplication is performed in-memory (per-file) via SHA-256 dedup_hash.
      On-disk dedup (cross-upload) is handled by a unique index on eval_records.dedup_hash.
      """

      def __init__(self, session: AsyncSession, batch_size: int = _BATCH_SIZE) -> None:
          self._session = session
          self._batch_size = batch_size
          self._buffer: list[NormalizedRecord] = []
          self._seen_hashes: set[str] = set()
          self.total_written = 0
          self.total_skipped = 0
          self.flush_count = 0

      async def add(self, record: NormalizedRecord) -> None:
          if record.dedup_hash in self._seen_hashes:
              self.total_skipped += 1
              return
          self._seen_hashes.add(record.dedup_hash)
          self._buffer.append(record)
          if len(self._buffer) >= self._batch_size:
              await self.flush()

      async def flush(self) -> None:
          if not self._buffer:
              return
          rows = [
              {
                  "session_id": r.session_id,
                  "benchmark": r.benchmark,
                  "model": r.model,
                  "model_version": r.model_version,
                  "task_category": r.task_category,
                  "question_id": r.question_id,
                  "question": r.question,
                  "expected_answer": r.expected_answer,
                  "model_answer": r.model_answer,
                  "is_correct": r.is_correct,
                  "score": r.score,
                  "extracted_code": r.extracted_code,
                  "metadata": orjson.loads(orjson.dumps(r.metadata)),
                  "raw_json": orjson.loads(orjson.dumps(r.raw_json)),
                  "dedup_hash": r.dedup_hash,
              }
              for r in self._buffer
          ]
          stmt = pg_insert(EvalRecord).values(rows).on_conflict_do_nothing(
              index_elements=["dedup_hash"]
          )
          result = await self._session.execute(stmt)
          await self._session.commit()
          written = result.rowcount if result.rowcount is not None else len(rows)
          skipped_in_db = len(rows) - written
          self.total_written += written
          self.total_skipped += skipped_in_db
          self.flush_count += 1
          logger.debug(
              "BatchWriter flushed %d rows (skipped %d duplicates in DB)",
              written, skipped_in_db,
          )
          self._buffer.clear()

      async def __aenter__(self) -> BatchWriter:
          return self

      async def __aexit__(self, exc_type, exc, tb) -> None:
          if exc_type is None:
              await self.flush()
  ```

  Note: Requires `EvalRecord` to have a `dedup_hash` VARCHAR column with a unique index. Add to the Alembic migration created in Plan 1 (or create a new migration):

  File: `backend/alembic/versions/002_add_dedup_hash_to_eval_records.py` (Create)

  ```python
  """add dedup_hash to eval_records

  Revision ID: 002
  Revises: 001
  """
  from alembic import op
  import sqlalchemy as sa

  def upgrade():
      op.add_column("eval_records", sa.Column("dedup_hash", sa.String(64), nullable=True))
      op.create_unique_constraint("uq_eval_records_dedup_hash", "eval_records", ["dedup_hash"])
      op.create_index("ix_eval_records_dedup_hash", "eval_records", ["dedup_hash"])

  def downgrade():
      op.drop_index("ix_eval_records_dedup_hash", table_name="eval_records")
      op.drop_constraint("uq_eval_records_dedup_hash", "eval_records")
      op.drop_column("eval_records", "dedup_hash")
  ```

  Run: `cd backend && pytest tests/ingestion/test_db_writer.py -x`
  Expected: `3 passed`

- [ ] **5.3 Commit**

  ```bash
  git add backend/app/ingestion/db_writer.py backend/alembic/versions/002_add_dedup_hash_to_eval_records.py backend/tests/ingestion/test_db_writer.py
  git commit -m "feat(ingestion): add BatchWriter with SHA-256 dedup and 1000-record batch flush"
  ```

---

### TASK 6 — Progress publisher (Redis pub/sub)

- [ ] **6.1 Write failing test**

  File: `backend/tests/ingestion/test_progress.py` (Create)

  ```python
  import pytest
  from unittest.mock import AsyncMock, patch, call
  from app.ingestion.progress import ProgressPublisher, ProgressEvent

  @pytest.mark.asyncio
  async def test_publish_sends_to_redis_channel():
      mock_redis = AsyncMock()
      pub = ProgressPublisher(redis=mock_redis, job_id="job-123")
      
      await pub.update(processed=500, total=1000, speed_rps=2500.0)
      
      mock_redis.publish.assert_called_once()
      channel, payload = mock_redis.publish.call_args[0]
      assert channel == "progress:job-123"
      
      import orjson
      data = orjson.loads(payload)
      assert data["processed"] == 500
      assert data["total"] == 1000
      assert data["percent"] == pytest.approx(50.0)

  @pytest.mark.asyncio
  async def test_publish_complete_sets_status_done():
      mock_redis = AsyncMock()
      pub = ProgressPublisher(redis=mock_redis, job_id="job-456")
      await pub.complete(total_written=800, total_skipped=200)
      
      import orjson
      channel, payload = mock_redis.publish.call_args[0]
      data = orjson.loads(payload)
      assert data["status"] == "done"
      assert data["total_written"] == 800

  @pytest.mark.asyncio
  async def test_publish_error_sets_status_failed():
      mock_redis = AsyncMock()
      pub = ProgressPublisher(redis=mock_redis, job_id="job-789")
      await pub.fail(reason="File not found")
      
      import orjson
      _, payload = mock_redis.publish.call_args[0]
      data = orjson.loads(payload)
      assert data["status"] == "failed"
      assert "File not found" in data["reason"]
  ```

  Run: `cd backend && pytest tests/ingestion/test_progress.py -x`
  Expected: `FAILED` (ImportError)

- [ ] **6.2 Implement ProgressPublisher**

  File: `backend/app/ingestion/progress.py` (Create)

  ```python
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
  ```

  Run: `cd backend && pytest tests/ingestion/test_progress.py -x`
  Expected: `3 passed`

- [ ] **6.3 Commit**

  ```bash
  git add backend/app/ingestion/progress.py backend/tests/ingestion/test_progress.py
  git commit -m "feat(ingestion): add ProgressPublisher for Redis pub/sub progress events"
  ```

---

### TASK 7 — Celery task: `tasks.ingest.parse_file`

- [ ] **7.1 Write failing test**

  File: `backend/tests/ingestion/test_celery_task.py` (Create)

  ```python
  import pytest
  import json
  from unittest.mock import patch, AsyncMock, MagicMock
  from app.tasks.ingest import parse_file

  @pytest.fixture
  def sample_jsonl(tmp_path):
      lines = [
          {"question_id": f"q{i}", "question": f"Q{i}", "expected_answer": "A",
           "model_answer": "B", "is_correct": False}
          for i in range(5)
      ]
      p = tmp_path / "test.jsonl"
      p.write_text("\n".join(json.dumps(l) for l in lines))
      return str(p)

  def test_parse_file_task_is_registered():
      from celery import current_app
      # Task must be discoverable
      assert "app.tasks.ingest.parse_file" in parse_file.name or \
             parse_file.name.endswith("parse_file")

  def test_parse_file_runs_synchronously(sample_jsonl):
      """Integration smoke test using task's .apply() (no broker needed)."""
      from unittest.mock import patch, AsyncMock, call
      
      # Mock the DB session and Redis
      mock_writer = MagicMock()
      mock_writer.__aenter__ = AsyncMock(return_value=mock_writer)
      mock_writer.__aexit__ = AsyncMock(return_value=False)
      mock_writer.add = AsyncMock()
      mock_writer.flush = AsyncMock()
      mock_writer.total_written = 5
      mock_writer.total_skipped = 0
      mock_writer.flush_count = 1

      with patch("app.tasks.ingest.BatchWriter", return_value=mock_writer), \
           patch("app.tasks.ingest.get_async_session") as mock_sess, \
           patch("app.tasks.ingest.get_redis") as mock_redis:
          
          mock_sess.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
          mock_sess.return_value.__aexit__ = AsyncMock(return_value=False)
          mock_redis.return_value = AsyncMock()

          result = parse_file.apply(
              args=[sample_jsonl],
              kwargs={
                  "adapter_name": "generic_jsonl",
                  "job_id": "test-job-1",
                  "session_id": "sess-abc",
                  "benchmark": "generic",
                  "model": "test-model",
                  "model_version": "v1",
              }
          )
          assert result.state in ("SUCCESS", "PENDING")
  ```

  Run: `cd backend && pytest tests/ingestion/test_celery_task.py::test_parse_file_task_is_registered -x`
  Expected: `FAILED` (ImportError)

- [ ] **7.2 Implement Celery task**

  File: `backend/app/tasks/__init__.py` (Create — empty)

  File: `backend/app/tasks/ingest.py` (Create)

  ```python
  from __future__ import annotations
  import asyncio
  import logging
  import time
  from pathlib import Path

  from celery import shared_task

  from app.ingestion.adapters.registry import get_adapter, auto_detect_adapter
  from app.ingestion.db_writer import BatchWriter
  from app.ingestion.parsers import parse_jsonl, parse_large_json
  from app.ingestion.progress import ProgressPublisher
  from app.db.session import get_async_session   # from Plan 1
  from app.core.redis import get_redis            # async Redis client from Plan 1

  logger = logging.getLogger(__name__)

  _PROGRESS_EVERY_N = 500  # publish progress every N records


  def _get_parser(file_path: str):
      """Choose parser based on file extension."""
      suffix = Path(file_path).suffix.lower()
      if suffix == ".jsonl":
          return parse_jsonl
      elif suffix == ".json":
          return parse_large_json
      else:
          # Try JSONL first (most common), fall back to large JSON
          return parse_jsonl


  async def _run_parse(
      file_path: str,
      adapter_name: str | None,
      job_id: str,
      session_id: str,
      benchmark: str,
      model: str,
      model_version: str,
  ) -> dict:
      # Resolve adapter
      if adapter_name:
          adapter = get_adapter(adapter_name)
          if adapter is None:
              raise ValueError(f"Unknown adapter: {adapter_name!r}")
      else:
          adapter = auto_detect_adapter(file_path)
          if adapter is None:
              raise ValueError(
                  f"Could not auto-detect adapter for {file_path}. "
                  "Specify adapter_name explicitly."
              )

      parser = _get_parser(file_path)
      redis = await get_redis()
      publisher = ProgressPublisher(redis=redis, job_id=job_id)

      processed = 0
      start_time = time.monotonic()

      try:
          async with get_async_session() as db_session:
              async with BatchWriter(session=db_session) as writer:
                  for raw in parser(file_path):
                      try:
                          record = adapter.normalize(
                              raw,
                              session_id=session_id,
                              benchmark=benchmark,
                              model=model,
                              model_version=model_version,
                          )
                      except Exception as exc:
                          logger.warning(
                              "parse_file[%s]: adapter.normalize failed at record %d — %s",
                              job_id, processed, exc,
                          )
                          continue

                      if record is None:
                          continue

                      await writer.add(record)
                      processed += 1

                      if processed % _PROGRESS_EVERY_N == 0:
                          elapsed = time.monotonic() - start_time
                          speed = processed / elapsed if elapsed > 0 else 0.0
                          await publisher.update(
                              processed=processed,
                              speed_rps=speed,
                          )

              # Writer flushed in __aexit__
              await publisher.complete(
                  total_written=writer.total_written,
                  total_skipped=writer.total_skipped,
              )

          return {
              "job_id": job_id,
              "status": "done",
              "total_written": writer.total_written,
              "total_skipped": writer.total_skipped,
          }

      except Exception as exc:
          await publisher.fail(reason=str(exc))
          logger.exception("parse_file[%s] failed: %s", job_id, exc)
          raise


  @shared_task(
      name="app.tasks.ingest.parse_file",
      bind=True,
      max_retries=0,         # No automatic retry — caller decides
      acks_late=True,        # Ack after task completes (survive worker restart)
      reject_on_worker_lost=True,
  )
  def parse_file(
      self,
      file_path: str,
      *,
      adapter_name: str | None = None,
      job_id: str,
      session_id: str,
      benchmark: str,
      model: str,
      model_version: str,
  ) -> dict:
      """
      Celery task: stream-parse a file and write normalized records to PostgreSQL.

      Args:
          file_path: Absolute path to the file (JSONL or JSON).
          adapter_name: Registered adapter name, or None for auto-detect.
          job_id: UUID for progress tracking via WebSocket.
          session_id: eval_sessions.id this ingest run belongs to.
          benchmark: Benchmark identifier (e.g. "mmlu").
          model: Model identifier.
          model_version: Model version string.
      """
      return asyncio.get_event_loop().run_until_complete(
          _run_parse(
              file_path=file_path,
              adapter_name=adapter_name,
              job_id=job_id,
              session_id=session_id,
              benchmark=benchmark,
              model=model,
              model_version=model_version,
          )
      )
  ```

  Run: `cd backend && pytest tests/ingestion/test_celery_task.py::test_parse_file_task_is_registered -x`
  Expected: `1 passed`

- [ ] **7.3 Commit**

  ```bash
  git add backend/app/tasks/ backend/tests/ingestion/test_celery_task.py
  git commit -m "feat(ingestion): add Celery task parse_file with streaming pipeline"
  ```

---

### TASK 8 — WebSocket progress endpoint

- [ ] **8.1 Write failing test**

  File: `backend/tests/api/test_ws_progress.py` (Create)

  ```python
  import pytest
  import orjson
  from unittest.mock import AsyncMock, patch

  @pytest.mark.asyncio
  async def test_ws_progress_streams_events(async_client):
      """Connect to WS, receive a progress event published to Redis."""
      job_id = "ws-test-job-1"

      # We'll use the ASGI WebSocket test client
      async with async_client.websocket_connect(
          f"/api/v1/ws/progress?job_id={job_id}"
      ) as ws:
          # Simulate a Redis publish from another coroutine
          # In tests we rely on the fact that the endpoint subscribes,
          # then we inject a message via the mock pubsub.
          message = await ws.receive_json(timeout=2)
          # Connection established event
          assert message["status"] in ("connected", "running", "done")

  @pytest.mark.asyncio
  async def test_ws_progress_missing_job_id_closes_with_error(async_client):
      """WebSocket without job_id param should close immediately."""
      with pytest.raises(Exception):
          async with async_client.websocket_connect("/api/v1/ws/progress") as ws:
              msg = await ws.receive_json(timeout=2)
              assert msg.get("error") is not None
  ```

  Note: `async_client` is the fixture from Plan 1's `tests/conftest.py`. Full integration test of pub/sub relay requires a live Redis in CI; unit testing the router function is shown below.

  File: `backend/tests/api/test_ws_progress_unit.py` (Create)

  ```python
  import pytest
  import orjson
  from unittest.mock import AsyncMock, MagicMock, patch
  from fastapi.testclient import TestClient
  from fastapi import FastAPI
  from fastapi.websockets import WebSocket

  @pytest.mark.asyncio
  async def test_progress_router_relays_redis_message():
      """Unit test: verify the router reads from pubsub and forwards to WS."""
      from app.api.v1.ws_progress import relay_progress

      mock_ws = AsyncMock(spec=WebSocket)
      mock_ws.accept = AsyncMock()
      mock_ws.send_text = AsyncMock()
      mock_ws.receive_text = AsyncMock(side_effect=Exception("disconnect"))

      fake_message = {"type": "message", "data": orjson.dumps({"processed": 100, "status": "running"})}

      mock_pubsub = AsyncMock()
      mock_pubsub.subscribe = AsyncMock()
      mock_pubsub.listen = AsyncMock(return_value=_async_gen([fake_message]))
      mock_pubsub.unsubscribe = AsyncMock()

      mock_redis = AsyncMock()
      mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

      with patch("app.api.v1.ws_progress.get_redis", AsyncMock(return_value=mock_redis)):
          await relay_progress(mock_ws, job_id="test-job")

      mock_ws.send_text.assert_called_once()
      sent = orjson.loads(mock_ws.send_text.call_args[0][0])
      assert sent["processed"] == 100

  async def _async_gen(items):
      for item in items:
          yield item
  ```

  Run: `cd backend && pytest tests/api/test_ws_progress_unit.py -x`
  Expected: `FAILED` (ImportError)

- [ ] **8.2 Implement WebSocket router**

  File: `backend/app/api/v1/ws_progress.py` (Create)

  ```python
  from __future__ import annotations
  import logging
  import orjson
  from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
  from starlette.websockets import WebSocketState

  from app.core.redis import get_redis

  logger = logging.getLogger(__name__)
  router = APIRouter()

  _PROGRESS_CHANNEL_PREFIX = "progress"


  async def relay_progress(websocket: WebSocket, job_id: str) -> None:
      """Subscribe to Redis channel and relay messages to WebSocket client."""
      await websocket.accept()
      redis = await get_redis()
      pubsub = redis.pubsub()
      channel = f"{_PROGRESS_CHANNEL_PREFIX}:{job_id}"

      try:
          await pubsub.subscribe(channel)
          await websocket.send_text(
              orjson.dumps({"status": "connected", "job_id": job_id}).decode()
          )
          async for message in pubsub.listen():
              if message["type"] != "message":
                  continue
              data = message["data"]
              if isinstance(data, bytes):
                  data = data.decode()
              await websocket.send_text(data)
              # Check if job is done or failed — close gracefully
              try:
                  parsed = orjson.loads(data)
                  if parsed.get("status") in ("done", "failed"):
                      break
              except Exception:
                  pass
      except WebSocketDisconnect:
          logger.debug("WS client disconnected for job %s", job_id)
      except Exception as exc:
          logger.exception("WS relay error for job %s: %s", job_id, exc)
          if websocket.client_state == WebSocketState.CONNECTED:
              await websocket.send_text(
                  orjson.dumps({"status": "error", "reason": str(exc)}).decode()
              )
      finally:
          await pubsub.unsubscribe(channel)
          if websocket.client_state == WebSocketState.CONNECTED:
              await websocket.close()


  @router.websocket("/ws/progress")
  async def ws_progress_endpoint(
      websocket: WebSocket,
      job_id: str = Query(..., description="Ingest or analysis job ID to subscribe to"),
  ) -> None:
      """
      WebSocket: WS /api/v1/ws/progress?job_id=<id>

      Streams real-time progress events for an ingest or LLM analysis job.
      Closes automatically when status becomes 'done' or 'failed'.
      """
      await relay_progress(websocket, job_id=job_id)
  ```

  File: `backend/app/api/v1/__init__.py` (Modify — add ws_progress router)

  In the existing `api_router` setup (from Plan 1), include:
  ```python
  from app.api.v1 import ws_progress
  api_router.include_router(ws_progress.router, tags=["realtime"])
  ```

  Run: `cd backend && pytest tests/api/test_ws_progress_unit.py -x`
  Expected: `1 passed`

- [ ] **8.3 Commit**

  ```bash
  git add backend/app/api/v1/ws_progress.py backend/tests/api/
  git commit -m "feat(ingestion): add WebSocket /api/v1/ws/progress progress relay"
  ```

---

### TASK 9 — Ingest job model + REST endpoints

- [ ] **9.1 Write failing test**

  File: `backend/tests/api/test_ingest_endpoints.py` (Create)

  ```python
  import pytest
  import io
  import json
  from unittest.mock import patch, MagicMock, AsyncMock

  @pytest.mark.asyncio
  async def test_upload_returns_job_id(async_client):
      content = b'{"question_id":"q1","question":"x","expected_answer":"a","model_answer":"b","is_correct":false}\n'
      
      with patch("app.api.v1.ingest.parse_file") as mock_task, \
           patch("app.api.v1.ingest.save_upload_file", return_value="/tmp/upload/test.jsonl"):
          mock_task.delay.return_value = MagicMock(id="celery-task-1")
          
          resp = await async_client.post(
              "/api/v1/ingest/upload",
              files={"file": ("test.jsonl", io.BytesIO(content), "application/octet-stream")},
              data={
                  "benchmark": "generic",
                  "model": "test-model",
                  "model_version": "v1",
              },
          )
      
      assert resp.status_code == 202
      body = resp.json()
      assert "job_id" in body
      assert "session_id" in body

  @pytest.mark.asyncio
  async def test_upload_rejects_non_json_file(async_client):
      content = b"this is not json at all"
      resp = await async_client.post(
          "/api/v1/ingest/upload",
          files={"file": ("data.csv", io.BytesIO(content), "text/csv")},
          data={"benchmark": "generic", "model": "m", "model_version": "v"},
      )
      assert resp.status_code == 422

  @pytest.mark.asyncio
  async def test_job_status_returns_progress(async_client):
      with patch("app.api.v1.ingest.get_job_status", return_value={
          "job_id": "job-123",
          "status": "running",
          "processed": 500,
          "total": 1000,
      }):
          resp = await async_client.get("/api/v1/ingest/job-123/status")
      
      assert resp.status_code == 200
      body = resp.json()
      assert body["status"] == "running"

  @pytest.mark.asyncio
  async def test_job_status_404_for_unknown_job(async_client):
      with patch("app.api.v1.ingest.get_job_status", return_value=None):
          resp = await async_client.get("/api/v1/ingest/unknown-job/status")
      assert resp.status_code == 404

  @pytest.mark.asyncio
  async def test_directory_ingest_queues_multiple_jobs(async_client, tmp_path):
      # Create two jsonl files
      for i in range(2):
          f = tmp_path / f"file{i}.jsonl"
          f.write_text('{"question_id":"q1","question":"x","expected_answer":"a","model_answer":"b","is_correct":false}\n')
      
      with patch("app.api.v1.ingest.parse_file") as mock_task:
          mock_task.delay.return_value = MagicMock(id="celery-task-x")
          resp = await async_client.post(
              "/api/v1/ingest/directory",
              json={
                  "directory_path": str(tmp_path),
                  "benchmark": "generic",
                  "model": "test-model",
                  "model_version": "v1",
              },
          )
      
      assert resp.status_code == 202
      body = resp.json()
      assert len(body["jobs"]) == 2
  ```

  Run: `cd backend && pytest tests/api/test_ingest_endpoints.py -x`
  Expected: `FAILED` (ImportError/404)

- [ ] **9.2 Add IngestJob model (Redis-backed status store)**

  File: `backend/app/ingestion/job_store.py` (Create)

  ```python
  """
  Lightweight job status store backed by Redis hashes.
  Keys expire after 24h to avoid Redis bloat.
  """
  from __future__ import annotations
  import time
  import orjson
  from typing import Literal

  _JOB_TTL_SECONDS = 86_400  # 24 hours
  _KEY_PREFIX = "ingest_job"


  def _key(job_id: str) -> str:
      return f"{_KEY_PREFIX}:{job_id}"


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
      raw = await redis.get(_key(job_id))
      if raw is None:
          return None
      return orjson.loads(raw)


  async def update_job_from_event(redis, job_id: str, event: dict) -> None:
      """Merge a progress event dict into the stored job status."""
      raw = await redis.get(_key(job_id))
      if raw is None:
          return
      current = orjson.loads(raw)
      current.update({k: v for k, v in event.items() if k in (
          "status", "processed", "total", "total_written", "total_skipped", "reason"
      )})
      await redis.set(_key(job_id), orjson.dumps(current), ex=_JOB_TTL_SECONDS)
  ```

- [ ] **9.3 Implement ingest router**

  File: `backend/app/api/v1/ingest.py` (Create)

  ```python
  from __future__ import annotations
  import uuid
  import logging
  from pathlib import Path
  from typing import Annotated

  import aiofiles
  import aiofiles.os
  from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
  from pydantic import BaseModel

  from app.core.config import settings
  from app.core.redis import get_redis
  from app.ingestion.job_store import create_job, get_job_status
  from app.tasks.ingest import parse_file

  logger = logging.getLogger(__name__)
  router = APIRouter(prefix="/ingest", tags=["ingestion"])

  _ALLOWED_EXTENSIONS = {".jsonl", ".json"}
  _UPLOAD_DIR = Path(settings.UPLOAD_DIR)  # e.g. /tmp/fla_uploads


  async def save_upload_file(upload: UploadFile, dest_dir: Path) -> str:
      dest_dir.mkdir(parents=True, exist_ok=True)
      dest = dest_dir / upload.filename
      async with aiofiles.open(dest, "wb") as out:
          while chunk := await upload.read(1024 * 1024):  # 1 MB chunks
              await out.write(chunk)
      return str(dest)


  class UploadResponse(BaseModel):
      job_id: str
      session_id: str
      message: str


  class DirectoryRequest(BaseModel):
      directory_path: str
      benchmark: str
      model: str
      model_version: str
      adapter_name: str | None = None
      session_id: str | None = None


  class DirectoryResponse(BaseModel):
      session_id: str
      jobs: list[dict]


  @router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
  async def upload_file(
      file: Annotated[UploadFile, File()],
      benchmark: Annotated[str, Form()],
      model: Annotated[str, Form()],
      model_version: Annotated[str, Form()],
      adapter_name: Annotated[str | None, Form()] = None,
      session_id: Annotated[str | None, Form()] = None,
  ) -> UploadResponse:
      """
      POST /api/v1/ingest/upload
      Upload a single .json or .jsonl file for ingestion.
      Returns job_id for progress tracking via WS /api/v1/ws/progress?job_id=<id>.
      """
      suffix = Path(file.filename or "").suffix.lower()
      if suffix not in _ALLOWED_EXTENSIONS:
          raise HTTPException(
              status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
              detail=f"File must be .json or .jsonl, got {suffix!r}",
          )

      job_id = str(uuid.uuid4())
      resolved_session_id = session_id or str(uuid.uuid4())

      file_path = await save_upload_file(file, _UPLOAD_DIR / resolved_session_id)

      redis = await get_redis()
      await create_job(
          redis, job_id=job_id, session_id=resolved_session_id, file_path=file_path
      )

      parse_file.delay(
          file_path,
          adapter_name=adapter_name,
          job_id=job_id,
          session_id=resolved_session_id,
          benchmark=benchmark,
          model=model,
          model_version=model_version,
      )

      return UploadResponse(
          job_id=job_id,
          session_id=resolved_session_id,
          message="Ingestion job queued",
      )


  @router.post("/directory", response_model=DirectoryResponse, status_code=status.HTTP_202_ACCEPTED)
  async def ingest_directory(body: DirectoryRequest) -> DirectoryResponse:
      """
      POST /api/v1/ingest/directory
      Scan a server-side directory and queue one Celery task per .json/.jsonl file.
      """
      dir_path = Path(body.directory_path)
      if not dir_path.is_dir():
          raise HTTPException(
              status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
              detail=f"Not a directory: {body.directory_path}",
          )

      files = [
          f for f in dir_path.iterdir()
          if f.suffix.lower() in _ALLOWED_EXTENSIONS
      ]
      if not files:
          raise HTTPException(
              status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
              detail="No .json or .jsonl files found in directory",
          )

      session_id = body.session_id or str(uuid.uuid4())
      redis = await get_redis()
      jobs = []

      for file_path in files:
          job_id = str(uuid.uuid4())
          await create_job(
              redis, job_id=job_id, session_id=session_id, file_path=str(file_path)
          )
          parse_file.delay(
              str(file_path),
              adapter_name=body.adapter_name,
              job_id=job_id,
              session_id=session_id,
              benchmark=body.benchmark,
              model=body.model,
              model_version=body.model_version,
          )
          jobs.append({"job_id": job_id, "file": file_path.name})

      return DirectoryResponse(session_id=session_id, jobs=jobs)


  @router.get("/{job_id}/status")
  async def get_ingest_status(job_id: str) -> dict:
      """
      GET /api/v1/ingest/{job_id}/status
      Poll ingestion job status (alternative to WebSocket).
      """
      redis = await get_redis()
      job = await get_job_status(redis, job_id)
      if job is None:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"Job {job_id!r} not found",
          )
      return job
  ```

  Register the router in `backend/app/api/v1/__init__.py` (Modify):
  ```python
  from app.api.v1 import ingest
  api_router.include_router(ingest.router)
  ```

  Run: `cd backend && pytest tests/api/test_ingest_endpoints.py -x`
  Expected: `5 passed`

- [ ] **9.4 Commit**

  ```bash
  git add backend/app/api/v1/ingest.py backend/app/ingestion/job_store.py backend/tests/api/test_ingest_endpoints.py
  git commit -m "feat(ingestion): add REST endpoints POST /upload, POST /directory, GET /{job_id}/status"
  ```

---

### TASK 10 — Wire adapters auto-import + update `requirements.txt`

- [ ] **10.1 Ensure adapters are imported at app startup**

  File: `backend/app/ingestion/adapters/__init__.py` (Modify)

  ```python
  # Auto-import all adapters so their @register_adapter decorators execute
  from app.ingestion.adapters import generic_jsonl  # noqa: F401
  ```

  File: `backend/app/main.py` (Modify — add import in startup)

  In the FastAPI lifespan or at module level, add:
  ```python
  import app.ingestion.adapters  # noqa: F401 — triggers adapter registration
  ```

- [ ] **10.2 Update dependencies**

  File: `backend/requirements.txt` (Modify — add if not present)

  ```
  ijson>=3.2.3
  orjson>=3.9.0
  chardet>=5.2.0
  aiofiles>=23.2.1
  celery[redis]>=5.3.0
  ```

  File: `backend/requirements-test.txt` (Modify — add if not present)

  ```
  pytest-asyncio>=0.23.0
  httpx>=0.27.0
  ```

- [ ] **10.3 Verify all tests pass**

  ```bash
  cd backend && pytest tests/ingestion/ tests/api/test_ws_progress_unit.py tests/api/test_ingest_endpoints.py -v
  ```

  Expected output (all green):
  ```
  tests/ingestion/test_normalized_record.py::test_required_fields_present PASSED
  tests/ingestion/test_normalized_record.py::test_is_correct_required PASSED
  tests/ingestion/test_normalized_record.py::test_sha256_computed_from_session_and_question_id PASSED
  tests/ingestion/test_adapter_registry.py::test_register_and_retrieve PASSED
  tests/ingestion/test_adapter_registry.py::test_unknown_adapter_returns_none PASSED
  tests/ingestion/test_adapter_registry.py::test_auto_detect_returns_highest_confidence PASSED
  tests/ingestion/test_generic_jsonl_adapter.py::test_detect_high_confidence_with_is_correct PASSED
  tests/ingestion/test_generic_jsonl_adapter.py::test_detect_low_confidence_without_is_correct PASSED
  tests/ingestion/test_generic_jsonl_adapter.py::test_normalize_minimal_record PASSED
  tests/ingestion/test_generic_jsonl_adapter.py::test_normalize_skips_correct_when_errors_only_false PASSED
  tests/ingestion/test_generic_jsonl_adapter.py::test_normalize_captures_extra_fields_in_metadata PASSED
  tests/ingestion/test_parsers.py::test_parse_jsonl_yields_all_records PASSED
  tests/ingestion/test_parsers.py::test_parse_jsonl_skips_blank_lines PASSED
  tests/ingestion/test_parsers.py::test_parse_jsonl_skips_corrupt_lines PASSED
  tests/ingestion/test_parsers.py::test_parse_large_json_yields_all_items PASSED
  tests/ingestion/test_db_writer.py::test_batch_writer_flushes_at_batch_size PASSED
  tests/ingestion/test_db_writer.py::test_batch_writer_final_flush PASSED
  tests/ingestion/test_db_writer.py::test_batch_writer_dedup_skips_seen_hash PASSED
  tests/ingestion/test_progress.py::test_publish_sends_to_redis_channel PASSED
  tests/ingestion/test_progress.py::test_publish_complete_sets_status_done PASSED
  tests/ingestion/test_progress.py::test_publish_error_sets_status_failed PASSED
  tests/ingestion/test_celery_task.py::test_parse_file_task_is_registered PASSED
  tests/api/test_ws_progress_unit.py::test_progress_router_relays_redis_message PASSED
  tests/api/test_ingest_endpoints.py::test_upload_returns_job_id PASSED
  tests/api/test_ingest_endpoints.py::test_upload_rejects_non_json_file PASSED
  tests/api/test_ingest_endpoints.py::test_job_status_returns_progress PASSED
  tests/api/test_ingest_endpoints.py::test_job_status_404_for_unknown_job PASSED
  tests/api/test_ingest_endpoints.py::test_directory_ingest_queues_multiple_jobs PASSED
  28 passed
  ```

- [ ] **10.4 Final commit**

  ```bash
  git add backend/app/ingestion/adapters/__init__.py backend/app/main.py backend/requirements.txt backend/requirements-test.txt
  git commit -m "feat(ingestion): wire adapter auto-import and update dependencies"
  ```

---

### TASK 11 — Watchdog directory watcher (production auto-ingest)

Design doc §4.3 specifies a watchdog-based directory watcher for production environments: configure a watch directory, detect new `.json`/`.jsonl` files, and automatically trigger the ingestion pipeline.

- [ ] **11.1 Write failing test**

  File: `backend/tests/ingestion/test_directory_watcher.py` (Create)

  ```python
  import pytest
  import time
  from pathlib import Path
  from unittest.mock import patch, MagicMock, AsyncMock, call

  from app.ingestion.directory_watcher import DirectoryWatcher, IngestFileHandler


  def test_handler_triggers_on_new_jsonl_file(tmp_path):
      """FileSystemEventHandler should dispatch a Celery task for new .jsonl files."""
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
      """Handler should ignore .csv, .txt, and other non-JSON files."""
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
      """Handler should also accept .json files."""
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
      """Same file created twice within debounce window should dispatch only once."""
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
      handler.on_created(event)  # duplicate within debounce window

      assert mock_task.call_count == 1


  def test_watcher_creates_directory_if_missing(tmp_path):
      """DirectoryWatcher should create the watch directory if it doesn't exist."""
      watch_dir = tmp_path / "nonexistent" / "subdir"
      watcher = DirectoryWatcher(
          watch_dir=str(watch_dir),
          benchmark="auto",
          model="unknown",
          model_version="unknown",
      )
      assert watch_dir.exists()


  def test_watcher_start_stop(tmp_path):
      """Watcher should start and stop without errors."""
      watcher = DirectoryWatcher(
          watch_dir=str(tmp_path),
          benchmark="auto",
          model="unknown",
          model_version="unknown",
      )
      watcher.start()
      assert watcher.is_running
      watcher.stop()
      assert not watcher.is_running
  ```

  Run: `cd backend && pytest tests/ingestion/test_directory_watcher.py -x`
  Expected: `FAILED` (ImportError — module does not exist yet)

- [ ] **11.2 Implement DirectoryWatcher + IngestFileHandler**

  File: `backend/app/ingestion/directory_watcher.py` (Create)

  ```python
  from __future__ import annotations
  import logging
  import time
  import uuid
  from pathlib import Path
  from threading import Lock

  from watchdog.observers import Observer
  from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

  logger = logging.getLogger(__name__)

  _ALLOWED_EXTENSIONS = {".jsonl", ".json"}
  _DEFAULT_DEBOUNCE_SECONDS = 5.0


  class IngestFileHandler(FileSystemEventHandler):
      """
      Watchdog event handler that dispatches a Celery ingest task
      when a new .json/.jsonl file appears in the watched directory.

      Features:
      - Filters by file extension (.json, .jsonl only)
      - Debounces rapid duplicate events for the same file path
      - Generates a unique session_id per file (or groups by parent dir)
      """

      def __init__(
          self,
          dispatch_fn,
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
          self._seen: dict[str, float] = {}  # file_path -> last_dispatch_time
          self._lock = Lock()

      def _should_process(self, file_path: str) -> bool:
          suffix = Path(file_path).suffix.lower()
          if suffix not in _ALLOWED_EXTENSIONS:
              return False
          # Debounce: skip if same path was dispatched recently
          now = time.monotonic()
          with self._lock:
              last = self._seen.get(file_path, 0.0)
              if now - last < self._debounce_seconds:
                  logger.debug("Debounced duplicate event for %s", file_path)
                  return False
              self._seen[file_path] = now
          return True

      def _dispatch(self, file_path: str) -> None:
          job_id = str(uuid.uuid4())
          session_id = str(uuid.uuid4())
          logger.info(
              "Watchdog detected new file: %s → dispatching job %s",
              file_path, job_id,
          )
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
          """Handle files moved/renamed into the watched directory."""
          if event.is_directory:
              return
          if self._should_process(event.dest_path):
              self._dispatch(event.dest_path)


  class DirectoryWatcher:
      """
      Manages a watchdog Observer that monitors a directory for new eval log files.

      Usage:
          watcher = DirectoryWatcher(
              watch_dir="/data/eval-logs",
              benchmark="auto",
              model="unknown",
              model_version="unknown",
          )
          watcher.start()
          # ... runs in background thread ...
          watcher.stop()

      In production, start this from a dedicated CLI command or Celery beat schedule.
      """

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

          # Default dispatch function is the Celery task;
          # inject a different one for testing.
          self._dispatch_fn = self._default_dispatch

          self._handler = IngestFileHandler(
              dispatch_fn=self._dispatch_fn,
              benchmark=benchmark,
              model=model,
              model_version=model_version,
              adapter_name=adapter_name,
              debounce_seconds=debounce_seconds,
          )
          self._observer = Observer()
          self._running = False

      @staticmethod
      def _default_dispatch(file_path: str, **kwargs) -> None:
          """Dispatch via Celery task. Import here to avoid circular imports."""
          from app.tasks.ingest import parse_file
          parse_file.delay(file_path, **kwargs)

      @property
      def is_running(self) -> bool:
          return self._running

      def start(self) -> None:
          if self._running:
              return
          self._observer.schedule(
              self._handler,
              str(self._watch_dir),
              recursive=self._recursive,
          )
          self._observer.start()
          self._running = True
          logger.info("DirectoryWatcher started: watching %s", self._watch_dir)

      def stop(self) -> None:
          if not self._running:
              return
          self._observer.stop()
          self._observer.join(timeout=10)
          self._running = False
          logger.info("DirectoryWatcher stopped")
  ```

  Run: `cd backend && pytest tests/ingestion/test_directory_watcher.py -x`
  Expected: `6 passed`

- [ ] **11.3 Add CLI command to start watcher**

  File: `backend/app/cli/watch.py` (Create)

  ```python
  """
  CLI entrypoint to run the directory watcher as a long-lived process.

  Usage:
      python -m app.cli.watch --dir /data/eval-logs --benchmark auto
  """
  from __future__ import annotations
  import argparse
  import logging
  import signal
  import sys

  from app.ingestion.directory_watcher import DirectoryWatcher

  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s %(levelname)s %(name)s — %(message)s",
  )
  logger = logging.getLogger(__name__)


  def main() -> None:
      parser = argparse.ArgumentParser(description="Watch a directory for new eval log files")
      parser.add_argument("--dir", required=True, help="Directory to watch")
      parser.add_argument("--benchmark", default="auto", help="Benchmark name (default: auto)")
      parser.add_argument("--model", default="unknown", help="Model identifier")
      parser.add_argument("--model-version", default="unknown", help="Model version")
      parser.add_argument("--adapter", default=None, help="Adapter name (default: auto-detect)")
      parser.add_argument("--no-recursive", action="store_true", help="Don't watch subdirectories")
      args = parser.parse_args()

      watcher = DirectoryWatcher(
          watch_dir=args.dir,
          benchmark=args.benchmark,
          model=args.model,
          model_version=args.model_version,
          adapter_name=args.adapter,
          recursive=not args.no_recursive,
      )

      def _shutdown(signum, frame):
          logger.info("Received signal %s, shutting down watcher...", signum)
          watcher.stop()
          sys.exit(0)

      signal.signal(signal.SIGINT, _shutdown)
      signal.signal(signal.SIGTERM, _shutdown)

      watcher.start()
      logger.info("Watcher running. Press Ctrl+C to stop.")

      # Block main thread — Observer runs in a daemon thread
      signal.pause()


  if __name__ == "__main__":
      main()
  ```

  File: `backend/app/cli/__init__.py` (Create — empty)

- [ ] **11.4 Add REST endpoint for watcher management**

  File: `backend/app/api/v1/ingest.py` (Modify — add watcher status/control endpoints)

  Add to the existing ingest router:

  ```python
  # --- Directory Watcher management (optional, for Dashboard control) ---

  _active_watcher: DirectoryWatcher | None = None


  class WatcherStartRequest(BaseModel):
      watch_dir: str
      benchmark: str = "auto"
      model: str = "unknown"
      model_version: str = "unknown"
      adapter_name: str | None = None
      recursive: bool = True


  class WatcherStatusResponse(BaseModel):
      running: bool
      watch_dir: str | None = None


  @router.post("/watcher/start", response_model=WatcherStatusResponse)
  async def start_watcher(body: WatcherStartRequest) -> WatcherStatusResponse:
      """Start the directory watcher. Only one watcher instance per API process."""
      global _active_watcher
      if _active_watcher and _active_watcher.is_running:
          raise HTTPException(
              status_code=status.HTTP_409_CONFLICT,
              detail="Watcher is already running",
          )

      from app.ingestion.directory_watcher import DirectoryWatcher
      _active_watcher = DirectoryWatcher(
          watch_dir=body.watch_dir,
          benchmark=body.benchmark,
          model=body.model,
          model_version=body.model_version,
          adapter_name=body.adapter_name,
          recursive=body.recursive,
      )
      _active_watcher.start()
      return WatcherStatusResponse(running=True, watch_dir=body.watch_dir)


  @router.post("/watcher/stop", response_model=WatcherStatusResponse)
  async def stop_watcher() -> WatcherStatusResponse:
      """Stop the directory watcher."""
      global _active_watcher
      if not _active_watcher or not _active_watcher.is_running:
          raise HTTPException(
              status_code=status.HTTP_409_CONFLICT,
              detail="No watcher is running",
          )
      _active_watcher.stop()
      _active_watcher = None
      return WatcherStatusResponse(running=False)


  @router.get("/watcher/status", response_model=WatcherStatusResponse)
  async def watcher_status() -> WatcherStatusResponse:
      """Check if the directory watcher is running."""
      if _active_watcher and _active_watcher.is_running:
          return WatcherStatusResponse(running=True, watch_dir=str(_active_watcher._watch_dir))
      return WatcherStatusResponse(running=False)
  ```

- [ ] **11.5 Update dependencies**

  File: `backend/requirements.txt` (Modify — add if not present)

  ```
  watchdog>=4.0.0
  ```

- [ ] **11.6 Commit**

  ```bash
  git add backend/app/ingestion/directory_watcher.py backend/app/cli/ backend/tests/ingestion/test_directory_watcher.py
  git commit -m "feat(ingestion): add watchdog directory watcher for production auto-ingest"
  ```

---

## Architecture Notes

### File Layout (new files in this plan)

```
backend/
  app/
    ingestion/
      __init__.py
      schemas.py          # NormalizedRecord
      parsers.py          # parse_jsonl, parse_large_json
      db_writer.py        # BatchWriter (1000-record batches)
      progress.py         # ProgressPublisher -> Redis pub/sub
      job_store.py        # Redis-backed job status (TTL 24h)
      directory_watcher.py  # Watchdog-based directory monitoring for auto-ingest
      adapters/
        __init__.py       # auto-imports all adapters
        base.py           # BaseAdapter ABC
        registry.py       # @register_adapter, get_adapter, auto_detect_adapter
        generic_jsonl.py  # example adapter
    cli/
      __init__.py
      watch.py            # CLI entrypoint: python -m app.cli.watch --dir /data/eval-logs
    tasks/
      __init__.py
      ingest.py           # @shared_task parse_file
    api/
      v1/
        ingest.py         # POST /upload, POST /directory, GET /{job_id}/status
        ws_progress.py    # WS /ws/progress
  alembic/
    versions/
      002_add_dedup_hash_to_eval_records.py
  tests/
    ingestion/
      test_normalized_record.py
      test_adapter_registry.py
      test_generic_jsonl_adapter.py
      test_parsers.py
      test_db_writer.py
      test_progress.py
      test_celery_task.py
      test_directory_watcher.py
    api/
      test_ws_progress_unit.py
      test_ingest_endpoints.py
```

### Key Design Decisions

1. **Adapter `normalize()` signature**: `GenericJsonlAdapter.normalize(raw, *, session_id, benchmark, model, model_version)` uses keyword-only args for context. This deviates from `BaseAdapter`'s abstract signature intentionally — the streaming pipeline always calls `adapter.normalize(raw, **ctx)`. Future adapters must follow this convention.

2. **Dedup scope**: `BatchWriter._seen_hashes` is per-task (per-file-per-run). Cross-run dedup is enforced by the PostgreSQL unique constraint on `dedup_hash`. Same-session re-upload of the same file is therefore safely skipped by the DB's `ON CONFLICT DO NOTHING`.

3. **Event loop in Celery**: `asyncio.get_event_loop().run_until_complete(...)` is used because Celery workers are synchronous by default. For Python 3.10+ this is `asyncio.run(...)` when no loop exists. Plan uses `run_until_complete` for compatibility; swap to `asyncio.run` if Celery worker is started fresh per task.

4. **Progress granularity**: Events are published every 500 records (`_PROGRESS_EVERY_N`). At 10,000 rps this means one Redis publish per 50ms — negligible overhead.

5. **Memory bound**: `BatchWriter._buffer` holds at most 1000 `NormalizedRecord` objects (~2 KB each) = ~2 MB. `_seen_hashes` holds SHA-256 hex strings (64 bytes each); 1 million unique records = ~64 MB. Total well within 256 MB limit.

6. **Watchdog directory watcher**: Runs as a separate long-lived process (CLI command or managed by the API). Uses `watchdog.Observer` in a background thread. File events are debounced (default 5s) to avoid duplicate dispatches from editors or partial writes. Each detected file gets its own `session_id` and `job_id`, dispatching to the same `parse_file` Celery task used by the REST endpoints. Supports `on_created` and `on_moved` events (covers both new files and files moved into the directory).

---

## Critical Files for Implementation

- `backend/app/ingestion/schemas.py` — Core `NormalizedRecord` dataclass; dedup hash logic; the contract between all adapters and the DB writer
- `backend/app/ingestion/adapters/registry.py` — The `@register_adapter` plugin mechanism; `auto_detect_adapter`; all future adapters depend on this
- `backend/app/ingestion/parsers.py` — O(1) streaming parsers using `readline` and `ijson`; encoding detection via `chardet`; this is the memory-critical path
- `backend/app/tasks/ingest.py` — Celery task wiring everything together: parser → adapter.normalize → BatchWriter → ProgressPublisher; entrypoint for all ingest operations
- `backend/app/api/v1/ingest.py` — REST layer: file upload, directory scan, job status polling, watcher management; integrates with Celery `.delay()` and Redis job store
- `backend/app/ingestion/directory_watcher.py` — Watchdog-based directory watcher: `IngestFileHandler` (event filtering + debounce) + `DirectoryWatcher` (Observer lifecycle); dispatches to the same `parse_file` Celery task
- `backend/app/cli/watch.py` — CLI entrypoint for running the watcher as a standalone process with signal handling
