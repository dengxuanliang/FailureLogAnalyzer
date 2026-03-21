from __future__ import annotations

from pydantic import BaseModel, Field


class VersionComparison(BaseModel):
    version_a: str
    version_b: str
    benchmark: str | None = None
    sessions_a: int
    sessions_b: int
    accuracy_a: float
    accuracy_b: float
    accuracy_delta: float
    error_rate_a: float
    error_rate_b: float
    error_rate_delta: float


class DiffItem(BaseModel):
    question_id: str | None = None
    benchmark: str | None = None
    category: str | None = None
    old_tag: str | None = None
    new_tag: str | None = None


class VersionDiff(BaseModel):
    version_a: str
    version_b: str
    regressed: list[DiffItem] = Field(default_factory=list)
    improved: list[DiffItem] = Field(default_factory=list)
    new_errors: list[DiffItem] = Field(default_factory=list)
    fixed_errors: list[DiffItem] = Field(default_factory=list)


class RadarData(BaseModel):
    version_a: str
    version_b: str
    dimensions: list[str] = Field(default_factory=list)
    scores_a: list[float] = Field(default_factory=list)
    scores_b: list[float] = Field(default_factory=list)
