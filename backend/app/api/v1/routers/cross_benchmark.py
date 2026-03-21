from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db.models.enums import UserRole
from app.db.session import get_db
from app.schemas.cross_benchmark import BenchmarkMatrix, SystematicWeaknesses
from app.services.cross_benchmark import get_benchmark_matrix, get_systematic_weaknesses

router = APIRouter(prefix="/cross-benchmark", tags=["cross-benchmark"])


@router.get("/matrix", response_model=BenchmarkMatrix)
async def matrix(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    return await get_benchmark_matrix(db=db)


@router.get("/weakness", response_model=SystematicWeaknesses)
async def weakness(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    return await get_systematic_weaknesses(db=db)
