"""Pydantic schemas for analysis_rules API."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class RuleCondition(BaseModel):
    type: str  # regex | contains | not_contains | length_gt | length_lt | field_equals | field_missing | python_expr
    pattern: Optional[str] = None   # for regex
    value: Optional[Any] = None     # for contains/not_contains/length_gt/length_lt/field_equals
    expr: Optional[str] = None      # for python_expr


class RuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    field: str = Field(..., min_length=1, max_length=255)
    condition: RuleCondition
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    priority: int = Field(default=50, ge=0)
    is_active: bool = True


class RulePatch(BaseModel):
    description: Optional[str] = None
    field: Optional[str] = None
    condition: Optional[RuleCondition] = None
    tags: Optional[list[str]] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    priority: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    field: str
    condition: dict
    tags: list[str]
    confidence: float
    priority: int
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
