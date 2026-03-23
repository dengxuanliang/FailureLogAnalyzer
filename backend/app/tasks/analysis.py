"""Celery tasks for the analysis pipeline."""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from celery import shared_task
from sqlalchemy import func as sqlfunc
from sqlalchemy import select

from app.core.redis import get_redis
from app.db.models.analysis_result import AnalysisResult
from app.db.models.analysis_rule import AnalysisRule
from app.db.models.analysis_strategy import AnalysisStrategy
from app.db.models.enums import AnalysisType, SeverityLevel, TagSource
from app.db.models.error_tag import ErrorTag
from app.db.models.eval_record import EvalRecord
from app.db.models.prompt_template import PromptTemplate
from app.db.models.provider_secret import ProviderSecret
from app.db.session import get_async_session
from app.ingestion.progress import ProgressPublisher
from app.llm.budget_tracker import BudgetTracker
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.cost_calculator import estimate_cost
from app.llm.job_store import update_job
from app.llm.output_parser import parse_llm_response
from app.llm.prompt_renderer import render_prompt
from app.llm.providers.base import BaseLlmProvider, LlmResponse
from app.llm.providers.registry import create_provider
from app.llm.rate_limiter import AsyncRateLimiter
from app.llm.record_selector import select_records
from app.llm.schemas import PromptContext
from app.rules.base import RuleContext, RuleResult
from app.services.provider_secret_crypto import decrypt_secret
from app.tasks.async_runner import run_async_in_worker
from app.rules.custom import CustomRule
from app.rules.registry import RuleRegistry

logger = logging.getLogger(__name__)

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
    started = time.monotonic()

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
                    db.add(
                        ErrorTag(
                            record_id=record.id,
                            analysis_result_id=analysis_result.id,
                            tag_path=result.tag_path,
                            tag_level=min(level, 3),
                            source=TagSource.rule,
                            confidence=result.confidence,
                        )
                    )
                    total_tagged += 1

                total_processed += 1

            await db.commit()
            offset += batch_size

    result = {
        "session_id": session_id,
        "total_processed": total_processed,
        "total_tagged": total_tagged,
    }
    logger.info(
        "run_rules completed",
        extra={
            "session_id": session_id,
            "rule_ids": rule_ids,
            "total_processed": total_processed,
            "total_tagged": total_tagged,
            "duration_seconds": round(time.monotonic() - started, 6),
        },
    )
    return result


# -----------------------------------------------------------------------
# Celery task entry point
# -----------------------------------------------------------------------


@shared_task(name="tasks.analysis.run_rules", bind=True, max_retries=3, default_retry_delay=10)
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
        logger.info("run_rules task started", extra={"session_id": session_id, "rule_ids": rule_ids})
        return run_async_in_worker(_run_rules_for_session_async(session_id=session_id, rule_ids=rule_ids))
    except Exception as exc:
        logger.exception("run_rules task failed", extra={"session_id": session_id, "rule_ids": rule_ids})
        raise self.retry(exc=exc)


# -----------------------------------------------------------------------
# LLM Judge helper path
# -----------------------------------------------------------------------

_FORMAT_REPAIR_SUFFIX = "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no explanation."
_DEFAULT_SYSTEM_PROMPT = (
    "You are an expert failure-analysis judge. Return JSON strictly following the requested schema."
)
_DEFAULT_TEMPLATE = """Question: {question}\nExpected: {expected}\nModel Answer: {model_answer}\nRule Tags: {rule_tags}\nTask Category: {task_category}"""


async def _call_llm_with_retry(
    provider: BaseLlmProvider,
    system_prompt: str,
    user_prompt: str,
    *,
    max_attempts: int = 3,
    base_backoff_seconds: float = 0.2,
) -> LlmResponse:
    """Call provider with lightweight exponential retry for transient API failures."""
    delay = base_backoff_seconds
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await provider.call(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as exc:  # pragma: no cover - behavior exercised through caller
            last_exc = exc
            if attempt == max_attempts - 1:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, 2.0)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("LLM call failed without exception")


