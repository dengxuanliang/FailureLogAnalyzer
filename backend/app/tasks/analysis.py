"""Celery tasks for the analysis pipeline."""
from __future__ import annotations
import asyncio
import uuid
from typing import Optional

from celery import shared_task
from sqlalchemy import select, func as sqlfunc

from app.db.session import get_async_session
from app.rules.base import RuleContext, RuleResult
from app.rules.registry import RuleRegistry
from app.rules.custom import CustomRule
from app.db.models.eval_record import EvalRecord
from app.db.models.analysis_result import AnalysisResult
from app.db.models.error_tag import ErrorTag
from app.db.models.analysis_rule import AnalysisRule
from app.db.models.enums import AnalysisType, TagSource


# -----------------------------------------------------------------------
# Pure logic helpers (testable without Celery/DB)
# -----------------------------------------------------------------------

def _apply_rules_to_record(
    record: EvalRecord,
    registry: RuleRegistry,
    session_avg_length: Optional[float],
) -> list[RuleResult]:
    """Run all rules in registry against one record, return combined results."""
    ctx = RuleContext(
        record_id=str(record.id),
        model_answer=record.model_answer or "",
        expected_answer=record.expected_answer or "",
        question=record.question or "",
        extracted_code=record.extracted_code,
        metadata=record.metadata_ or {} if hasattr(record, "metadata_") else record.metadata or {},
        session_avg_length=session_avg_length,
    )
    results: list[RuleResult] = []
    for rule in registry.all_rules():
        results.extend(rule.evaluate(ctx))
    return results


async def _run_rules_for_session_async(
    session_id: str,
    rule_ids: Optional[list[str]],
    batch_size: int = 500,
) -> dict:
    """
    Core async batch logic: reads eval_records for session_id, runs rules,
    writes analysis_results + error_tags. Returns summary dict.
    """
    async with get_async_session() as db:
        # 1. Load active custom rules from DB and merge into registry
        registry = RuleRegistry.default()
        db_rules_stmt = select(AnalysisRule).where(AnalysisRule.is_active == True)  # noqa: E712
        if rule_ids:
            db_rules_stmt = db_rules_stmt.where(AnalysisRule.name.in_(rule_ids))
        db_rules_result = await db.execute(db_rules_stmt)
        for db_rule in db_rules_result.scalars().all():
            registry.register(
                CustomRule(
                    name=db_rule.name,
                    field_path=db_rule.field,
                    condition=db_rule.condition,
                    tags=db_rule.tags,
                    confidence=db_rule.confidence,
                    priority=db_rule.priority,
                    description=db_rule.description or "",
                )
            )

        # 2. Compute session average answer length for LengthAnomalyRule
        avg_stmt = select(sqlfunc.avg(sqlfunc.length(EvalRecord.model_answer))).where(
            EvalRecord.session_id == uuid.UUID(session_id)
        )
        avg_row = (await db.execute(avg_stmt)).scalar()
        session_avg_length = float(avg_row) if avg_row else None

        # 3. Batch-process records
        offset = 0
        total_processed = 0
        total_tagged = 0

        while True:
            records_stmt = (
                select(EvalRecord)
                .where(EvalRecord.session_id == uuid.UUID(session_id))
                .order_by(EvalRecord.id)
                .offset(offset)
                .limit(batch_size)
            )
            records_result = await db.execute(records_stmt)
            records = records_result.scalars().all()
            if not records:
                break

            for record in records:
                rule_results = _apply_rules_to_record(record, registry, session_avg_length)
                if not rule_results:
                    total_processed += 1
                    continue

                # Write one analysis_result row
                error_types = list({r.tag_path for r in rule_results})
                analysis_result = AnalysisResult(
                    record_id=record.id,
                    analysis_type=AnalysisType.rule,
                    error_types=error_types,
                    confidence=max(r.confidence for r in rule_results),
                    evidence="; ".join(r.evidence for r in rule_results if r.evidence),
                )
                db.add(analysis_result)
                await db.flush()  # get analysis_result.id

                # Write one error_tag row per unique tag
                seen_tags: set[str] = set()
                for result in rule_results:
                    if result.tag_path in seen_tags:
                        continue
                    seen_tags.add(result.tag_path)
                    level = len(result.tag_path.split("."))
                    db.add(ErrorTag(
                        record_id=record.id,
                        analysis_result_id=analysis_result.id,
                        tag_path=result.tag_path,
                        tag_level=min(level, 3),
                        source=TagSource.rule,
                        confidence=result.confidence,
                    ))
                    total_tagged += 1

                total_processed += 1

            await db.commit()
            offset += batch_size

    return {
        "session_id": session_id,
        "total_processed": total_processed,
        "total_tagged": total_tagged,
    }


# -----------------------------------------------------------------------
# Celery task entry point
# -----------------------------------------------------------------------

@shared_task(
    name="tasks.analysis.run_rules",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def run_rules(self, session_id: str, rule_ids: Optional[list[str]] = None) -> dict:
    """
    Celery task: run rule engine over all eval_records in a session.

    Args:
        session_id: UUID of the eval session to analyse.
        rule_ids:   Optional list of custom rule names to include.
                    Pass None to include all active rules.

    Returns:
        Summary dict with total_processed and total_tagged counts.
    """
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            _run_rules_for_session_async(
                session_id=session_id,
                rule_ids=rule_ids,
            )
        )
    except Exception as exc:
        raise self.retry(exc=exc)
