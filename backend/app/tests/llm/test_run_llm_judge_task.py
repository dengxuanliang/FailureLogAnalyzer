import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.analysis_result import AnalysisResult
from app.db.models.analysis_strategy import AnalysisStrategy
from app.db.models.enums import StrategyType
from app.db.models.error_tag import ErrorTag
from app.db.models.prompt_template import PromptTemplate
from app.llm.providers.base import BaseLlmProvider, LlmResponse
from app.tasks.analysis import _FORMAT_REPAIR_SUFFIX, _analyse_single_record


VALID_RESPONSE = '''{
  "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂"],
  "root_cause": "推理链断裂",
  "severity": "high",
  "confidence": 0.9,
  "evidence": "遗漏关键步骤",
  "suggestion": "要求展示中间步骤"
}'''


class StubProvider(BaseLlmProvider):
    def __init__(self, responses: list[LlmResponse]):
        self._responses = responses
        self.calls: list[tuple[str, str]] = []

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LlmResponse:
        self.calls.append((system_prompt, user_prompt))
        if not self._responses:
            raise RuntimeError("no response configured")
        return self._responses.pop(0)


def _make_record(**kwargs):
    defaults = {
        "id": "record-1",
        "question": "What is 2+2?",
        "expected_answer": "4",
        "model_answer": "5",
        "task_category": "math",
    }
    defaults.update(kwargs)

    record = MagicMock()
    for key, value in defaults.items():
        setattr(record, key, value)
    return record


class _FakeDb:
    def __init__(self, strategy: AnalysisStrategy, template: PromptTemplate):
        self._strategy = strategy
        self._template = template
        self.added: list[object] = []
        self.commits = 0

    async def get(self, model, pk):
        if model is AnalysisStrategy and pk == self._strategy.id:
            return self._strategy
        if model is PromptTemplate and pk == self._template.id:
            return self._template
        return None

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", uuid.uuid4())

    async def commit(self):
        self.commits += 1


class _FakeRedis:
    async def publish(self, *_args, **_kwargs):
        return None


@pytest.mark.asyncio
async def test_analyse_single_record_success_path():
    provider = StubProvider([
        LlmResponse(
            text=VALID_RESPONSE,
            prompt_tokens=100,
            completion_tokens=50,
            model="gpt-4o",
        )
    ])

    result = await _analyse_single_record(
        record=_make_record(),
        provider=provider,
        template="Q:{question}\nE:{expected}\nA:{model_answer}\nTags:{rule_tags}",
        system_prompt="judge",
        rule_tags=["推理性错误.数学/计算错误.算术错误"],
    )

    assert result["success"] is True
    assert result["error_types"] == ["推理性错误.逻辑推理错误.前提正确但推理链断裂"]
    assert result["prompt_tokens"] == 100
    assert result["completion_tokens"] == 50
    assert result["llm_cost"] > 0


@pytest.mark.asyncio
async def test_analyse_single_record_retries_with_format_repair_once_on_parse_failure():
    provider = StubProvider([
        LlmResponse(text="not-json", prompt_tokens=10, completion_tokens=5, model="gpt-4o"),
        LlmResponse(text=VALID_RESPONSE, prompt_tokens=8, completion_tokens=4, model="gpt-4o"),
    ])

    result = await _analyse_single_record(
        record=_make_record(),
        provider=provider,
        template="Q:{question}",
        system_prompt="judge",
        rule_tags=[],
    )

    assert result["success"] is True
    assert len(provider.calls) == 2
    assert provider.calls[-1][1].endswith(_FORMAT_REPAIR_SUFFIX)
    assert result["prompt_tokens"] == 18
    assert result["completion_tokens"] == 9


@pytest.mark.asyncio
async def test_analyse_single_record_returns_failure_when_parse_still_fails():
    provider = StubProvider([
        LlmResponse(text="bad", prompt_tokens=1, completion_tokens=1, model="gpt-4o"),
        LlmResponse(text="still bad", prompt_tokens=2, completion_tokens=3, model="gpt-4o"),
    ])

    result = await _analyse_single_record(
        record=_make_record(),
        provider=provider,
        template="Q:{question}",
        system_prompt="judge",
        rule_tags=[],
    )

    assert result["success"] is False
    assert result["raw_response"] == "still bad"
    assert result["prompt_tokens"] == 3
    assert result["completion_tokens"] == 4