async def _analyse_single_record(
    record: object,
    provider: BaseLlmProvider,
    template: str,
    system_prompt: str,
    rule_tags: list[str],
) -> dict:
    """Run one record through render -> provider -> parse and return normalized payload."""
    context = PromptContext(
        question=getattr(record, "question", "") or "",
        expected=getattr(record, "expected_answer", "") or "",
        model_answer=getattr(record, "model_answer", "") or "",
        rule_tags=rule_tags,
        task_category=getattr(record, "task_category", "") or "",
    )
    user_prompt = render_prompt(template, context)

    first = await _call_llm_with_retry(
        provider=provider,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    parsed = parse_llm_response(first.text)
    final_response = first
    prompt_tokens = first.prompt_tokens
    completion_tokens = first.completion_tokens

    if not parsed.success:
        repaired = await _call_llm_with_retry(
            provider=provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt + _FORMAT_REPAIR_SUFFIX,
        )
        final_response = repaired
        prompt_tokens += repaired.prompt_tokens
        completion_tokens += repaired.completion_tokens
        parsed = parse_llm_response(repaired.text)

    llm_cost = estimate_cost(
        model=final_response.model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    if not parsed.success:
        return {
            "success": False,
            "record_id": str(getattr(record, "id", "")),
            "raw_response": final_response.text,
            "error": parsed.error,
            "llm_cost": llm_cost,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "model": final_response.model,
        }

    output = parsed.output
    assert output is not None
    return {
        "success": True,
        "record_id": str(getattr(record, "id", "")),
        "error_types": output.error_types,
        "root_cause": output.root_cause,
        "severity": output.severity.value,
        "confidence": output.confidence,
        "evidence": output.evidence,
        "suggestion": output.suggestion,
        "unmatched_tags": parsed.unmatched_tags,
        "llm_cost": llm_cost,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "model": final_response.model,
        "raw_response": final_response.text,
    }


def _coerce_uuid_list(values: list[str] | None) -> list[uuid.UUID]:
    if not values:
        return []
    parsed: list[uuid.UUID] = []
    for value in values:
        parsed.append(uuid.UUID(str(value)))
    return parsed


def _severity_from_str(value: str | None) -> SeverityLevel | None:
    if not value:
        return None
    normalized = value.lower()
    if normalized == SeverityLevel.high.value:
        return SeverityLevel.high
    if normalized == SeverityLevel.medium.value:
        return SeverityLevel.medium
    if normalized == SeverityLevel.low.value:
        return SeverityLevel.low
    return None


async def _resolve_provider_api_key(db, provider_name: str) -> str:
    normalized = provider_name.lower()

    provider_aliases: dict[str, list[str]] = {
        "openai": ["openai"],
        "local": ["local", "openai"],
        "claude": ["claude", "anthropic"],
        "anthropic": ["anthropic", "claude"],
    }
    env_var_names: dict[str, str] = {
        "openai": "OPENAI_API_KEY",
        "local": "OPENAI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }

    aliases = provider_aliases.get(normalized)
    env_var = env_var_names.get(normalized)
    if aliases is None or env_var is None:
        raise ValueError(f"Unsupported provider: {provider_name!r}")

    row = None
    if hasattr(db, "execute"):
        stmt = (
            select(ProviderSecret)
            .where(ProviderSecret.provider.in_(aliases), ProviderSecret.is_active.is_(True))
            .order_by(ProviderSecret.is_default.desc(), ProviderSecret.updated_at.desc())
            .limit(1)
        )
        row = (await db.execute(stmt)).scalars().first()
    if row is not None:
        return decrypt_secret(row.encrypted_secret)

    key = os.getenv(env_var, "")
    if key:
        return key
    raise ValueError(f"{env_var} is required for {normalized} provider")


async def _get_existing_daily_spend(db, *, model: str | None = None) -> float:
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(sqlfunc.coalesce(sqlfunc.sum(AnalysisResult.llm_cost), 0.0)).where(
        AnalysisResult.analysis_type == AnalysisType.llm,
        AnalysisResult.created_at >= day_start,
    )
    if model:
        stmt = stmt.where(AnalysisResult.llm_model == model)
    value = (await db.execute(stmt)).scalar_one()
    return float(value or 0.0)


async def _fetch_ruled_record_ids(db, *, session_id: uuid.UUID) -> set[uuid.UUID]:
    stmt = (
        select(AnalysisResult.record_id)
        .join(EvalRecord, EvalRecord.id == AnalysisResult.record_id)
        .where(EvalRecord.session_id == session_id)
        .where(AnalysisResult.analysis_type == AnalysisType.rule)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return set(rows)


async def _fetch_rule_tags_map(db, record_ids: list[uuid.UUID]) -> dict[str, list[str]]:
    if not record_ids:
        return {}
    stmt = (
        select(ErrorTag.record_id, ErrorTag.tag_path)
        .where(ErrorTag.record_id.in_(record_ids))
        .where(ErrorTag.source == TagSource.rule)
    )
    rows = (await db.execute(stmt)).all()
    tags_map: dict[str, list[str]] = {}
    for record_id, tag_path in rows:
        key = str(record_id)
        bucket = tags_map.setdefault(key, [])
        if tag_path not in bucket:
            bucket.append(tag_path)
    return tags_map


async def _persist_llm_result(
    db,
    *,
    record_id: uuid.UUID,
    payload: dict,
    prompt_template: str,
) -> None:
    analysis = AnalysisResult(
        record_id=record_id,
        analysis_type=AnalysisType.llm,
        error_types=payload.get("error_types") if payload.get("success") else None,
        root_cause=payload.get("root_cause") if payload.get("success") else None,
        severity=_severity_from_str(payload.get("severity")),
        confidence=payload.get("confidence") if payload.get("success") else None,
        evidence=payload.get("evidence") if payload.get("success") else payload.get("error"),
        suggestion=payload.get("suggestion") if payload.get("success") else None,
        llm_model=payload.get("model"),
        llm_cost=float(payload.get("llm_cost") or 0.0),
        prompt_template=prompt_template,
        raw_response={"text": payload.get("raw_response", "")},
        unmatched_tags=payload.get("unmatched_tags") if payload.get("success") else None,
    )
    db.add(analysis)
    await db.flush()

    if not payload.get("success"):
        return

    seen_tags: set[str] = set()
    for tag in payload.get("error_types") or []:
        if tag in seen_tags:
            continue
        seen_tags.add(tag)
        db.add(
            ErrorTag(
                record_id=record_id,
                analysis_result_id=analysis.id,
                tag_path=tag,
                tag_level=min(len(tag.split(".")), 3),
                source=TagSource.llm,
                confidence=payload.get("confidence"),
            )
        )


async def _run_llm_judge_for_session_async(
    session_id: str,
    strategy_id: str,
    job_id: str,
    manual_record_ids: list[str] | None = None,
) -> dict:
    session_uuid = uuid.UUID(session_id)
    strategy_uuid = uuid.UUID(strategy_id)
    manual_uuids = _coerce_uuid_list(manual_record_ids)

    redis = await get_redis()
    progress = ProgressPublisher(redis=redis, job_id=job_id)

    await update_job(redis, job_id, status="running", processed=0, succeeded=0, failed=0, total_cost=0.0)

    try:
        async with get_async_session() as db:
            strategy = await db.get(AnalysisStrategy, strategy_uuid)
            if strategy is None:
                raise ValueError(f"Strategy {strategy_id} not found")
            if not strategy.is_active:
                raise ValueError(f"Strategy {strategy_id} is inactive")

            template_name = "builtin-default"
            template_text = _DEFAULT_TEMPLATE
            if strategy.prompt_template_id is not None:
                template = await db.get(PromptTemplate, strategy.prompt_template_id)
                if template is None:
                    raise ValueError(f"Prompt template {strategy.prompt_template_id} not found")
                if not template.is_active:
                    raise ValueError(f"Prompt template {strategy.prompt_template_id} is inactive")
                template_name = template.name
                template_text = template.template

            provider_name = strategy.llm_provider or "openai"
            model_name = strategy.llm_model or "gpt-4o"
            base_url = None
            if strategy.config and isinstance(strategy.config, dict):
                base_url = strategy.config.get("base_url")
            provider = create_provider(
                provider_name=provider_name,
                api_key=await _resolve_provider_api_key(db, provider_name),
                model=model_name,
                base_url=base_url,
            )

            ruled_record_ids = await _fetch_ruled_record_ids(db, session_id=session_uuid)
            records = await select_records(
                db,
                session_id=session_uuid,
                strategy_type=strategy.strategy_type,
                config=strategy.config or {},
                manual_record_ids=manual_uuids,
                ruled_record_ids=ruled_record_ids,
            )
            total = len(records)

            await update_job(redis, job_id, total=total)

            rule_tags_map = await _fetch_rule_tags_map(db, [record.id for record in records])

            rpm = None
            if strategy.config and isinstance(strategy.config, dict):
                rpm = strategy.config.get("requests_per_minute")
                if rpm is None and strategy.config.get("requests_per_second"):
                    rpm = float(strategy.config["requests_per_second"]) * 60
            requests_per_second = (float(rpm) / 60.0) if rpm else None

            limiter = AsyncRateLimiter(requests_per_second=requests_per_second)
            breaker = CircuitBreaker(
                failure_threshold=int((strategy.config or {}).get("breaker_failure_threshold", 3)),
                recovery_timeout_seconds=float((strategy.config or {}).get("breaker_recovery_seconds", 30.0)),
            )
            budget = BudgetTracker(
                daily_budget=strategy.daily_budget,
                initial_spent=await _get_existing_daily_spend(db, model=model_name),
            )

            started = time.monotonic()
            processed = 0
            succeeded = 0
            failed = 0
            total_cost = 0.0
            stop_reason: str | None = None

            for record in records:
                if budget.exhausted:
                    stop_reason = "budget_exhausted"
                    break
                if not breaker.can_execute():
                    stop_reason = "circuit_open"
                    break

                await limiter.acquire()

                try:
                    payload = await _analyse_single_record(
                        record=record,
                        provider=provider,
                        template=template_text,
                        system_prompt=(strategy.config or {}).get("system_prompt", _DEFAULT_SYSTEM_PROMPT),
                        rule_tags=rule_tags_map.get(str(record.id), []),
                    )
                    breaker.record_success()
                except Exception as exc:  # provider/system failure
                    breaker.record_failure()
                    payload = {
                        "success": False,
                        "record_id": str(record.id),
                        "raw_response": "",
                        "error": str(exc),
                        "llm_cost": 0.0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "model": model_name,
                    }

                record_cost = float(payload.get("llm_cost") or 0.0)
                budget.record_spend(record_cost)
                total_cost += record_cost

                await _persist_llm_result(
                    db,
                    record_id=record.id,
                    payload=payload,
                    prompt_template=template_name,
                )
                await db.commit()

                processed += 1
                if payload.get("success"):
                    succeeded += 1
                else:
                    failed += 1

                elapsed = max(time.monotonic() - started, 1e-6)
                speed = processed / elapsed
                await progress.update(processed=processed, total=total, speed_rps=speed)
                await update_job(
                    redis,
                    job_id,
                    processed=processed,
                    total=total,
                    succeeded=succeeded,
                    failed=failed,
                    total_cost=total_cost,
                    stop_reason=stop_reason,
                    status="running",
                )

            await progress.complete(total_written=succeeded, total_skipped=failed)
            await update_job(
                redis,
                job_id,
                status="done",
                processed=processed,
                total=total,
                succeeded=succeeded,
                failed=failed,
                total_cost=total_cost,
                stop_reason=stop_reason,
            )

            return {
                "job_id": job_id,
                "session_id": session_id,
                "strategy_id": strategy_id,
                "processed": processed,
                "total": total,
                "succeeded": succeeded,
                "failed": failed,
                "total_cost": total_cost,
                "stop_reason": stop_reason,
            }

    except Exception as exc:
        await progress.fail(reason=str(exc))
        await update_job(redis, job_id, status="failed", reason=str(exc))
        raise


@shared_task(name="tasks.analysis.run_llm_judge", bind=True, max_retries=3, default_retry_delay=10)
def run_llm_judge(
    self,
    session_id: str,
    strategy_id: str,
    job_id: str,
    manual_record_ids: list[str] | None = None,
) -> dict:
    """Celery task: run LLM judge on selected records in one session."""
    try:
        return run_async_in_worker(
            _run_llm_judge_for_session_async(
                session_id=session_id,
                strategy_id=strategy_id,
                job_id=job_id,
                manual_record_ids=manual_record_ids,
            )
        )
    except Exception as exc:
        raise self.retry(exc=exc)
