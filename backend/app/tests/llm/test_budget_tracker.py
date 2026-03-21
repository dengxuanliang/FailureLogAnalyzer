from app.llm.budget_tracker import BudgetTracker


def test_budget_tracker_enforces_daily_limit():
    tracker = BudgetTracker(daily_budget=10.0, initial_spent=3.0)

    assert tracker.can_spend(2.0) is True
    assert tracker.can_spend(7.01) is False

    tracker.record_spend(2.5)
    assert tracker.spent == 5.5
    assert tracker.remaining == 4.5

    summary = tracker.snapshot()
    assert summary["budget"] == 10.0
    assert summary["spent"] == 5.5
    assert summary["remaining"] == 4.5
    assert summary["exhausted"] is False


def test_budget_tracker_unlimited_mode():
    tracker = BudgetTracker(daily_budget=None, initial_spent=99.0)

    assert tracker.can_spend(1000.0) is True
    tracker.record_spend(12.3)

    assert tracker.remaining is None
    assert tracker.snapshot()["exhausted"] is False
