"""Daily budget accounting for LLM judge jobs."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BudgetTracker:
    """Track cumulative spend against an optional daily budget limit."""

    daily_budget: float | None
    initial_spent: float = 0.0

    def __post_init__(self) -> None:
        self.daily_budget = None if self.daily_budget is None else max(0.0, float(self.daily_budget))
        self._spent = max(0.0, float(self.initial_spent))

    @property
    def spent(self) -> float:
        return self._spent

    @property
    def remaining(self) -> float | None:
        if self.daily_budget is None:
            return None
        return max(0.0, self.daily_budget - self._spent)

    @property
    def exhausted(self) -> bool:
        if self.daily_budget is None:
            return False
        return self._spent >= self.daily_budget

    def can_spend(self, cost: float) -> bool:
        if cost < 0:
            return False
        if self.daily_budget is None:
            return True
        return self._spent + cost <= self.daily_budget

    def record_spend(self, cost: float) -> None:
        if cost <= 0:
            return
        self._spent += float(cost)

    def snapshot(self) -> dict[str, float | bool | None]:
        return {
            "budget": self.daily_budget,
            "spent": self._spent,
            "remaining": self.remaining,
            "exhausted": self.exhausted,
        }
