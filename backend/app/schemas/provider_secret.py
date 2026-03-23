from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProviderSecretCreate(BaseModel):
    provider: str = Field(..., min_length=1, max_length=64)
    name: str = Field(default="default", min_length=1, max_length=128)
    secret: str = Field(..., min_length=1, max_length=4096)
    is_active: bool = True
    is_default: bool = False


class ProviderSecretPatch(BaseModel):
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    secret: str | None = Field(default=None, min_length=1, max_length=4096)
    is_active: bool | None = None
    is_default: bool | None = None


class ProviderSecretResponse(BaseModel):
    id: uuid.UUID
    provider: str
    name: str
    secret_mask: str
    is_active: bool
    is_default: bool
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
