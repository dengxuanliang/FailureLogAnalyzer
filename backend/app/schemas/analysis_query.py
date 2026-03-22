from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalysisSummary(BaseModel):
    total_sessions: int
    total_records: int
    total_errors: int
    accuracy: float
    llm_analysed_count: int
    llm_total_cost: float


class DistributionItem(BaseModel):
    label: str
    count: int
    percentage: float


class ErrorRecordBrief(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    benchmark: str
    task_category: str | None = None
    question_id: str | None = None
    question: str
    is_correct: bool
    score: float | None = None
    error_tags: list[str] = Field(default_factory=list)
    has_llm_analysis: bool = False


class PaginatedRecords(BaseModel):
    items: list[ErrorRecordBrief]
    total: int
    page: int
    size: int


class AnalysisResultDetail(BaseModel):
    id: uuid.UUID
    analysis_type: str
    error_types: list[str] = Field(default_factory=list)
    root_cause: str | None = None
    severity: str | None = None
    confidence: float | None = None
    evidence: str | None = None
    suggestion: str | None = None
    llm_model: str | None = None
    llm_cost: float | None = None
    unmatched_tags: list[str] = Field(default_factory=list)
    created_at: datetime


class RecordDetail(BaseModel):
    record: dict[str, Any]
    analysis_results: list[AnalysisResultDetail]
    error_tags: list[dict[str, Any]]


class RecordTagsPatchRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)
    note: str | None = None


class RecordTagsPatchResponse(BaseModel):
    record_id: uuid.UUID
    saved_tags: list[str] = Field(default_factory=list)
