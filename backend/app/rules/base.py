"""BaseRule interface shared by all built-in and custom rules."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RuleContext:
    """All fields a rule can inspect from a single eval_record row."""
    record_id: str
    model_answer: str
    expected_answer: str
    question: str
    extracted_code: Optional[str]
    metadata: dict
    # Optional enrichment used by LengthAnomalyRule
    session_avg_length: Optional[float] = None


@dataclass
class RuleResult:
    tag_path: str
    confidence: float
    evidence: str = ""


class BaseRule(ABC):
    """Abstract base for all rules."""

    # Subclasses set these as class attributes
    rule_id: str = ""
    name: str = ""
    description: str = ""
    priority: int = 50  # lower = runs first

    @abstractmethod
    def evaluate(self, ctx: RuleContext) -> list[RuleResult]:
        """Return zero or more RuleResults for the given record context."""
        ...

    def is_enabled(self) -> bool:  # noqa: D102
        return True
