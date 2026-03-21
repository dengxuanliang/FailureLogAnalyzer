"""Record selection utilities for LLM judge strategies."""
from __future__ import annotations

import random
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import StrategyType
from app.db.models.eval_record import EvalRecord


def _select_from_candidates(
    records: Sequence[EvalRecord],
    *,
    strategy_type: StrategyType,
    config: dict | None,
    manual_record_ids: Sequence[uuid.UUID],
    ruled_record_ids: set[uuid.UUID],
) -> list[EvalRecord]:
    """Apply strategy rules to in-memory candidates."""

    config = config or {}
    manual_id_set = set(manual_record_ids)

    if strategy_type == StrategyType.full:
        return list(records)

    if strategy_type == StrategyType.fallback:
        return [record for record in records if record.id not in ruled_record_ids]

    if strategy_type == StrategyType.manual:
        if not manual_id_set:
            return []
        return [record for record in records if record.id in manual_id_set]

    # sample strategy
    filtered = list(records)
    categories = config.get("categories") or []
    if categories:
        category_set = set(str(cat) for cat in categories)
        filtered = [record for record in filtered if (record.task_category or "") in category_set]

    if not filtered:
        return []

    sample_size = config.get("sample_size")
    sample_rate = config.get("sample_rate")

    if sample_size is None:
        if sample_rate is None:
            sample_size = min(100, len(filtered))
        else:
            sample_rate = float(sample_rate)
            if sample_rate <= 0:
                return []
            sample_size = int(round(len(filtered) * min(sample_rate, 1.0)))

    sample_size = max(0, min(int(sample_size), len(filtered)))
    if sample_size == 0:
        return []

    seed = config.get("seed")
    rng = random.Random(seed)
    return rng.sample(filtered, sample_size)


async def select_records(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    strategy_type: StrategyType,
    config: dict | None,
    manual_record_ids: Sequence[uuid.UUID],
    ruled_record_ids: set[uuid.UUID],
) -> list[EvalRecord]:
    """Select records for LLM judging from a session."""

    stmt = (
        select(EvalRecord)
        .where(EvalRecord.session_id == session_id)
        .where(EvalRecord.is_correct.is_(False))
        .order_by(EvalRecord.id)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return _select_from_candidates(
        records,
        strategy_type=strategy_type,
        config=config,
        manual_record_ids=manual_record_ids,
        ruled_record_ids=ruled_record_ids,
    )
