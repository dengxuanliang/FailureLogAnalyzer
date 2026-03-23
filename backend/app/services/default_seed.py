from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis_rule import AnalysisRule
from app.db.models.analysis_strategy import AnalysisStrategy
from app.db.models.enums import StrategyType
from app.db.models.prompt_template import PromptTemplate
from app.rules.taxonomy import TaxonomyTree

DEFAULT_TEMPLATE_NAME = "builtin-default"
DEFAULT_TEMPLATE_VERSION = 1
DEFAULT_STRATEGY_NAMES = ["default-fallback", "default-manual"]
DEFAULT_RULE_NAME = "default-refusal-phrases"

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert failure-analysis judge. "
    "Return JSON only, following the requested schema and taxonomy."
)

_DEFAULT_RULE_PATTERN = r"(?i)\\b(i don't know|i do not know|cannot|can't|unable|sorry)\\b"


@dataclass
class SeedReport:
    created_templates: list[str] = field(default_factory=list)
    skipped_templates: list[str] = field(default_factory=list)
    created_strategies: list[str] = field(default_factory=list)
    skipped_strategies: list[str] = field(default_factory=list)
    created_rules: list[str] = field(default_factory=list)
    skipped_rules: list[str] = field(default_factory=list)


def _build_default_template() -> str:
    taxonomy_paths = "\n".join(f"- {path}" for path in TaxonomyTree.load_default().all_paths())
    return (
        "You are analyzing a model failure. Use the taxonomy paths below.\n"
        "Question: {question}\n"
        "Expected: {expected}\n"
        "Model Answer: {model_answer}\n"
        "Rule Tags: {rule_tags}\n"
        "Task Category: {task_category}\n\n"
        "Return JSON ONLY with keys:\n"
        "- error_types: list of taxonomy paths\n"
        "- root_cause: short explanation\n"
        "- severity: high|medium|low\n"
        "- confidence: 0-1\n"
        "- evidence: brief supporting evidence\n"
        "- suggestion: how to fix\n\n"
        "Valid taxonomy paths:\n"
        f"{taxonomy_paths}\n"
    )


async def _get_template(db: AsyncSession) -> PromptTemplate | None:
    stmt = select(PromptTemplate).where(
        PromptTemplate.name == DEFAULT_TEMPLATE_NAME,
        PromptTemplate.version == DEFAULT_TEMPLATE_VERSION,
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def _get_strategy(db: AsyncSession, name: str) -> AnalysisStrategy | None:
    stmt = select(AnalysisStrategy).where(AnalysisStrategy.name == name)
    result = await db.execute(stmt)
    return result.scalars().first()


async def _get_rule(db: AsyncSession) -> AnalysisRule | None:
    stmt = select(AnalysisRule).where(AnalysisRule.name == DEFAULT_RULE_NAME)
    result = await db.execute(stmt)
    return result.scalars().first()


async def seed_defaults(
    db: AsyncSession,
    *,
    provider: str = "openai",
    model: str = "gpt-4o",
    created_by: str = "bootstrap",
) -> SeedReport:
    report = SeedReport()

    template = await _get_template(db)
    if template is None:
        template = PromptTemplate(
            name=DEFAULT_TEMPLATE_NAME,
            benchmark=None,
            template=_build_default_template(),
            version=DEFAULT_TEMPLATE_VERSION,
            is_active=True,
            created_by=created_by,
        )
        db.add(template)
        await db.flush()
        report.created_templates.append(DEFAULT_TEMPLATE_NAME)
    else:
        report.skipped_templates.append(DEFAULT_TEMPLATE_NAME)

    strategy_config = {
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "requests_per_minute": 60,
        "breaker_failure_threshold": 3,
        "breaker_recovery_seconds": 30.0,
    }

    strategy_defs = [
        (DEFAULT_STRATEGY_NAMES[0], StrategyType.fallback),
        (DEFAULT_STRATEGY_NAMES[1], StrategyType.manual),
    ]

    for name, strategy_type in strategy_defs:
        existing = await _get_strategy(db, name)
        if existing is None:
            strategy = AnalysisStrategy(
                name=name,
                strategy_type=strategy_type,
                config=dict(strategy_config),
                llm_provider=provider,
                llm_model=model,
                prompt_template_id=template.id,
                max_concurrent=None,
                daily_budget=None,
                is_active=True,
                created_by=created_by,
            )
            db.add(strategy)
            report.created_strategies.append(name)
        else:
            report.skipped_strategies.append(name)

    rule = await _get_rule(db)
    if rule is None:
        rule = AnalysisRule(
            name=DEFAULT_RULE_NAME,
            description="Flag common refusal/unknown responses.",
            field="model_answer",
            condition={"type": "regex", "pattern": _DEFAULT_RULE_PATTERN},
            tags=["格式与规范错误.空回答/拒绝回答"],
            confidence=0.75,
            priority=20,
            is_active=True,
            created_by=created_by,
        )
        db.add(rule)
        report.created_rules.append(DEFAULT_RULE_NAME)
    else:
        report.skipped_rules.append(DEFAULT_RULE_NAME)

    await db.commit()
    return report
