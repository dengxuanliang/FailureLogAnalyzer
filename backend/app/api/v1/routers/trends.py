from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db.models.enums import UserRole
from app.db.session import get_db
from app.schemas.cross_benchmark import ErrorTrends
from app.services.cross_benchmark import get_error_trends

router = APIRouter(tags=["trends"])


@router.get("/trends", response_model=ErrorTrends)
async def trends(
    benchmark: str | None = None,
    model_version: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    return await get_error_trends(db=db, benchmark=benchmark, model_version=model_version)