@pytest.mark.asyncio
async def test_run_llm_judge_pipeline_persists_results(monkeypatch):
    from app.tasks import analysis as analysis_task

    session_id = uuid.uuid4()
    strategy = AnalysisStrategy(
        id=uuid.uuid4(),
        name="default",
        strategy_type=StrategyType.full,
        config={"requests_per_minute": 10_000},
        llm_provider="openai",
        llm_model="gpt-4o",
        prompt_template_id=uuid.uuid4(),
        max_concurrent=1,
        daily_budget=1.0,
        is_active=True,
        created_by="tester",
    )
    template = PromptTemplate(
        id=strategy.prompt_template_id,
        name="t1",
        benchmark="mmlu",
        template="Q:{question} A:{model_answer}",
        version=1,
        is_active=True,
        created_by="tester",
    )
    fake_db = _FakeDb(strategy, template)

    records = [
        _make_record(id=uuid.uuid4(), question="Q1", model_answer="A1", expected_answer="E1"),
        _make_record(id=uuid.uuid4(), question="Q2", model_answer="A2", expected_answer="E2"),
    ]

    provider = StubProvider([
        LlmResponse(text=VALID_RESPONSE, prompt_tokens=10, completion_tokens=5, model="gpt-4o"),
        LlmResponse(text=VALID_RESPONSE, prompt_tokens=11, completion_tokens=6, model="gpt-4o"),
    ])

    @asynccontextmanager
    async def _fake_session_cm():
        yield fake_db

    monkeypatch.setattr(analysis_task, "get_async_session", _fake_session_cm)
    monkeypatch.setattr(analysis_task, "get_redis", AsyncMock(return_value=_FakeRedis()))
    monkeypatch.setattr(analysis_task, "update_job", AsyncMock(return_value={}))
    monkeypatch.setattr(analysis_task, "create_provider", lambda **_kwargs: provider)
    monkeypatch.setattr(analysis_task, "select_records", AsyncMock(return_value=records))
    monkeypatch.setattr(analysis_task, "_fetch_ruled_record_ids", AsyncMock(return_value=set()))
    monkeypatch.setattr(
        analysis_task,
        "_fetch_rule_tags_map",
        AsyncMock(return_value={str(records[0].id): ["推理性错误.数学/计算错误.算术错误"]}),
    )
    monkeypatch.setattr(analysis_task, "_get_existing_daily_spend", AsyncMock(return_value=0.0))

    summary = await analysis_task._run_llm_judge_for_session_async(
        session_id=str(session_id),
        strategy_id=str(strategy.id),
        job_id=str(uuid.uuid4()),
    )

    assert summary["processed"] == 2
    assert summary["succeeded"] == 2
    assert summary["failed"] == 0
    assert summary["total_cost"] > 0

    analysis_rows = [obj for obj in fake_db.added if isinstance(obj, AnalysisResult)]
    tag_rows = [obj for obj in fake_db.added if isinstance(obj, ErrorTag)]
    assert len(analysis_rows) == 2
    assert len(tag_rows) == 2


@pytest.mark.asyncio
async def test_run_llm_judge_pipeline_stops_when_budget_exhausted(monkeypatch):
    from app.tasks import analysis as analysis_task

    session_id = uuid.uuid4()
    strategy = AnalysisStrategy(
        id=uuid.uuid4(),
        name="budget-stop",
        strategy_type=StrategyType.full,
        config={"requests_per_minute": 10_000},
        llm_provider="openai",
        llm_model="gpt-4o",
        prompt_template_id=uuid.uuid4(),
        max_concurrent=1,
        daily_budget=0.1,
        is_active=True,
        created_by="tester",
    )
    template = PromptTemplate(
        id=strategy.prompt_template_id,
        name="t1",
        benchmark="mmlu",
        template="Q:{question} A:{model_answer}",
        version=1,
        is_active=True,
        created_by="tester",
    )
    fake_db = _FakeDb(strategy, template)

    @asynccontextmanager
    async def _fake_session_cm():
        yield fake_db

    monkeypatch.setattr(analysis_task, "get_async_session", _fake_session_cm)
    monkeypatch.setattr(analysis_task, "get_redis", AsyncMock(return_value=_FakeRedis()))
    monkeypatch.setattr(analysis_task, "update_job", AsyncMock(return_value={}))
    monkeypatch.setattr(analysis_task, "create_provider", lambda **_kwargs: StubProvider([]))
    monkeypatch.setattr(
        analysis_task,
        "select_records",
        AsyncMock(return_value=[_make_record(id=uuid.uuid4(), question="Q", model_answer="A")]),
    )
    monkeypatch.setattr(analysis_task, "_fetch_ruled_record_ids", AsyncMock(return_value=set()))
    monkeypatch.setattr(analysis_task, "_fetch_rule_tags_map", AsyncMock(return_value={}))
    monkeypatch.setattr(analysis_task, "_get_existing_daily_spend", AsyncMock(return_value=0.1))

    summary = await analysis_task._run_llm_judge_for_session_async(
        session_id=str(session_id),
        strategy_id=str(strategy.id),
        job_id=str(uuid.uuid4()),
    )

    assert summary["processed"] == 0
    assert summary["stop_reason"] == "budget_exhausted"
