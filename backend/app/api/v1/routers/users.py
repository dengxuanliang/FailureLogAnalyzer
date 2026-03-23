from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.core.auth import hash_password
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.user import UserCreate, UserPatch, UserResponse
from app.services.user_admin import find_user_by_username_or_email

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin)),
) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin)),
) -> User:
    existing = await find_user_by_username_or_email(
        db,
        username=payload.username,
        email=payload.email,
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    user = User(
        username=payload.username,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: UserPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.email is not None and payload.email != user.email:
        existing = await find_user_by_username_or_email(db, email=str(payload.email))
        if existing is not None and existing.id != user.id:
            raise HTTPException(status_code=409, detail="Email already exists")
        user.email = str(payload.email)

    if payload.password is not None:
        user.password_hash = hash_password(payload.password)

    if payload.role is not None:
        if current_user.id == user.id and payload.role != UserRole.admin:
            raise HTTPException(status_code=400, detail="Cannot remove your own admin role")
        user.role = payload.role

    if payload.is_active is not None:
        if current_user.id == user.id and payload.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return user
