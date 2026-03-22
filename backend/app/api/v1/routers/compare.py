from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db.models.enums import UserRole
from app.db.session import get_db
from app.schemas.compare import RadarData, VersionComparison, VersionDiff
from app.services.compare import compare_versions, get_radar_data, get_version_diff

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("/versions", response_model=VersionComparison)
async def versions(
    version_a: str = Query(...),
    version_b: str = Query(...),
    benchmark: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    return await compare_versions(db=db, version_a=version_a, version_b=version_b, benchmark=benchmark)


@router.get("/diff", response_model=VersionDiff)
async def diff(
    version_a: str = Query(...),
    version_b: str = Query(...),
    benchmark: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    return await get_version_diff(db=db, version_a=version_a, version_b=version_b, benchmark=benchmark)


@router.get("/radar", response_model=RadarData)
async def radar(
    version_a: str = Query(...),
    version_b: str = Query(...),
    benchmark: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    return await get_radar_data(db=db, version_a=version_a, version_b=version_b, benchmark=benchmark)
