"""Pydantic schemas for LLM strategy/template/job APIs."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.db.models.enums import StrategyType


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    benchmark: str | None = Field(default=None, max_length=64)
    template: str = Field(..., min_length=1)
    version: int = Field(default=1, ge=1)
    is_active: bool = True


class TemplatePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    benchmark: str | None = Field(default=None, max_length=64)
    template: str | None = Field(default=None, min_length=1)
    version: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    benchmark: str | None
    template: str
    version: int
    is_active: bool
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    strategy_type: StrategyType
    config: dict[str, Any] = Field(default_factory=dict)
    llm_provider: str = Field(..., min_length=1, max_length=64)
    llm_model: str = Field(..., min_length=1, max_length=128)
    prompt_template_id: uuid.UUID | None = None
    max_concurrent: int | None = Field(default=None, ge=1, le=32)
    daily_budget: float | None = Field(default=None, ge=0.0)
    is_active: bool = True


class StrategyPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    strategy_type: StrategyType | None = None
    config: dict[str, Any] | None = None
    llm_provider: str | None = Field(default=None, min_length=1, max_length=64)
    llm_model: str | None = Field(default=None, min_length=1, max_length=128)
    prompt_template_id: uuid.UUID | None = None
    max_concurrent: int | None = Field(default=None, ge=1, le=32)
    daily_budget: float | None = Field(default=None, ge=0.0)
    is_active: bool | None = None


class StrategyResponse(BaseModel):
    id: uuid.UUID
    name: str
    strategy_type: StrategyType
    config: dict[str, Any] | None
    llm_provider: str | None
    llm_model: str | None
    prompt_template_id: uuid.UUID | None
    max_concurrent: int | None
    daily_budget: float | None
    is_active: bool
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LlmJobTriggerRequest(BaseModel):
    session_id: uuid.UUID
    strategy_id: uuid.UUID
    manual_record_ids: list[uuid.UUID] = Field(default_factory=list)
    expect_manual_records: bool = False

    @model_validator(mode="after")
    def validate_manual_ids_if_required(self) -> "LlmJobTriggerRequest":
        if self.expect_manual_records and not self.manual_record_ids:
            raise ValueError("manual_record_ids is required when expect_manual_records=true")
        return self


class LlmJobTriggerResponse(BaseModel):
    job_id: str
    celery_task_id: str
    status: str


class LlmJobStatusResponse(BaseModel):
    job_id: str
    session_id: str
    strategy_id: str
    status: str
    processed: int
    total: int | None
    succeeded: int
    failed: int
    total_cost: float
    stop_reason: str | None = None
    reason: str = ""
    celery_task_id: str | None = None
    created_at: float
    updated_at: float


class SessionCostModelBreakdown(BaseModel):
    llm_model: str
    calls: int
    total_cost: float


class SessionCostSummaryResponse(BaseModel):
    session_id: str
    total_calls: int
    total_cost: float
    by_model: list[SessionCostModelBreakdown]
