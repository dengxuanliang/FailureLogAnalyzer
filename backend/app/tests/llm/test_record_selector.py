import uuid

from app.db.models.enums import StrategyType
from app.llm.record_selector import _select_from_candidates


class _Record:
    def __init__(self, rid: str, task_category: str | None = None):
        self.id = uuid.UUID(rid)
        self.task_category = task_category


def test_select_from_candidates_full_returns_all_records():
    records = [
        _Record("00000000-0000-0000-0000-000000000001"),
        _Record("00000000-0000-0000-0000-000000000002"),
    ]

    selected = _select_from_candidates(
        records,
        strategy_type=StrategyType.full,
        config={},
        manual_record_ids=[],
        ruled_record_ids=set(),
    )

    assert selected == records


def test_select_from_candidates_fallback_excludes_ruled_records():
    records = [
        _Record("00000000-0000-0000-0000-000000000001"),
        _Record("00000000-0000-0000-0000-000000000002"),
    ]

    selected = _select_from_candidates(
        records,
        strategy_type=StrategyType.fallback,
        config={},
        manual_record_ids=[],
        ruled_record_ids={uuid.UUID("00000000-0000-0000-0000-000000000001")},
    )

    assert [r.id for r in selected] == [uuid.UUID("00000000-0000-0000-0000-000000000002")]


def test_select_from_candidates_sample_honors_filters_and_size():
    records = [
        _Record("00000000-0000-0000-0000-000000000001", task_category="math"),
        _Record("00000000-0000-0000-0000-000000000002", task_category="math"),
        _Record("00000000-0000-0000-0000-000000000003", task_category="reasoning"),
    ]

    selected = _select_from_candidates(
        records,
        strategy_type=StrategyType.sample,
        config={"sample_size": 1, "categories": ["math"], "seed": 7},
        manual_record_ids=[],
        ruled_record_ids=set(),
    )

    assert len(selected) == 1
    assert selected[0].task_category == "math"


def test_select_from_candidates_manual_requires_manual_ids():
    records = [
        _Record("00000000-0000-0000-0000-000000000001"),
    ]

    selected = _select_from_candidates(
        records,
        strategy_type=StrategyType.manual,
        config={},
        manual_record_ids=[uuid.UUID("00000000-0000-0000-0000-000000000001")],
        ruled_record_ids=set(),
    )

    assert len(selected) == 1
