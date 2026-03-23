import uuid
import pytest
from unittest.mock import AsyncMock

from app.ingestion.session_store import ensure_eval_session


@pytest.mark.asyncio
async def test_ensure_eval_session_accepts_uuid_instance():
    db_session = AsyncMock()
    session_id = uuid.uuid4()

    await ensure_eval_session(
        session=db_session,
        session_id=session_id,
        benchmark="mmlu",
        model="gpt-test",
        model_version="v1",
    )

    db_session.execute.assert_awaited_once()
    db_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_eval_session_rejects_invalid_uuid_string():
    db_session = AsyncMock()

    with pytest.raises(ValueError):
        await ensure_eval_session(
            session=db_session,
            session_id="not-a-uuid",
            benchmark="mmlu",
            model="gpt-test",
            model_version="v1",
        )
