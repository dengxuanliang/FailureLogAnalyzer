from __future__ import annotations
import hashlib
from typing import Any
from pydantic import BaseModel, Field, model_validator


class NormalizedRecord(BaseModel):
    """Standard representation of one evaluation record across all benchmarks."""
    session_id: str
    benchmark: str
    model: str
    model_version: str
    task_category: str = ""
    question_id: str
    question: str
    expected_answer: str
    model_answer: str
    is_correct: bool
    score: float = 0.0
    extracted_code: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_json: dict[str, Any] = Field(default_factory=dict)

    # Computed on construction — NOT a constructor argument
    dedup_hash: str = Field(default="", init=False)

    @model_validator(mode="after")
    def _compute_dedup_hash(self) -> NormalizedRecord:
        key = f"{self.session_id}:{self.question_id}".encode()
        self.dedup_hash = hashlib.sha256(key).hexdigest()
        return self
