from __future__ import annotations

from pydantic import BaseModel, Field


class BenchmarkMatrix(BaseModel):
    models: list[str] = Field(default_factory=list)
    benchmarks: list[str] = Field(default_factory=list)
    matrix: list[list[float]] = Field(default_factory=list)


class WeaknessItem(BaseModel):
    tag: str
    affected_benchmarks: list[str] = Field(default_factory=list)
    avg_error_rate: float


class SystematicWeaknesses(BaseModel):
    weaknesses: list[WeaknessItem] = Field(default_factory=list)


class TrendDataPoint(BaseModel):
    date: str
    error_rate: float
    benchmark: str | None = None
    model_version: str | None = None

    model_config = {"protected_namespaces": ()}


class ErrorTrends(BaseModel):
    data_points: list[TrendDataPoint] = Field(default_factory=list)
