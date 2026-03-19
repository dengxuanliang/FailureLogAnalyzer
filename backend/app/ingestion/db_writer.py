from __future__ import annotations
import logging
import orjson
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.ingestion.schemas import NormalizedRecord
from app.db.models.eval_record import EvalRecord  # ORM model from Plan 1

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


class DuplicateSkippedError(Exception):
    pass


class BatchWriter:
    """
    Buffers NormalizedRecord objects and flushes to PostgreSQL in batches.
    Deduplication is performed in-memory (per-file) via SHA-256 dedup_hash.
    On-disk dedup (cross-upload) is handled by a unique index on eval_records.dedup_hash.

    Counters:
      total_written  — unique records accepted (not in-memory deduped); may still be DB-deduped
      total_skipped  — records dropped (in-memory dedup + DB ON CONFLICT DO NOTHING)
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
        """Add a record; skip in-memory duplicates immediately."""
        if record.dedup_hash in self._seen_hashes:
            self.total_skipped += 1
            return
        self._seen_hashes.add(record.dedup_hash)
        self._buffer.append(record)
        self.total_written += 1  # Counts unique records accepted into the pipeline
        if len(self._buffer) >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Write buffered records to PostgreSQL using ON CONFLICT DO NOTHING."""
        if not self._buffer:
            return
        # Note: `record.model` is stored in EvalSession, not in EvalRecord rows
        rows = [
            {
                "session_id": r.session_id,
                "benchmark": r.benchmark,
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
        # Use the Core Table object to avoid ORM metadata name collision
        stmt = pg_insert(EvalRecord.__table__).values(rows).on_conflict_do_nothing(
            index_elements=["dedup_hash"]
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        # rowcount may be -1 in some backends (e.g. when using ON CONFLICT DO NOTHING)
        # or a mock in tests
        db_skipped = 0
        try:
            rc = int(result.rowcount)
            if rc >= 0:
                db_skipped = len(rows) - rc
                self.total_skipped += db_skipped
        except (TypeError, ValueError):
            pass  # Mock or unknown rowcount — don't adjust skipped count
        self.flush_count += 1
        logger.debug(
            "BatchWriter flushed %d rows (skipped %d duplicates in DB)",
            len(rows) - db_skipped, db_skipped,
        )
        self._buffer.clear()

    async def __aenter__(self) -> BatchWriter:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            await self.flush()
