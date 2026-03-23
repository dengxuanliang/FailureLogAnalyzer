from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.db.models.enums import ReportStatus, ReportType


class ReportGenerateRequest(BaseModel):
    title: str
    report_type: ReportType = ReportType.summary
    benchmark: str | None = None
    model_version: str | None = None
    session_ids: list[uuid.UUID] | None = None
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    version_a: str | None = None
    version_b: str | None = None

    model_config = {"protected_namespaces": ()}

    @model_validator(mode="after")
    def validate_comparison_fields(self) -> "ReportGenerateRequest":
        if self.report_type == ReportType.comparison and (not self.version_a or not self.version_b):
            raise ValueError("version_a and version_b are required when report_type=comparison")
        return self


class ReportGenerateResponse(BaseModel):
    report_id: uuid.UUID
    status: ReportStatus
    message: str


class ReportListItem(BaseModel):
    id: uuid.UUID
    title: str
    report_type: ReportType
    status: ReportStatus
    benchmark: str | None = None
    model_version: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ReportResponse(ReportListItem):
    session_ids: list[uuid.UUID] | None = None
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None

    model_config = {"from_attributes": True, "protected_namespaces": ()}
