from __future__ import annotations

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.eval_session import EvalSession


async def ensure_eval_session(
    *,
    session: AsyncSession,
    session_id: str | UUID,
    benchmark: str,
    model: str,
    model_version: str,
) -> None:
    """Create eval_sessions row if missing (idempotent)."""
    normalized_session_id = session_id if isinstance(session_id, UUID) else UUID(session_id)
    stmt = (
        pg_insert(EvalSession.__table__)
        .values(
            id=normalized_session_id,
            benchmark=benchmark,
            model=model,
            model_version=model_version,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(stmt)
    await session.commit()
