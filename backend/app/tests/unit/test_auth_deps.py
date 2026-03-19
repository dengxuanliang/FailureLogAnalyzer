import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock
from app.api.v1.deps import require_role
from app.db.models.enums import UserRole


@pytest.mark.asyncio
async def test_require_role_passes_when_role_matches():
    mock_user = MagicMock()
    mock_user.role = UserRole.analyst
    checker = require_role(UserRole.analyst)
    result = await checker(current_user=mock_user)
    assert result == mock_user


@pytest.mark.asyncio
async def test_require_role_passes_for_higher_role():
    mock_user = MagicMock()
    mock_user.role = UserRole.admin
    checker = require_role(UserRole.analyst)
    result = await checker(current_user=mock_user)
    assert result == mock_user


@pytest.mark.asyncio
async def test_require_role_raises_403_for_insufficient_role():
    mock_user = MagicMock()
    mock_user.role = UserRole.viewer
    checker = require_role(UserRole.analyst)
    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=mock_user)
    assert exc_info.value.status_code == 403
