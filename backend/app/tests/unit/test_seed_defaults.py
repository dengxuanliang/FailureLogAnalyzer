import uuid
from unittest.mock import AsyncMock

import pytest

from app.db.models.analysis_rule import AnalysisRule
from app.db.models.analysis_strategy import AnalysisStrategy
from app.db.models.enums import StrategyType
from app.db.models.prompt_template import PromptTemplate
from app.services.default_seed import (
    DEFAULT_RULE_NAME,
    DEFAULT_STRATEGY_NAMES,
    DEFAULT_TEMPLATE_NAME,
    seed_defaults,
)


class _Result:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def first(self):
        return self._items[0] if self._items else None


class _FakeDb:
    def __init__(self, templates=None, strategies=None, rules=None):
        self.templates = templates or []
        self.strategies = strategies or []
        self.rules = rules or []
        self.added = []
        self.commit = AsyncMock()
        self.flush = AsyncMock(side_effect=self._flush)

    async def execute(self, stmt):
        stmt_text = str(stmt)
        if "prompt_templates" in stmt_text:
            return _Result(self.templates)
        if "analysis_strategies" in stmt_text:
            return _Result(self.strategies)
        if "analysis_rules" in stmt_text:
            return _Result(self.rules)
        raise AssertionError(f"Unexpected stmt: {stmt_text}")

    def add(self, obj):
        self.added.append(obj)

    async def _flush(self):
        for obj in self.added:
            if isinstance(obj, PromptTemplate) and obj.id is None:
                obj.id = uuid.uuid4()


@pytest.mark.asyncio
async def test_seed_defaults_creates_items_when_missing():
    db = _FakeDb()

    report = await seed_defaults(db, provider="openai", model="gpt-4o", created_by="bootstrap")

    assert report.created_templates == [DEFAULT_TEMPLATE_NAME]
    assert report.created_strategies == DEFAULT_STRATEGY_NAMES
    assert report.created_rules == [DEFAULT_RULE_NAME]
    assert report.skipped_templates == []

    template = next(obj for obj in db.added if isinstance(obj, PromptTemplate))
    strategies = [obj for obj in db.added if isinstance(obj, AnalysisStrategy)]
    rules = [obj for obj in db.added if isinstance(obj, AnalysisRule)]

    assert template.name == DEFAULT_TEMPLATE_NAME
    assert template.id is not None
    assert "error_types" in template.template
    assert len(strategies) == 2
    for strategy in strategies:
        assert strategy.prompt_template_id == template.id
        assert strategy.llm_provider == "openai"
        assert strategy.llm_model == "gpt-4o"
        assert strategy.created_by == "bootstrap"

    assert len(rules) == 1
    assert rules[0].name == DEFAULT_RULE_NAME

    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_seed_defaults_skips_existing_items():
    template = PromptTemplate(
        id=uuid.uuid4(),
        name=DEFAULT_TEMPLATE_NAME,
        benchmark=None,
        template="existing",
        version=1,
        is_active=True,
        created_by="someone",
    )
    strategies = [
        AnalysisStrategy(
            id=uuid.uuid4(),
            name=DEFAULT_STRATEGY_NAMES[0],
            strategy_type=StrategyType.fallback,
            config={},
            llm_provider="openai",
            llm_model="gpt-4o",
            prompt_template_id=template.id,
            is_active=True,
            created_by="someone",
        ),
        AnalysisStrategy(
            id=uuid.uuid4(),
            name=DEFAULT_STRATEGY_NAMES[1],
            strategy_type=StrategyType.manual,
            config={},
            llm_provider="openai",
            llm_model="gpt-4o",
            prompt_template_id=template.id,
            is_active=True,
            created_by="someone",
        ),
    ]
    rule = AnalysisRule(
        id=uuid.uuid4(),
        name=DEFAULT_RULE_NAME,
        field="model_answer",
        condition={"type": "regex", "pattern": "hi"},
        tags=["x"],
        confidence=0.5,
        priority=10,
        is_active=True,
        created_by="someone",
    )
    db = _FakeDb(templates=[template], strategies=strategies, rules=[rule])

    report = await seed_defaults(db, provider="openai", model="gpt-4o", created_by="bootstrap")

    assert report.created_templates == []
    assert report.created_strategies == []
    assert report.created_rules == []
    assert report.skipped_templates == [DEFAULT_TEMPLATE_NAME]
    assert report.skipped_strategies == DEFAULT_STRATEGY_NAMES
    assert report.skipped_rules == [DEFAULT_RULE_NAME]
    assert db.added == []

    db.commit.assert_awaited_once()
