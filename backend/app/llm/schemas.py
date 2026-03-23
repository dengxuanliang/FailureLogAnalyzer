"""Schemas used by the LLM Judge pipeline."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class LlmJudgeOutput(BaseModel):
    """Structured response expected from an LLM judge model."""

    error_types: list[str] = Field(..., min_length=1)
    root_cause: str
    severity: Severity
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: str
    suggestion: str


class PromptContext(BaseModel):
    """Available template variables while rendering prompts."""

    model_config = ConfigDict(protected_namespaces=())

    question: str
    expected: str
    model_answer: str
    rule_tags: list[str] = Field(default_factory=list)
    task_category: str = ""
