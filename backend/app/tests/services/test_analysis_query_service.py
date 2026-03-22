from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.error_tag import ErrorTag
from app.services.analysis_query import update_record_error_tags


@pytest.mark.asyncio
async def test_update_record_error_tags_returns_none_for_missing_record():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    result = await update_record_error_tags(db=db, record_id=uuid.uuid4(), tags=["推理性错误.逻辑推理.推理链断裂"])

    assert result is None
    db.execute.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_update_record_error_tags_replaces_and_normalizes_tags():
    record_id = uuid.uuid4()
    db = AsyncMock()
    db.get = AsyncMock(return_value=MagicMock(id=record_id))
    db.add = MagicMock()

    result = await update_record_error_tags(
        db=db,
        record_id=record_id,
        tags=[
            " 推理性错误.逻辑推理.推理链断裂 ",
            "推理性错误.逻辑推理.推理链断裂",
            "",
            "格式性错误.输出格式不符",
        ],
    )

    assert result == {
        "record_id": record_id,
        "saved_tags": [
            "推理性错误.逻辑推理.推理链断裂",
            "格式性错误.输出格式不符",
        ],
    }
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()
    assert db.add.call_count == 2

    added_tags = [call.args[0] for call in db.add.call_args_list]
    assert all(isinstance(item, ErrorTag) for item in added_tags)
    assert [item.tag_path for item in added_tags] == result["saved_tags"]
    assert [item.tag_level for item in added_tags] == [3, 2]
