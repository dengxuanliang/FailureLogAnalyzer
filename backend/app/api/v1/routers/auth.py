from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.core.auth import verify_password, create_access_token, hash_password
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BootstrapRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)


class BootstrapResponse(TokenResponse):
    user: UserResponse


async def authenticate_user(username: str, password: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(form.username, form.password, db)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/bootstrap", response_model=BootstrapResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap_admin(
    payload: BootstrapRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        async with db.begin():
            await db.execute(text("LOCK TABLE users IN EXCLUSIVE MODE"))
            existing = (await db.execute(select(User.id).limit(1))).scalar_one_or_none()
            if existing is not None:
                raise HTTPException(status_code=409, detail="Bootstrap already completed")

            user = User(
                username=payload.username,
                email=str(payload.email),
                password_hash=hash_password(payload.password),
                role=UserRole.admin,
                is_active=True,
            )
            db.add(user)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Bootstrap already completed") from exc

    await db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return BootstrapResponse(access_token=token, user=user)
