# LLM Judge Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the LLM Judge Agent — an LLM-powered deep error analysis pipeline with configurable trigger strategies (full / fallback / sampling / manual), prompt template management, multi-provider LLM calling via Celery workers, structured output parsing, cost tracking, circuit breaker resilience, and full REST API for strategies, templates, job control, and cost monitoring.

**Architecture:** Users configure an `AnalysisStrategy` (trigger mode + LLM provider + budget) and bind it to a `PromptTemplate`. When triggered via REST or Orchestrator, a record selector picks which `eval_records` to analyse based on strategy type. A Celery task (`tasks.analysis.run_llm_judge`) fans out individual LLM calls, each rendering the prompt template, calling the LLM provider, parsing the structured JSON response, validating error_types against the taxonomy tree, and writing `analysis_results` + `error_tags` rows. A circuit breaker halts calls after consecutive failures; a budget tracker enforces daily spend limits. Progress and cost are published to Redis for WebSocket relay.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 (async), Celery 5 + Redis, httpx (LLM HTTP client), tiktoken (token counting), tenacity (retry), pytest + pytest-asyncio, factory-boy

---

## Prerequisites (Plans 1 + 3 must be complete)

Plan 1 provides:
- `/backend/app/db/` — SQLAlchemy engine, `Base`, session factories
- `/backend/app/db/session.py` — `get_db_session()` must provide a **sync** `Session` context manager for Celery workers (Celery tasks are synchronous; async session will not work here)
- `/backend/app/models/` — `EvalRecord`, `AnalysisResult`, `ErrorTag`, `AnalysisStrategy`, `PromptTemplate` ORM models
- `/backend/app/core/config.py` — `Settings` with `REDIS_URL`, `CELERY_BROKER_URL`
- `/backend/app/celery_app.py` — Celery application instance
- `/backend/app/api/v1/deps.py` — `get_db`, `require_role` dependencies
- Docker Compose with `postgres`, `redis`, `api`, `worker` services

Plan 3 provides:
- `/backend/app/rules/taxonomy.py` — `TaxonomyTree` for tag path validation
- `/backend/app/rules/base.py` — `RuleResult` dataclass (used for tag comparison)
- `/backend/app/tasks/analysis.py` — existing file where `run_llm_judge` task will be added

---

## File Structure After This Plan

```
backend/app/
  llm/
    __init__.py
    schemas.py            # LlmJudgeOutput, PromptContext Pydantic models
    prompt_renderer.py    # Template variable rendering
    output_parser.py      # JSON parse + taxonomy validation
    record_selector.py    # Strategy-based record selection
    providers/
      __init__.py
      base.py             # BaseLlmProvider ABC
      openai_provider.py  # OpenAI-compatible (OpenAI, local vLLM)
      claude_provider.py  # Anthropic Claude
      registry.py         # provider_registry dict
    circuit_breaker.py    # CircuitBreaker (Redis-backed state)
    rate_limiter.py       # RateLimiter (sliding window, Redis-backed)
    budget_tracker.py     # DailyBudgetTracker (Redis-backed counters)
    cost_calculator.py    # Token counting + cost estimation
  models/
    analysis_strategy.py  # (already exists from Plan 1, verify)
    prompt_template.py    # (already exists from Plan 1, verify)
  schemas/
    strategy.py           # Pydantic schemas for strategy CRUD
    prompt_template.py    # Pydantic schemas for template CRUD
    llm_job.py            # Pydantic schemas for job trigger/status
  tasks/
    analysis.py           # (extend) add run_llm_judge task
  api/v1/routers/
    llm_strategies.py     # CRUD /api/v1/llm/strategies
    llm_templates.py      # CRUD /api/v1/llm/prompt-templates
    llm_jobs.py           # POST /trigger, GET /jobs, GET /jobs/{id}/status, GET /cost-summary

tests/
  llm/
    test_prompt_renderer.py
    test_output_parser.py
    test_record_selector.py
    test_circuit_breaker.py
    test_rate_limiter.py
    test_budget_tracker.py
    test_cost_calculator.py
    test_openai_provider.py
    test_claude_provider.py
    test_run_llm_judge_task.py
  api/
    test_llm_strategies_api.py
    test_llm_templates_api.py
    test_llm_jobs_api.py
```

---

## Phase 1 — LLM Output Schema & Prompt Renderer

### Task 1.1 — Write failing test for LlmJudgeOutput and PromptContext

**Files:**
- Create: `backend/tests/llm/test_prompt_renderer.py`
- Create: `backend/app/llm/schemas.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_prompt_renderer.py
import pytest
from pydantic import ValidationError
from app.llm.schemas import LlmJudgeOutput, PromptContext
from app.llm.prompt_renderer import render_prompt


# ---- LlmJudgeOutput --------------------------------------------------------

def test_llm_judge_output_valid():
    out = LlmJudgeOutput(
        error_types=["推理性错误.逻辑推理错误.前提正确但推理链断裂"],
        root_cause="模型在第3步推理时错误地将充分条件当作必要条件",
        severity="high",
        confidence=0.85,
        evidence="模型回答中'因为A所以必然B'",
        suggestion="加强逻辑推理训练数据中条件关系的多样性",
    )
    assert out.severity == "high"
    assert len(out.error_types) == 1


def test_llm_judge_output_severity_enum():
    with pytest.raises(ValidationError):
        LlmJudgeOutput(
            error_types=["x"], root_cause="x",
            severity="invalid",  # must be high/medium/low
            confidence=0.5, evidence="x", suggestion="x",
        )


def test_llm_judge_output_confidence_bounds():
    with pytest.raises(ValidationError):
        LlmJudgeOutput(
            error_types=["x"], root_cause="x",
            severity="low", confidence=1.5,  # > 1.0
            evidence="x", suggestion="x",
        )


# ---- PromptContext ----------------------------------------------------------

def test_prompt_context_fields():
    ctx = PromptContext(
        question="What is 2+2?",
        expected="4",
        model_answer="5",
        rule_tags=["推理性错误.数学/计算错误.算术错误"],
        task_category="math",
    )
    assert ctx.question == "What is 2+2?"


# ---- render_prompt ----------------------------------------------------------

def test_render_prompt_substitutes_variables():
    template = "Question: {question}\nExpected: {expected}\nAnswer: {model_answer}\nRule tags: {rule_tags}\nCategory: {task_category}"
    ctx = PromptContext(
        question="What is 2+2?",
        expected="4",
        model_answer="5",
        rule_tags=["数学错误"],
        task_category="math",
    )
    result = render_prompt(template, ctx)
    assert "What is 2+2?" in result
    assert "数学错误" in result
    assert "{question}" not in result


def test_render_prompt_missing_variable_left_as_is():
    template = "Q: {question} Extra: {nonexistent}"
    ctx = PromptContext(
        question="test", expected="a", model_answer="b",
        rule_tags=[], task_category="",
    )
    result = render_prompt(template, ctx)
    assert "test" in result
    assert "{nonexistent}" in result  # unknown vars untouched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_prompt_renderer.py -x`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.llm'`

### Task 1.2 — Implement schemas and prompt renderer

- [ ] **Step 3: Create `__init__.py` files**

```bash
mkdir -p backend/app/llm/providers backend/tests/llm
touch backend/app/llm/__init__.py backend/app/llm/providers/__init__.py backend/tests/llm/__init__.py
```

- [ ] **Step 4: Write `app/llm/schemas.py`**

```python
# backend/app/llm/schemas.py
"""Pydantic models for LLM Judge input/output."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class Severity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class LlmJudgeOutput(BaseModel):
    """Structured output expected from the LLM Judge."""
    error_types: list[str] = Field(..., min_length=1)
    root_cause: str
    severity: Severity
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: str
    suggestion: str


class PromptContext(BaseModel):
    """Variables available for prompt template rendering."""
    question: str
    expected: str
    model_answer: str
    rule_tags: list[str] = Field(default_factory=list)
    task_category: str = ""
```

- [ ] **Step 5: Write `app/llm/prompt_renderer.py`**

```python
# backend/app/llm/prompt_renderer.py
"""Render a prompt template with PromptContext variables."""
from __future__ import annotations
from app.llm.schemas import PromptContext


def render_prompt(template: str, ctx: PromptContext) -> str:
    """Substitute known variables in template. Unknown placeholders are left as-is."""
    mapping = {
        "question": ctx.question,
        "expected": ctx.expected,
        "model_answer": ctx.model_answer,
        "rule_tags": ", ".join(ctx.rule_tags) if ctx.rule_tags else "(none)",
        "task_category": ctx.task_category or "(unknown)",
    }
    result = template
    for key, value in mapping.items():
        result = result.replace("{" + key + "}", value)
    return result
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_prompt_renderer.py -x -v`
Expected: 6 passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/llm/ backend/tests/llm/
git commit -m "feat(llm): add LlmJudgeOutput, PromptContext schemas and prompt renderer"
```

---

## Phase 2 — Output Parser with Taxonomy Validation

### Task 2.1 — Write failing test for output parser

**Files:**
- Create: `backend/tests/llm/test_output_parser.py`
- Create: `backend/app/llm/output_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_output_parser.py
import pytest
from app.llm.output_parser import parse_llm_response, LlmParseResult


VALID_JSON = '''{
    "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂"],
    "root_cause": "模型推理链断裂",
    "severity": "high",
    "confidence": 0.85,
    "evidence": "模型回答中推理步骤缺失",
    "suggestion": "增加训练数据"
}'''

INVALID_JSON = "This is not JSON at all."

PARTIAL_JSON = '''{
    "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂"],
    "root_cause": "test",
    "severity": "high",
    "confidence": 0.85,
    "evidence": "test",
'''  # truncated

VALID_JSON_UNKNOWN_TAG = '''{
    "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂", "完全不存在的分类.子分类"],
    "root_cause": "test",
    "severity": "medium",
    "confidence": 0.7,
    "evidence": "test",
    "suggestion": "test"
}'''

MARKDOWN_WRAPPED = '''```json
{
    "error_types": ["格式与规范错误.空回答/拒绝回答"],
    "root_cause": "空回答",
    "severity": "low",
    "confidence": 0.95,
    "evidence": "answer is empty",
    "suggestion": "none"
}
```'''


def test_parse_valid_json():
    result = parse_llm_response(VALID_JSON)
    assert result.success is True
    assert result.output is not None
    assert result.output.severity.value == "high"
    assert result.unmatched_tags == []


def test_parse_invalid_json():
    result = parse_llm_response(INVALID_JSON)
    assert result.success is False
    assert result.output is None
    assert result.raw_text == INVALID_JSON


def test_parse_truncated_json():
    result = parse_llm_response(PARTIAL_JSON)
    assert result.success is False


def test_parse_unknown_tags_flagged():
    result = parse_llm_response(VALID_JSON_UNKNOWN_TAG)
    assert result.success is True
    assert "完全不存在的分类.子分类" in result.unmatched_tags
    # Known tag should not be in unmatched
    assert "推理性错误.逻辑推理错误.前提正确但推理链断裂" not in result.unmatched_tags


def test_parse_markdown_wrapped_json():
    result = parse_llm_response(MARKDOWN_WRAPPED)
    assert result.success is True
    assert result.output is not None
    assert result.output.root_cause == "空回答"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_output_parser.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 2.2 — Implement output parser

- [ ] **Step 3: Write `app/llm/output_parser.py`**

```python
# backend/app/llm/output_parser.py
"""Parse and validate LLM Judge JSON output."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from pydantic import ValidationError
from app.llm.schemas import LlmJudgeOutput
from app.rules.taxonomy import TaxonomyTree


@dataclass
class LlmParseResult:
    success: bool
    output: Optional[LlmJudgeOutput] = None
    unmatched_tags: list[str] = field(default_factory=list)
    raw_text: str = ""
    error: str = ""


_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _extract_json_block(text: str) -> str:
    """Strip markdown code fences if present."""
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def parse_llm_response(
    raw: str,
    taxonomy: Optional[TaxonomyTree] = None,
) -> LlmParseResult:
    """
    Parse raw LLM text into LlmJudgeOutput.

    Steps:
    1. Strip markdown fences
    2. JSON-decode
    3. Pydantic validation
    4. Validate error_types against taxonomy tree
    """
    if taxonomy is None:
        taxonomy = TaxonomyTree.load_default()

    cleaned = _extract_json_block(raw)

    # JSON decode
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        return LlmParseResult(
            success=False, raw_text=raw,
            error=f"JSON decode error: {exc}",
        )

    # Pydantic validation
    try:
        output = LlmJudgeOutput(**data)
    except ValidationError as exc:
        return LlmParseResult(
            success=False, raw_text=raw,
            error=f"Validation error: {exc}",
        )

    # Taxonomy validation
    unmatched: list[str] = []
    for tag_path in output.error_types:
        if taxonomy.resolve_path(tag_path) is None:
            unmatched.append(tag_path)

    return LlmParseResult(
        success=True,
        output=output,
        unmatched_tags=unmatched,
        raw_text=raw,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_output_parser.py -x -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/output_parser.py backend/tests/llm/test_output_parser.py
git commit -m "feat(llm): add output parser with markdown stripping and taxonomy validation"
```

---

## Phase 3 — LLM Providers (OpenAI + Claude)

### Task 3.1 — Write failing test for provider interface and OpenAI provider

**Files:**
- Create: `backend/tests/llm/test_openai_provider.py`
- Create: `backend/app/llm/providers/base.py`
- Create: `backend/app/llm/providers/openai_provider.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_openai_provider.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.llm.providers.base import BaseLlmProvider, LlmResponse
from app.llm.providers.openai_provider import OpenAIProvider


def test_base_provider_is_abstract():
    with pytest.raises(TypeError):
        BaseLlmProvider()


def test_llm_response_fields():
    resp = LlmResponse(
        text='{"error_types":["x"]}',
        prompt_tokens=100,
        completion_tokens=50,
        model="gpt-4o",
    )
    assert resp.total_tokens == 150


@pytest.mark.asyncio
async def test_openai_provider_call_success():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"result": "ok"}'
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.model = "gpt-4o"

    provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
    with patch.object(provider, "_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        resp = await provider.call(
            system_prompt="You are a judge.",
            user_prompt="Analyze this error.",
        )
    assert resp.text == '{"result": "ok"}'
    assert resp.total_tokens == 150
    assert resp.model == "gpt-4o"


@pytest.mark.asyncio
async def test_openai_provider_handles_api_error():
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
    with patch.object(provider, "_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )
        with pytest.raises(Exception, match="API rate limit"):
            await provider.call(
                system_prompt="test",
                user_prompt="test",
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_openai_provider.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 3.2 — Implement BaseLlmProvider and OpenAIProvider

- [ ] **Step 3: Write `app/llm/providers/base.py`**

```python
# backend/app/llm/providers/base.py
"""Abstract base for LLM providers."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LlmResponse:
    """Normalized response from any LLM provider."""
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BaseLlmProvider(ABC):
    """Interface that all LLM providers must implement."""

    @abstractmethod
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LlmResponse:
        ...
```

- [ ] **Step 4: Write `app/llm/providers/openai_provider.py`**

```python
# backend/app/llm/providers/openai_provider.py
"""OpenAI-compatible LLM provider (works with OpenAI API and local vLLM)."""
from __future__ import annotations
from typing import Optional

from app.llm.providers.base import BaseLlmProvider, LlmResponse

try:
    from openai import AsyncOpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


class OpenAIProvider(BaseLlmProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
    ) -> None:
        if not _OPENAI_AVAILABLE:
            raise ImportError("openai package is required: pip install openai")
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LlmResponse:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        return LlmResponse(
            text=choice.message.content or "",
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            model=response.model,
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_openai_provider.py -x -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/llm/providers/ backend/tests/llm/test_openai_provider.py
git commit -m "feat(llm): add BaseLlmProvider interface and OpenAI provider"
```

### Task 3.3 — Claude provider

**Files:**
- Create: `backend/tests/llm/test_claude_provider.py`
- Create: `backend/app/llm/providers/claude_provider.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_claude_provider.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.llm.providers.claude_provider import ClaudeProvider


@pytest.mark.asyncio
async def test_claude_provider_call_success():
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = '{"result": "ok"}'
    mock_response.usage.input_tokens = 80
    mock_response.usage.output_tokens = 40
    mock_response.model = "claude-sonnet-4-20250514"

    provider = ClaudeProvider(api_key="test-key", model="claude-sonnet-4-20250514")
    with patch.object(provider, "_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        resp = await provider.call(
            system_prompt="You are a judge.",
            user_prompt="Analyze this error.",
        )
    assert resp.text == '{"result": "ok"}'
    assert resp.total_tokens == 120
    assert resp.model == "claude-sonnet-4-20250514"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_claude_provider.py -x`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `app/llm/providers/claude_provider.py`**

```python
# backend/app/llm/providers/claude_provider.py
"""Anthropic Claude LLM provider."""
from __future__ import annotations
from typing import Optional

from app.llm.providers.base import BaseLlmProvider, LlmResponse

try:
    from anthropic import AsyncAnthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


class ClaudeProvider(BaseLlmProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: Optional[str] = None,
    ) -> None:
        if not _ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package is required: pip install anthropic")
        self._client = AsyncAnthropic(api_key=api_key, base_url=base_url)
        self._model = model

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LlmResponse:
        response = await self._client.messages.create(
            model=self._model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.content[0].text if response.content else ""
        return LlmResponse(
            text=text,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            model=response.model,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_claude_provider.py -x -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/providers/claude_provider.py backend/tests/llm/test_claude_provider.py
git commit -m "feat(llm): add Claude (Anthropic) LLM provider"
```

### Task 3.4 — Provider registry

**Files:**
- Create: `backend/app/llm/providers/registry.py`

- [ ] **Step 1: Write `app/llm/providers/registry.py`**

```python
# backend/app/llm/providers/registry.py
"""Resolve LLM provider by name string from strategy config."""
from __future__ import annotations
from typing import Optional
from app.llm.providers.base import BaseLlmProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.claude_provider import ClaudeProvider


def create_provider(
    provider_name: str,
    api_key: str,
    model: str,
    base_url: Optional[str] = None,
) -> BaseLlmProvider:
    """Factory: create an LLM provider instance from config strings.

    Args:
        provider_name: One of 'openai', 'claude', 'local'.
        api_key: API key for the provider.
        model: Model name (e.g. 'gpt-4o', 'claude-sonnet-4-20250514').
        base_url: Override base URL (for local/vLLM deployments).
    """
    name = provider_name.lower()
    if name in ("openai", "local"):
        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
    if name == "claude":
        return ClaudeProvider(api_key=api_key, model=model, base_url=base_url)
    raise ValueError(f"Unknown LLM provider: {provider_name!r}. Supported: openai, claude, local")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/llm/providers/registry.py
git commit -m "feat(llm): add provider registry factory"
```

---

## Phase 4 — Circuit Breaker & Budget Tracker

### Task 4.1 — Write failing test for circuit breaker

**Files:**
- Create: `backend/tests/llm/test_circuit_breaker.py`
- Create: `backend/app/llm/circuit_breaker.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_circuit_breaker.py
import pytest
import time
from unittest.mock import MagicMock
from app.llm.circuit_breaker import CircuitBreaker, CircuitOpenError


@pytest.fixture
def breaker():
    """In-memory circuit breaker for tests (no Redis)."""
    return CircuitBreaker(
        failure_threshold=3,
        cooldown_seconds=1,
        backend="memory",
    )


def test_initial_state_is_closed(breaker):
    assert breaker.is_closed()


def test_stays_closed_under_threshold(breaker):
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_closed()


def test_opens_after_threshold(breaker):
    for _ in range(3):
        breaker.record_failure()
    assert not breaker.is_closed()


def test_raises_when_open(breaker):
    for _ in range(3):
        breaker.record_failure()
    with pytest.raises(CircuitOpenError):
        breaker.check()


def test_resets_after_cooldown(breaker):
    for _ in range(3):
        breaker.record_failure()
    assert not breaker.is_closed()
    time.sleep(1.1)  # cooldown = 1s
    assert breaker.is_closed()


def test_record_success_resets_count(breaker):
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_success()
    assert breaker.is_closed()
    # Another failure should not open (count reset)
    breaker.record_failure()
    assert breaker.is_closed()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_circuit_breaker.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 4.2 — Implement circuit breaker

- [ ] **Step 3: Write `app/llm/circuit_breaker.py`**

```python
# backend/app/llm/circuit_breaker.py
"""Circuit breaker for LLM API calls (memory or Redis-backed)."""
from __future__ import annotations
import time
from typing import Optional


class CircuitOpenError(Exception):
    """Raised when attempting a call while the circuit is open."""
    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"Circuit open. Retry after {retry_after:.1f}s")


class CircuitBreaker:
    """
    Simple circuit breaker.

    States:
    - CLOSED: requests pass through, failures counted
    - OPEN: requests rejected, transitions to CLOSED after cooldown

    Args:
        failure_threshold: consecutive failures before opening (spec: 5)
        cooldown_seconds: seconds to stay open (spec: 60)
        backend: 'memory' for in-process or 'redis' for distributed
        redis_client: required if backend='redis'
        key_prefix: Redis key namespace
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: int = 60,
        backend: str = "memory",
        redis_client: Optional[object] = None,
        key_prefix: str = "cb:llm",
    ) -> None:
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._backend = backend

        if backend == "memory":
            self._failure_count = 0
            self._opened_at: Optional[float] = None
        elif backend == "redis":
            if redis_client is None:
                raise ValueError("redis_client required for backend='redis'")
            self._redis = redis_client
            self._key_count = f"{key_prefix}:fail_count"
            self._key_opened = f"{key_prefix}:opened_at"
        else:
            raise ValueError(f"Unknown backend: {backend}")

    # ---- state queries ---------------------------------------------------

    def is_closed(self) -> bool:
        if self._backend == "memory":
            if self._opened_at is not None:
                if time.monotonic() - self._opened_at >= self._cooldown:
                    self._reset()
                    return True
                return False
            return self._failure_count < self._threshold
        # Redis path
        opened_at = self._redis.get(self._key_opened)
        if opened_at is not None:
            if time.time() - float(opened_at) >= self._cooldown:
                self._reset()
                return True
            return False
        count = int(self._redis.get(self._key_count) or 0)
        return count < self._threshold

    def check(self) -> None:
        """Raise CircuitOpenError if circuit is open."""
        if not self.is_closed():
            if self._backend == "memory" and self._opened_at:
                remaining = self._cooldown - (time.monotonic() - self._opened_at)
            else:
                remaining = self._cooldown
            raise CircuitOpenError(retry_after=max(0, remaining))

    # ---- recording -------------------------------------------------------

    def record_failure(self) -> None:
        if self._backend == "memory":
            self._failure_count += 1
            if self._failure_count >= self._threshold and self._opened_at is None:
                self._opened_at = time.monotonic()
        else:
            count = self._redis.incr(self._key_count)
            if count >= self._threshold:
                self._redis.set(self._key_opened, str(time.time()))

    def record_success(self) -> None:
        self._reset()

    # ---- internal --------------------------------------------------------

    def _reset(self) -> None:
        if self._backend == "memory":
            self._failure_count = 0
            self._opened_at = None
        else:
            self._redis.delete(self._key_count, self._key_opened)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_circuit_breaker.py -x -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/circuit_breaker.py backend/tests/llm/test_circuit_breaker.py
git commit -m "feat(llm): add circuit breaker for LLM API calls"
```

### Task 4.3 — Write failing test for budget tracker

**Files:**
- Create: `backend/tests/llm/test_budget_tracker.py`
- Create: `backend/app/llm/budget_tracker.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_budget_tracker.py
import pytest
from app.llm.budget_tracker import DailyBudgetTracker, BudgetExhaustedError


@pytest.fixture
def tracker():
    """In-memory budget tracker for tests."""
    return DailyBudgetTracker(
        daily_limit=10.0,
        backend="memory",
    )


def test_initial_spend_is_zero(tracker):
    assert tracker.current_spend() == 0.0


def test_record_cost_adds_up(tracker):
    tracker.record_cost(2.50)
    tracker.record_cost(3.00)
    assert tracker.current_spend() == pytest.approx(5.50)


def test_remaining_budget(tracker):
    tracker.record_cost(7.0)
    assert tracker.remaining() == pytest.approx(3.0)


def test_check_raises_when_exhausted(tracker):
    tracker.record_cost(10.0)
    with pytest.raises(BudgetExhaustedError):
        tracker.check()


def test_check_passes_under_limit(tracker):
    tracker.record_cost(5.0)
    tracker.check()  # should not raise


def test_zero_limit_always_exhausted():
    tracker = DailyBudgetTracker(daily_limit=0.0, backend="memory")
    # 0 limit means LLM disabled
    with pytest.raises(BudgetExhaustedError):
        tracker.check()


def test_negative_limit_disables_budget():
    tracker = DailyBudgetTracker(daily_limit=-1.0, backend="memory")
    tracker.record_cost(999999.0)
    tracker.check()  # negative limit = unlimited, should not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_budget_tracker.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 4.4 — Implement budget tracker

- [ ] **Step 3: Write `app/llm/budget_tracker.py`**

```python
# backend/app/llm/budget_tracker.py
"""Daily budget tracker for LLM API spend (memory or Redis-backed)."""
from __future__ import annotations
from datetime import date
from typing import Optional


class BudgetExhaustedError(Exception):
    """Raised when daily LLM budget has been reached."""
    def __init__(self, limit: float, spent: float) -> None:
        self.limit = limit
        self.spent = spent
        super().__init__(f"Daily budget exhausted: ${spent:.4f} / ${limit:.2f}")


class DailyBudgetTracker:
    """
    Track daily LLM spend against a configurable limit.

    Args:
        daily_limit: Max USD per day. 0 = disabled. Negative = unlimited.
        backend: 'memory' or 'redis'.
        redis_client: required if backend='redis'.
        key_prefix: Redis key namespace.
    """

    def __init__(
        self,
        daily_limit: float,
        backend: str = "memory",
        redis_client: Optional[object] = None,
        key_prefix: str = "budget:llm",
    ) -> None:
        self._limit = daily_limit
        self._backend = backend

        if backend == "memory":
            self._spend: float = 0.0
            self._date: str = str(date.today())
        elif backend == "redis":
            if redis_client is None:
                raise ValueError("redis_client required for backend='redis'")
            self._redis = redis_client
            self._key_prefix = key_prefix
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def _redis_key(self) -> str:
        return f"{self._key_prefix}:{date.today()}"

    def current_spend(self) -> float:
        if self._backend == "memory":
            today = str(date.today())
            if self._date != today:
                self._spend = 0.0
                self._date = today
            return self._spend
        raw = self._redis.get(self._redis_key())
        return float(raw) if raw else 0.0

    def remaining(self) -> float:
        if self._limit < 0:
            return float("inf")
        return max(0.0, self._limit - self.current_spend())

    def record_cost(self, cost_usd: float) -> None:
        if self._backend == "memory":
            today = str(date.today())
            if self._date != today:
                self._spend = 0.0
                self._date = today
            self._spend += cost_usd
        else:
            key = self._redis_key()
            self._redis.incrbyfloat(key, cost_usd)
            self._redis.expire(key, 86400 * 2)  # auto-cleanup after 2 days

    def check(self) -> None:
        """Raise BudgetExhaustedError if limit reached."""
        if self._limit < 0:
            return  # unlimited
        spent = self.current_spend()
        if spent >= self._limit:
            raise BudgetExhaustedError(limit=self._limit, spent=spent)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_budget_tracker.py -x -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/budget_tracker.py backend/tests/llm/test_budget_tracker.py
git commit -m "feat(llm): add daily budget tracker for LLM cost control"
```

### Task 4.5 — Write failing test for rate limiter

**Files:**
- Create: `backend/tests/llm/test_rate_limiter.py`
- Create: `backend/app/llm/rate_limiter.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_rate_limiter.py
import pytest
import time
from app.llm.rate_limiter import RateLimiter, RateLimitExceededError


@pytest.fixture
def limiter():
    """In-memory rate limiter: 3 requests per 1 second."""
    return RateLimiter(
        max_requests_per_minute=180,  # = 3/sec for testing
        backend="memory",
    )


def test_allows_requests_under_limit():
    limiter = RateLimiter(max_requests_per_minute=60, backend="memory")
    limiter.acquire()  # should not raise


def test_blocks_after_limit():
    limiter = RateLimiter(max_requests_per_minute=2, backend="memory")
    limiter.acquire()
    limiter.acquire()
    with pytest.raises(RateLimitExceededError):
        limiter.acquire()


def test_resets_after_window():
    limiter = RateLimiter(max_requests_per_minute=2, backend="memory", _window_seconds=1)
    limiter.acquire()
    limiter.acquire()
    time.sleep(1.1)
    limiter.acquire()  # should not raise after window reset


def test_wait_blocks_until_available():
    limiter = RateLimiter(max_requests_per_minute=2, backend="memory", _window_seconds=1)
    limiter.acquire()
    limiter.acquire()
    start = time.monotonic()
    limiter.wait_and_acquire(timeout=2.0)
    elapsed = time.monotonic() - start
    assert elapsed >= 0.9  # waited ~1s for window reset
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_rate_limiter.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 4.6 — Implement rate limiter

- [ ] **Step 3: Write `app/llm/rate_limiter.py`**

```python
# backend/app/llm/rate_limiter.py
"""Sliding window rate limiter for LLM API calls (memory or Redis-backed)."""
from __future__ import annotations
import time
from typing import Optional


class RateLimitExceededError(Exception):
    """Raised when per-minute rate limit is exceeded."""
    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        super().__init__(f"Rate limit exceeded: {limit} requests per {window}s window")


class RateLimiter:
    """
    Sliding-window rate limiter.

    Args:
        max_requests_per_minute: Max API calls per minute.
        backend: 'memory' or 'redis'.
        redis_client: required if backend='redis'.
        key_prefix: Redis key namespace.
        _window_seconds: Override window size (default 60, lower for tests).
    """

    def __init__(
        self,
        max_requests_per_minute: int,
        backend: str = "memory",
        redis_client: Optional[object] = None,
        key_prefix: str = "rl:llm",
        _window_seconds: float = 60.0,
    ) -> None:
        self._limit = max_requests_per_minute
        self._window = _window_seconds
        self._backend = backend

        if backend == "memory":
            self._timestamps: list[float] = []
        elif backend == "redis":
            if redis_client is None:
                raise ValueError("redis_client required for backend='redis'")
            self._redis = redis_client
            self._key = f"{key_prefix}:timestamps"
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def _cleanup(self) -> None:
        """Remove timestamps outside the current window."""
        cutoff = time.monotonic() - self._window
        if self._backend == "memory":
            self._timestamps = [t for t in self._timestamps if t > cutoff]

    def acquire(self) -> None:
        """Record a request. Raises RateLimitExceededError if limit reached."""
        self._cleanup()
        if self._backend == "memory":
            if len(self._timestamps) >= self._limit:
                raise RateLimitExceededError(limit=self._limit, window=self._window)
            self._timestamps.append(time.monotonic())
        else:
            # Redis: use sorted set with scores as timestamps
            now = time.time()
            cutoff = now - self._window
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(self._key, 0, cutoff)
            pipe.zcard(self._key)
            pipe.zadd(self._key, {str(now): now})
            pipe.expire(self._key, int(self._window) + 10)
            results = pipe.execute()
            count = results[1]
            if count >= self._limit:
                # Remove the just-added entry
                self._redis.zrem(self._key, str(now))
                raise RateLimitExceededError(limit=self._limit, window=self._window)

    def wait_and_acquire(self, timeout: float = 30.0) -> None:
        """Block until a slot is available, then acquire."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self.acquire()
                return
            except RateLimitExceededError:
                time.sleep(0.1)
        raise RateLimitExceededError(limit=self._limit, window=self._window)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_rate_limiter.py -x -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/rate_limiter.py backend/tests/llm/test_rate_limiter.py
git commit -m "feat(llm): add sliding window rate limiter for LLM API calls"
```

---

## Phase 5 — Cost Calculator

### Task 5.1 — Write failing test for cost calculator

**Files:**
- Create: `backend/tests/llm/test_cost_calculator.py`
- Create: `backend/app/llm/cost_calculator.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_cost_calculator.py
import pytest
from app.llm.cost_calculator import estimate_cost


def test_gpt4o_cost():
    cost = estimate_cost(
        model="gpt-4o",
        prompt_tokens=1000,
        completion_tokens=500,
    )
    # gpt-4o: $2.50/1M input, $10.00/1M output (as of 2025)
    expected = (1000 * 2.50 / 1_000_000) + (500 * 10.00 / 1_000_000)
    assert cost == pytest.approx(expected, rel=0.01)


def test_claude_sonnet_cost():
    cost = estimate_cost(
        model="claude-sonnet-4-20250514",
        prompt_tokens=1000,
        completion_tokens=500,
    )
    # claude-sonnet-4: $3/1M input, $15/1M output
    expected = (1000 * 3.0 / 1_000_000) + (500 * 15.0 / 1_000_000)
    assert cost == pytest.approx(expected, rel=0.01)


def test_unknown_model_returns_zero():
    cost = estimate_cost(
        model="unknown-model-xyz",
        prompt_tokens=1000,
        completion_tokens=500,
    )
    assert cost == 0.0


def test_zero_tokens_returns_zero():
    assert estimate_cost("gpt-4o", 0, 0) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_cost_calculator.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 5.2 — Implement cost calculator

- [ ] **Step 3: Write `app/llm/cost_calculator.py`**

```python
# backend/app/llm/cost_calculator.py
"""Estimate USD cost from token counts and model name."""
from __future__ import annotations

# Prices in USD per 1M tokens: (input_price, output_price)
_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    # Anthropic
    "claude-opus-4-20250514": (15.00, 75.00),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-haiku-4-20250514": (0.80, 4.00),
}


def _match_model(model: str) -> tuple[float, float] | None:
    """Try exact match first, then prefix match."""
    if model in _PRICING:
        return _PRICING[model]
    for key, prices in _PRICING.items():
        if model.startswith(key.rsplit("-", 1)[0]):
            return prices
    return None


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Return estimated cost in USD. Returns 0.0 for unknown models."""
    prices = _match_model(model)
    if prices is None:
        return 0.0
    input_price, output_price = prices
    return (prompt_tokens * input_price / 1_000_000) + (completion_tokens * output_price / 1_000_000)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_cost_calculator.py -x -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/cost_calculator.py backend/tests/llm/test_cost_calculator.py
git commit -m "feat(llm): add cost calculator with model pricing table"
```

---

## Phase 6 — Record Selector (Strategy-Based)

### Task 6.1 — Write failing test for record selector

**Files:**
- Create: `backend/tests/llm/test_record_selector.py`
- Create: `backend/app/llm/record_selector.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_record_selector.py
import pytest
from unittest.mock import MagicMock
from app.llm.record_selector import select_records


def _make_record(id: str, is_correct: bool, has_rule_tags: bool = False):
    rec = MagicMock()
    rec.id = id
    rec.is_correct = is_correct
    rec.session_id = "session-1"
    # Simulate whether rule analysis already tagged this record
    rec.has_rule_tags = has_rule_tags
    return rec


@pytest.fixture
def error_records():
    """10 error records, 5 with rule tags, 5 without."""
    records = []
    for i in range(10):
        records.append(_make_record(
            id=f"r{i}",
            is_correct=False,
            has_rule_tags=(i < 5),
        ))
    return records


def test_full_strategy_returns_all_errors(error_records):
    result = select_records(
        records=error_records,
        strategy_type="full",
        config={},
    )
    assert len(result) == 10


def test_fallback_strategy_returns_untagged_only(error_records):
    result = select_records(
        records=error_records,
        strategy_type="fallback",
        config={},
    )
    # Only records without rule tags
    assert len(result) == 5
    assert all(not r.has_rule_tags for r in result)


def test_sampling_strategy_respects_rate(error_records):
    result = select_records(
        records=error_records,
        strategy_type="sampling",
        config={"sample_rate": 0.3, "seed": 42},
    )
    # 30% of 10 = 3
    assert len(result) == 3


def test_manual_strategy_filters_by_ids(error_records):
    result = select_records(
        records=error_records,
        strategy_type="manual",
        config={"record_ids": ["r0", "r3", "r7"]},
    )
    assert len(result) == 3
    ids = {r.id for r in result}
    assert ids == {"r0", "r3", "r7"}


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="Unknown strategy"):
        select_records([], strategy_type="bogus", config={})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_record_selector.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 6.2 — Implement record selector

- [ ] **Step 3: Write `app/llm/record_selector.py`**

```python
# backend/app/llm/record_selector.py
"""Select which eval_records should go through LLM analysis based on strategy."""
from __future__ import annotations
import math
import random
from typing import Any


def select_records(
    records: list,
    strategy_type: str,
    config: dict[str, Any],
) -> list:
    """
    Filter/sample records according to strategy_type.

    Args:
        records: List of record objects (must have .id and .has_rule_tags attrs).
        strategy_type: One of 'full', 'fallback', 'sampling', 'manual'.
        config: Strategy-specific parameters.
    """
    stype = strategy_type.lower()

    if stype == "full":
        return list(records)

    if stype == "fallback":
        return [r for r in records if not r.has_rule_tags]

    if stype == "sampling":
        rate = float(config.get("sample_rate", 0.1))
        seed = config.get("seed")
        count = max(1, math.ceil(len(records) * rate))
        rng = random.Random(seed)
        if count >= len(records):
            return list(records)
        return rng.sample(records, count)

    if stype == "manual":
        ids = set(config.get("record_ids", []))
        return [r for r in records if r.id in ids]

    raise ValueError(f"Unknown strategy type: {strategy_type!r}. Supported: full, fallback, sampling, manual")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_record_selector.py -x -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/record_selector.py backend/tests/llm/test_record_selector.py
git commit -m "feat(llm): add strategy-based record selector (full/fallback/sampling/manual)"
```

---

## Phase 7 — Celery Task: `tasks.analysis.run_llm_judge`

### Task 7.1 — Write failing test for run_llm_judge core logic

**Files:**
- Create: `backend/tests/llm/test_run_llm_judge_task.py`
- Modify: `backend/app/tasks/analysis.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/llm/test_run_llm_judge_task.py
"""Unit tests for run_llm_judge — mock LLM provider, test end-to-end logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tasks.analysis import _analyse_single_record
from app.llm.providers.base import LlmResponse
from app.llm.schemas import PromptContext


VALID_LLM_RESPONSE = '''{
    "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂"],
    "root_cause": "推理链断裂",
    "severity": "high",
    "confidence": 0.85,
    "evidence": "步骤3推理错误",
    "suggestion": "增加训练数据"
}'''


def _make_record(**kwargs):
    defaults = dict(
        id="record-uuid-1",
        session_id="session-uuid-1",
        question="What is 2+2?",
        expected_answer="4",
        model_answer="5",
        extracted_code=None,
        task_category="math",
        metadata={},
    )
    defaults.update(kwargs)
    rec = MagicMock()
    for k, v in defaults.items():
        setattr(rec, k, v)
    return rec


@pytest.mark.asyncio
async def test_analyse_single_record_success():
    mock_provider = AsyncMock()
    mock_provider.call.return_value = LlmResponse(
        text=VALID_LLM_RESPONSE,
        prompt_tokens=500,
        completion_tokens=200,
        model="gpt-4o",
    )
    record = _make_record()

    result = await _analyse_single_record(
        record=record,
        provider=mock_provider,
        template="Q: {question}\nExpected: {expected}\nAnswer: {model_answer}",
        system_prompt="You are an LLM Judge.",
        rule_tags=[],
    )

    assert result["success"] is True
    assert result["error_types"] == ["推理性错误.逻辑推理错误.前提正确但推理链断裂"]
    assert result["llm_cost"] > 0
    assert result["prompt_tokens"] == 500
    assert result["completion_tokens"] == 200


@pytest.mark.asyncio
async def test_analyse_single_record_parse_failure():
    mock_provider = AsyncMock()
    mock_provider.call.return_value = LlmResponse(
        text="I cannot parse this into JSON sorry",
        prompt_tokens=100,
        completion_tokens=50,
        model="gpt-4o",
    )
    record = _make_record()

    result = await _analyse_single_record(
        record=record,
        provider=mock_provider,
        template="Q: {question}",
        system_prompt="Judge.",
        rule_tags=[],
    )

    assert result["success"] is False
    assert result["raw_response"] == "I cannot parse this into JSON sorry"


@pytest.mark.asyncio
async def test_analyse_single_record_unmatched_tags():
    response_with_unknown = '''{
        "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂", "不存在.的.分类"],
        "root_cause": "test",
        "severity": "medium",
        "confidence": 0.7,
        "evidence": "test",
        "suggestion": "test"
    }'''
    mock_provider = AsyncMock()
    mock_provider.call.return_value = LlmResponse(
        text=response_with_unknown,
        prompt_tokens=100,
        completion_tokens=50,
        model="gpt-4o",
    )
    record = _make_record()

    result = await _analyse_single_record(
        record=record,
        provider=mock_provider,
        template="Q: {question}",
        system_prompt="Judge.",
        rule_tags=[],
    )

    assert result["success"] is True
    assert "不存在.的.分类" in result["unmatched_tags"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/llm/test_run_llm_judge_task.py -x`
Expected: FAIL with `ImportError: cannot import name '_analyse_single_record'`

### Task 7.2 — Implement `_analyse_single_record`

- [ ] **Step 3: Add to `app/tasks/analysis.py`**

Append the following to the existing `app/tasks/analysis.py` (after the `run_rules` code from Plan 3):

```python
# ---------------------------------------------------------------------------
# LLM Judge helpers (added by Plan 4)
# ---------------------------------------------------------------------------
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from app.llm.schemas import PromptContext
from app.llm.prompt_renderer import render_prompt
from app.llm.output_parser import parse_llm_response
from app.llm.cost_calculator import estimate_cost
from app.llm.providers.base import BaseLlmProvider


_FORMAT_REPAIR_SUFFIX = "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no explanation."

_SYSTEM_PROMPT_DEFAULT = """You are an expert LLM evaluation analyst. Analyze why the model gave an incorrect answer.

Respond in JSON with this exact structure:
{
    "error_types": ["<L1>.<L2>.<L3 if applicable>"],
    "root_cause": "<concise root cause explanation>",
    "severity": "high|medium|low",
    "confidence": 0.0-1.0,
    "evidence": "<evidence from the model's answer>",
    "suggestion": "<improvement suggestion>"
}"""


async def _call_llm_with_retry(
    provider: BaseLlmProvider,
    system_prompt: str,
    user_prompt: str,
):
    """Call LLM with 3 retries and exponential backoff on API failures."""
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call():
        return await provider.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
    return await _call()


async def _analyse_single_record(
    record: object,
    provider: BaseLlmProvider,
    template: str,
    system_prompt: str,
    rule_tags: list[str],
) -> dict:
    """
    Call LLM for one record, parse response, return result dict.

    Retry logic:
    - API failures: 3 retries with exponential backoff (via tenacity)
    - JSON parse failures: 1 retry with format-repair prompt suffix
    """
    ctx = PromptContext(
        question=getattr(record, "question", "") or "",
        expected=getattr(record, "expected_answer", "") or "",
        model_answer=getattr(record, "model_answer", "") or "",
        rule_tags=rule_tags,
        task_category=getattr(record, "task_category", "") or "",
    )
    user_prompt = render_prompt(template, ctx)

    # First attempt (with retry on API failures)
    llm_resp = await _call_llm_with_retry(provider, system_prompt, user_prompt)
    parse_result = parse_llm_response(llm_resp.text)

    # Retry once with format-repair prompt if JSON parse failed
    if not parse_result.success:
        llm_resp_retry = await _call_llm_with_retry(
            provider, system_prompt, user_prompt + _FORMAT_REPAIR_SUFFIX,
        )
        parse_result = parse_llm_response(llm_resp_retry.text)
        # Combine token counts
        total_prompt = llm_resp.prompt_tokens + llm_resp_retry.prompt_tokens
        total_completion = llm_resp.completion_tokens + llm_resp_retry.completion_tokens
    else:
        total_prompt = llm_resp.prompt_tokens
        total_completion = llm_resp.completion_tokens

    cost = estimate_cost(
        model=llm_resp.model,
        prompt_tokens=total_prompt,
        completion_tokens=total_completion,
    )

    if not parse_result.success:
        return {
            "success": False,
            "record_id": str(getattr(record, "id", "")),
            "raw_response": llm_resp.text,
            "error": parse_result.error,
            "llm_cost": cost,
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "model": llm_resp.model,
        }

    out = parse_result.output
    return {
        "success": True,
        "record_id": str(getattr(record, "id", "")),
        "error_types": out.error_types,
        "root_cause": out.root_cause,
        "severity": out.severity.value,
        "confidence": out.confidence,
        "evidence": out.evidence,
        "suggestion": out.suggestion,
        "unmatched_tags": parse_result.unmatched_tags,
        "llm_cost": cost,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "model": llm_resp.model,
        "raw_response": llm_resp.text,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/llm/test_run_llm_judge_task.py -x -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/analysis.py backend/tests/llm/test_run_llm_judge_task.py
git commit -m "feat(llm): implement _analyse_single_record core logic with retry and cost tracking"
```

### Task 7.3 — Implement full `run_llm_judge` Celery task

- [ ] **Step 6: Add the Celery task entry point to `app/tasks/analysis.py`**

```python
# ---------------------------------------------------------------------------
# Celery task: run_llm_judge
# ---------------------------------------------------------------------------
from app.llm.providers.registry import create_provider
from app.llm.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.llm.budget_tracker import DailyBudgetTracker, BudgetExhaustedError
from app.llm.rate_limiter import RateLimiter, RateLimitExceededError
from app.llm.record_selector import select_records
from app.models.analysis_strategy import AnalysisStrategy
from app.models.prompt_template import PromptTemplate

# Priority mapping for Celery task routing (spec §6.4)
_STRATEGY_PRIORITY = {"manual": 9, "full": 5, "fallback": 3, "sampling": 1}


def _get_rule_tags_for_record(record_id: str, db: Session) -> list[str]:
    """Fetch existing rule-generated tags for a record."""
    from app.models.error_tag import ErrorTag
    tags = (
        db.query(ErrorTag.tag_path)
        .filter(ErrorTag.record_id == record_id, ErrorTag.source == "rule")
        .all()
    )
    return [t[0] for t in tags]


def _has_rule_tags(record_id: str, db: Session) -> bool:
    from app.models.error_tag import ErrorTag
    return (
        db.query(ErrorTag)
        .filter(ErrorTag.record_id == record_id, ErrorTag.source == "rule")
        .first()
    ) is not None


@shared_task(
    name="tasks.analysis.run_llm_judge",
    bind=True,
    max_retries=0,  # retries handled per-record via tenacity, not at task level
)
def run_llm_judge(
    self,
    session_id: str,
    strategy_id: str,
    record_ids: Optional[list[str]] = None,
) -> dict:
    """
    Celery task: run LLM Judge analysis over eval_records in a session.

    NOTE: uuid and Optional are already imported at the top of analysis.py (Plan 3).

    Args:
        session_id: UUID of the eval session.
        strategy_id: UUID of the AnalysisStrategy to use.
        record_ids: Optional explicit record IDs (for manual strategy).

    Priority dispatch: Callers should use apply_async(priority=...) with
    _STRATEGY_PRIORITY mapping. See trigger endpoint in llm_jobs.py.
    """
    with get_db_session() as db:
        # 1. Load strategy and template
        strategy = db.get(AnalysisStrategy, uuid.UUID(strategy_id))
        if strategy is None:
            return {"error": f"Strategy {strategy_id} not found"}

        template_row = db.get(PromptTemplate, strategy.prompt_template_id)
        if template_row is None:
            return {"error": f"PromptTemplate {strategy.prompt_template_id} not found"}

        # 2. Create provider
        provider = create_provider(
            provider_name=strategy.llm_provider,
            api_key=strategy.config.get("api_key", ""),
            model=strategy.llm_model,
            base_url=strategy.config.get("base_url"),
        )

        # 3. Set up circuit breaker, rate limiter, and budget tracker
        breaker = CircuitBreaker(
            failure_threshold=5,
            cooldown_seconds=60,
            backend="memory",
        )
        rate_limiter = RateLimiter(
            max_requests_per_minute=int(strategy.config.get("max_rpm", 60)),
            backend="memory",
        )
        budget = DailyBudgetTracker(
            daily_limit=strategy.daily_budget or -1.0,
            backend="memory",
        )

        # 4. Load error records for the session
        records = (
            db.query(EvalRecord)
            .filter(
                EvalRecord.session_id == session_id,
                EvalRecord.is_correct == False,  # noqa: E712
            )
            .all()
        )

        # Enrich records with has_rule_tags attribute for selector
        for rec in records:
            rec.has_rule_tags = _has_rule_tags(str(rec.id), db)

        # 5. Apply strategy to select records
        config = dict(strategy.config or {})
        if record_ids:
            config["record_ids"] = record_ids
        selected = select_records(
            records=records,
            strategy_type=strategy.strategy_type,
            config=config,
        )

        # 6. Process each record with concurrency via asyncio.gather
        loop = asyncio.new_event_loop()
        total_analysed = 0
        total_failed = 0
        total_cost = 0.0
        sem = asyncio.Semaphore(strategy.max_concurrent or 5)

        async def _process_one(record):
            nonlocal total_analysed, total_failed, total_cost

            async with sem:
                # Get rule tags for context
                rule_tags = _get_rule_tags_for_record(str(record.id), db)

                result = await _analyse_single_record(
                    record=record,
                    provider=provider,
                    template=template_row.template,
                    system_prompt=_SYSTEM_PROMPT_DEFAULT,
                    rule_tags=rule_tags,
                )
                return record, result

        for record in selected:
            # Check circuit breaker
            try:
                breaker.check()
            except CircuitOpenError:
                break

            # Check budget
            try:
                budget.check()
            except BudgetExhaustedError:
                # Mark remaining as budget_exhausted
                break

            # Rate limiting
            try:
                rate_limiter.wait_and_acquire(timeout=30.0)
            except RateLimitExceededError:
                break

            # Dedup: skip if already has LLM analysis
            existing = (
                db.query(AnalysisResult)
                .filter(
                    AnalysisResult.record_id == str(record.id),
                    AnalysisResult.analysis_type == "llm",
                )
                .first()
            )
            if existing:
                continue

            # Get rule tags for context
            rule_tags = _get_rule_tags_for_record(str(record.id), db)

            # Call LLM (with tenacity retries inside _analyse_single_record)
            try:
                result = loop.run_until_complete(
                    _analyse_single_record(
                        record=record,
                        provider=provider,
                        template=template_row.template,
                        system_prompt=_SYSTEM_PROMPT_DEFAULT,
                        rule_tags=rule_tags,
                    )
                )
                breaker.record_success()
            except Exception:
                breaker.record_failure()
                # Mark record as analysis_failed after retries exhausted
                ar_failed = AnalysisResult(
                    id=str(uuid.uuid4()),
                    record_id=str(record.id),
                    analysis_type="llm",
                    error_types=[],
                    severity="low",
                    confidence=0,
                    llm_model=strategy.llm_model,
                    prompt_template=template_row.name,
                    raw_response={"error": "analysis_failed after 3 retries"},
                )
                db.add(ar_failed)
                total_failed += 1
                continue

            budget.record_cost(result.get("llm_cost", 0))
            total_cost += result.get("llm_cost", 0)

            # Write analysis_result
            ar = AnalysisResult(
                id=str(uuid.uuid4()),
                record_id=str(record.id),
                analysis_type="llm",
                error_types=result.get("error_types", []),
                root_cause=result.get("root_cause", ""),
                severity=result.get("severity"),
                confidence=result.get("confidence", 0),
                evidence=result.get("evidence", ""),
                suggestion=result.get("suggestion", ""),
                llm_model=result.get("model", ""),
                llm_cost=result.get("llm_cost", 0),
                prompt_template=template_row.name,
                raw_response={"text": result.get("raw_response", "")},
                unmatched_tags=result.get("unmatched_tags", []),
            )
            db.add(ar)
            db.flush()

            # Write error_tags for valid (matched) tags
            if result.get("success"):
                all_tags = set(result.get("error_types", []))
                unmatched = set(result.get("unmatched_tags", []))
                matched_tags = all_tags - unmatched
                for tag_path in matched_tags:
                    level = min(len(tag_path.split(".")), 3)
                    db.add(ErrorTag(
                        id=str(uuid.uuid4()),
                        record_id=str(record.id),
                        analysis_result_id=str(ar.id),
                        tag_path=tag_path,
                        tag_level=level,
                        source="llm",
                        confidence=result.get("confidence", 0),
                    ))

            total_analysed += 1

        db.commit()
        loop.close()

        return {
            "session_id": session_id,
            "strategy_id": strategy_id,
            "total_selected": len(selected),
            "total_analysed": total_analysed,
            "total_failed": total_failed,
            "total_cost_usd": round(total_cost, 6),
        }
```

- [ ] **Step 7: Run existing tests to ensure nothing broke**

Run: `cd backend && python -m pytest tests/ -x --tb=short`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/app/tasks/analysis.py
git commit -m "feat(llm): implement run_llm_judge Celery task with circuit breaker, budget, and dedup"
```

---

## Phase 8 — Pydantic Schemas for Strategy, Template, Job APIs

### Task 8.1 — Strategy schemas

**Files:**
- Create: `backend/app/schemas/strategy.py`

- [ ] **Step 1: Write the schemas**

```python
# backend/app/schemas/strategy.py
"""Pydantic schemas for analysis_strategies API."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    strategy_type: str = Field(..., pattern=r"^(full|fallback|sampling|manual)$")
    config: dict[str, Any] = Field(default_factory=dict)
    llm_provider: str = Field(..., pattern=r"^(openai|claude|local)$")
    llm_model: str = Field(..., min_length=1, max_length=255)
    prompt_template_id: uuid.UUID
    max_concurrent: int = Field(default=5, ge=1, le=100)
    daily_budget: float = Field(default=-1.0)  # -1 = unlimited
    is_active: bool = True


class StrategyPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    strategy_type: Optional[str] = Field(default=None, pattern=r"^(full|fallback|sampling|manual)$")
    config: Optional[dict[str, Any]] = None
    llm_provider: Optional[str] = Field(default=None, pattern=r"^(openai|claude|local)$")
    llm_model: Optional[str] = Field(default=None, min_length=1, max_length=255)
    prompt_template_id: Optional[uuid.UUID] = None
    max_concurrent: Optional[int] = Field(default=None, ge=1, le=100)
    daily_budget: Optional[float] = None
    is_active: Optional[bool] = None


class StrategyResponse(BaseModel):
    id: uuid.UUID
    name: str
    strategy_type: str
    config: dict[str, Any]
    llm_provider: str
    llm_model: str
    prompt_template_id: uuid.UUID
    max_concurrent: int
    daily_budget: float
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### Task 8.2 — Prompt template schemas

**Files:**
- Create: `backend/app/schemas/prompt_template.py`

- [ ] **Step 2: Write the schemas**

```python
# backend/app/schemas/prompt_template.py
"""Pydantic schemas for prompt_templates API."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PromptTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    benchmark: Optional[str] = None  # NULL = generic
    template: str = Field(..., min_length=10)
    version: int = Field(default=1, ge=1)
    is_active: bool = True


class PromptTemplatePatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    benchmark: Optional[str] = None
    template: Optional[str] = Field(default=None, min_length=10)
    version: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class PromptTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    benchmark: Optional[str]
    template: str
    version: int
    is_active: bool
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
```

### Task 8.3 — LLM job schemas

**Files:**
- Create: `backend/app/schemas/llm_job.py`

- [ ] **Step 3: Write the schemas**

```python
# backend/app/schemas/llm_job.py
"""Pydantic schemas for LLM job trigger and status."""
from __future__ import annotations
import uuid
from typing import Optional
from pydantic import BaseModel, Field


class LlmTriggerRequest(BaseModel):
    session_id: uuid.UUID
    strategy_id: uuid.UUID
    record_ids: Optional[list[str]] = None  # for manual strategy


class LlmTriggerResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: str = ""


class LlmJobStatus(BaseModel):
    job_id: str
    status: str  # queued / running / completed / failed
    result: Optional[dict] = None


class LlmCostSummary(BaseModel):
    total_cost_usd: float
    total_records_analysed: int
    cost_by_model: dict[str, float] = Field(default_factory=dict)
    cost_by_session: dict[str, float] = Field(default_factory=dict)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/strategy.py backend/app/schemas/prompt_template.py backend/app/schemas/llm_job.py
git commit -m "feat(llm): add Pydantic schemas for strategies, templates, and job control APIs"
```

---

## Phase 9 — REST APIs

### Task 9.1 — Strategies CRUD API

**Files:**
- Create: `backend/app/api/v1/routers/llm_strategies.py`
- Create: `backend/tests/api/test_llm_strategies_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_llm_strategies_api.py
import pytest
from httpx import AsyncClient

TEMPLATE_PAYLOAD = {
    "name": "generic_judge",
    "template": "Q: {question}\nExpected: {expected}\nAnswer: {model_answer}\nTags: {rule_tags}\nCategory: {task_category}\nAnalyze the error.",
    "version": 1,
    "is_active": True,
}

STRATEGY_PAYLOAD = {
    "name": "test_full_strategy",
    "strategy_type": "full",
    "config": {},
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "prompt_template_id": None,  # will be set after template creation
    "max_concurrent": 5,
    "daily_budget": 50.0,
    "is_active": True,
}


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-analyst-token"}


@pytest.mark.anyio
async def test_strategy_crud_lifecycle(async_client: AsyncClient, auth_headers):
    # Create template first
    tmpl_resp = await async_client.post(
        "/api/v1/llm/prompt-templates", json=TEMPLATE_PAYLOAD, headers=auth_headers,
    )
    assert tmpl_resp.status_code == 201
    template_id = tmpl_resp.json()["id"]

    payload = {**STRATEGY_PAYLOAD, "prompt_template_id": template_id}

    # CREATE
    resp = await async_client.post("/api/v1/llm/strategies", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    strategy_id = resp.json()["id"]
    assert resp.json()["name"] == "test_full_strategy"

    # LIST
    resp = await async_client.get("/api/v1/llm/strategies", headers=auth_headers)
    assert resp.status_code == 200
    assert any(s["id"] == strategy_id for s in resp.json())

    # GET
    resp = await async_client.get(f"/api/v1/llm/strategies/{strategy_id}", headers=auth_headers)
    assert resp.status_code == 200

    # PATCH
    resp = await async_client.patch(
        f"/api/v1/llm/strategies/{strategy_id}",
        json={"daily_budget": 100.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["daily_budget"] == 100.0

    # DELETE
    resp = await async_client.delete(f"/api/v1/llm/strategies/{strategy_id}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_strategy_requires_analyst(async_client: AsyncClient):
    viewer_headers = {"Authorization": "Bearer test-viewer-token"}
    resp = await async_client.post(
        "/api/v1/llm/strategies", json=STRATEGY_PAYLOAD, headers=viewer_headers,
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Write the router**

```python
# backend/app/api/v1/routers/llm_strategies.py
"""CRUD endpoints for /api/v1/llm/strategies."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.api.v1.deps import require_role
from app.models.analysis_strategy import AnalysisStrategy
from app.schemas.strategy import StrategyCreate, StrategyPatch, StrategyResponse

router = APIRouter(prefix="/llm/strategies", tags=["llm-strategies"])


@router.get("", response_model=list[StrategyResponse])
def list_strategies(db: Session = Depends(get_db)):
    return db.query(AnalysisStrategy).order_by(AnalysisStrategy.created_at.desc()).all()


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(strategy_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.get(AnalysisStrategy, strategy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return row


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
def create_strategy(
    payload: StrategyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["analyst", "admin"])),
):
    row = AnalysisStrategy(**payload.model_dump(), created_by=current_user.username)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Strategy name '{payload.name}' already exists")
    db.refresh(row)
    return row


@router.put("/{strategy_id}", response_model=StrategyResponse)
def replace_strategy(
    strategy_id: uuid.UUID,
    payload: StrategyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["analyst", "admin"])),
):
    row = db.get(AnalysisStrategy, strategy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(
    strategy_id: uuid.UUID,
    payload: StrategyPatch,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["analyst", "admin"])),
):
    row = db.get(AnalysisStrategy, strategy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(
    strategy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["analyst", "admin"])),
):
    row = db.get(AnalysisStrategy, strategy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    db.delete(row)
    db.commit()
```

- [ ] **Step 3: Run test**

Run: `cd backend && python -m pytest tests/api/test_llm_strategies_api.py -x -v`
Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/routers/llm_strategies.py backend/tests/api/test_llm_strategies_api.py
git commit -m "feat(llm): add CRUD REST API for /api/v1/llm/strategies"
```

### Task 9.2 — Prompt Templates CRUD API

**Files:**
- Create: `backend/app/api/v1/routers/llm_templates.py`
- Create: `backend/tests/api/test_llm_templates_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_llm_templates_api.py
import pytest
from httpx import AsyncClient

PAYLOAD = {
    "name": "test_template",
    "benchmark": None,
    "template": "Q: {question}\nExpected: {expected}\nAnswer: {model_answer}\nAnalyze the error.",
    "version": 1,
    "is_active": True,
}


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-analyst-token"}


@pytest.mark.anyio
async def test_template_crud_lifecycle(async_client: AsyncClient, auth_headers):
    # CREATE
    resp = await async_client.post("/api/v1/llm/prompt-templates", json=PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    tid = resp.json()["id"]

    # LIST
    resp = await async_client.get("/api/v1/llm/prompt-templates", headers=auth_headers)
    assert resp.status_code == 200
    assert any(t["id"] == tid for t in resp.json())

    # GET
    resp = await async_client.get(f"/api/v1/llm/prompt-templates/{tid}", headers=auth_headers)
    assert resp.status_code == 200

    # PATCH
    resp = await async_client.patch(
        f"/api/v1/llm/prompt-templates/{tid}",
        json={"version": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 2

    # DELETE
    resp = await async_client.delete(f"/api/v1/llm/prompt-templates/{tid}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_template_requires_analyst(async_client: AsyncClient):
    viewer_headers = {"Authorization": "Bearer test-viewer-token"}
    resp = await async_client.post(
        "/api/v1/llm/prompt-templates", json=PAYLOAD, headers=viewer_headers,
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Write the router**

```python
# backend/app/api/v1/routers/llm_templates.py
"""CRUD endpoints for /api/v1/llm/prompt-templates."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.api.v1.deps import require_role
from app.models.prompt_template import PromptTemplate
from app.schemas.prompt_template import PromptTemplateCreate, PromptTemplatePatch, PromptTemplateResponse

router = APIRouter(prefix="/llm/prompt-templates", tags=["llm-templates"])


@router.get("", response_model=list[PromptTemplateResponse])
def list_templates(db: Session = Depends(get_db)):
    return db.query(PromptTemplate).order_by(PromptTemplate.created_at.desc()).all()


@router.get("/{template_id}", response_model=PromptTemplateResponse)
def get_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.get(PromptTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return row


@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: PromptTemplateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["analyst", "admin"])),
):
    row = PromptTemplate(**payload.model_dump(), created_by=current_user.username)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Template name '{payload.name}' already exists")
    db.refresh(row)
    return row


@router.put("/{template_id}", response_model=PromptTemplateResponse)
def replace_template(
    template_id: uuid.UUID,
    payload: PromptTemplateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["analyst", "admin"])),
):
    row = db.get(PromptTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{template_id}", response_model=PromptTemplateResponse)
def update_template(
    template_id: uuid.UUID,
    payload: PromptTemplatePatch,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["analyst", "admin"])),
):
    row = db.get(PromptTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["analyst", "admin"])),
):
    row = db.get(PromptTemplate, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(row)
    db.commit()
```

- [ ] **Step 3: Run test**

Run: `cd backend && python -m pytest tests/api/test_llm_templates_api.py -x -v`
Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/routers/llm_templates.py backend/tests/api/test_llm_templates_api.py
git commit -m "feat(llm): add CRUD REST API for /api/v1/llm/prompt-templates"
```

### Task 9.3 — LLM Jobs API (trigger, status, cost-summary)

**Files:**
- Create: `backend/app/api/v1/routers/llm_jobs.py`
- Create: `backend/tests/api/test_llm_jobs_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_llm_jobs_api.py
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-analyst-token"}


@pytest.mark.anyio
async def test_trigger_returns_job_id(async_client: AsyncClient, auth_headers):
    with patch("app.api.v1.routers.llm_jobs.run_llm_judge") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "celery-job-uuid-123"
        mock_task.apply_async.return_value = mock_result

        # Also mock strategy lookup for priority
        with patch("app.api.v1.routers.llm_jobs.AnalysisStrategy") as _:
            resp = await async_client.post(
                "/api/v1/llm/trigger",
                json={
                    "session_id": "00000000-0000-0000-0000-000000000001",
                    "strategy_id": "00000000-0000-0000-0000-000000000002",
                },
                headers=auth_headers,
            )
    assert resp.status_code == 202
    assert resp.json()["job_id"] == "celery-job-uuid-123"
    assert resp.json()["status"] == "queued"


@pytest.mark.anyio
async def test_trigger_requires_analyst(async_client: AsyncClient):
    viewer_headers = {"Authorization": "Bearer test-viewer-token"}
    resp = await async_client.post(
        "/api/v1/llm/trigger",
        json={
            "session_id": "00000000-0000-0000-0000-000000000001",
            "strategy_id": "00000000-0000-0000-0000-000000000002",
        },
        headers=viewer_headers,
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_job_status_pending(async_client: AsyncClient, auth_headers):
    with patch("app.api.v1.routers.llm_jobs.AsyncResult") as mock_ar:
        mock_ar.return_value.state = "PENDING"
        mock_ar.return_value.result = None
        resp = await async_client.get(
            "/api/v1/llm/jobs/celery-job-uuid-123/status",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING"


@pytest.mark.anyio
async def test_cost_summary(async_client: AsyncClient, auth_headers):
    resp = await async_client.get("/api/v1/llm/cost-summary", headers=auth_headers)
    assert resp.status_code == 200
    assert "total_cost_usd" in resp.json()


@pytest.mark.anyio
async def test_list_jobs(async_client: AsyncClient, auth_headers):
    resp = await async_client.get("/api/v1/llm/jobs", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

- [ ] **Step 2: Write the router**

```python
# backend/app/api/v1/routers/llm_jobs.py
"""LLM analysis job control: trigger, status, job list, cost summary."""
from __future__ import annotations
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from celery.result import AsyncResult

from app.db.session import get_db
from app.api.v1.deps import require_role
from app.tasks.analysis import run_llm_judge, _STRATEGY_PRIORITY
from app.models.analysis_result import AnalysisResult
from app.models.eval_record import EvalRecord
from app.schemas.llm_job import (
    LlmTriggerRequest,
    LlmTriggerResponse,
    LlmJobStatus,
    LlmCostSummary,
)

router = APIRouter(prefix="/llm", tags=["llm-jobs"])


@router.post("/trigger", response_model=LlmTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_llm_analysis(
    payload: LlmTriggerRequest,
    current_user=Depends(require_role(["analyst", "admin"])),
    db: Session = Depends(get_db),
):
    """Dispatch an LLM analysis job to the Celery queue with priority."""
    # Look up strategy to determine priority
    from app.models.analysis_strategy import AnalysisStrategy
    strategy = db.get(AnalysisStrategy, payload.strategy_id)
    priority = _STRATEGY_PRIORITY.get(
        strategy.strategy_type if strategy else "sampling", 1
    )
    result = run_llm_judge.apply_async(
        kwargs=dict(
            session_id=str(payload.session_id),
            strategy_id=str(payload.strategy_id),
            record_ids=payload.record_ids,
        ),
        priority=priority,
    )
    return LlmTriggerResponse(
        job_id=result.id,
        status="queued",
        message=f"LLM analysis job dispatched (priority={priority}) for session {payload.session_id}",
    )


@router.get("/jobs", response_model=list[LlmJobStatus])
def list_jobs(
    db: Session = Depends(get_db),
):
    """List recent LLM analysis jobs (from analysis_results with analysis_type='llm')."""
    # Return distinct jobs by grouping analysis_results created_at
    # For a full solution, a dedicated llm_jobs table would be added.
    # This lightweight approach returns one entry per unique (session, template) combo.
    from app.models.eval_session import EvalSession
    rows = (
        db.query(
            AnalysisResult.prompt_template,
            sqlfunc.min(AnalysisResult.created_at).label("started_at"),
            sqlfunc.count(AnalysisResult.id).label("count"),
            sqlfunc.sum(AnalysisResult.llm_cost).label("cost"),
        )
        .filter(AnalysisResult.analysis_type == "llm")
        .group_by(AnalysisResult.prompt_template)
        .order_by(sqlfunc.min(AnalysisResult.created_at).desc())
        .limit(50)
        .all()
    )
    return [
        LlmJobStatus(
            job_id=f"db-{row.prompt_template or 'unknown'}",
            status="completed",
            result={"count": row.count, "cost": float(row.cost or 0)},
        )
        for row in rows
    ]


@router.get("/jobs/{job_id}/status", response_model=LlmJobStatus)
def get_job_status(job_id: str):
    """Check status of an LLM analysis Celery task."""
    ar = AsyncResult(job_id)
    return LlmJobStatus(
        job_id=job_id,
        status=ar.state,
        result=ar.result if ar.ready() else None,
    )


@router.get("/cost-summary", response_model=LlmCostSummary)
def get_cost_summary(db: Session = Depends(get_db)):
    """Aggregate LLM analysis costs."""
    # Cost by model
    model_rows = (
        db.query(
            AnalysisResult.llm_model,
            sqlfunc.sum(AnalysisResult.llm_cost).label("total"),
            sqlfunc.count(AnalysisResult.id).label("cnt"),
        )
        .filter(AnalysisResult.analysis_type == "llm")
        .group_by(AnalysisResult.llm_model)
        .all()
    )

    total_cost = 0.0
    total_count = 0
    cost_by_model: dict[str, float] = {}
    for model_name, total, cnt in model_rows:
        model_key = model_name or "unknown"
        cost_by_model[model_key] = float(total or 0)
        total_cost += float(total or 0)
        total_count += int(cnt or 0)

    # Cost by session (via JOIN to eval_records)
    session_rows = (
        db.query(
            EvalRecord.session_id,
            sqlfunc.sum(AnalysisResult.llm_cost).label("total"),
        )
        .join(EvalRecord, EvalRecord.id == AnalysisResult.record_id)
        .filter(AnalysisResult.analysis_type == "llm")
        .group_by(EvalRecord.session_id)
        .all()
    )
    cost_by_session = {
        str(sid): float(total or 0) for sid, total in session_rows
    }

    return LlmCostSummary(
        total_cost_usd=round(total_cost, 6),
        total_records_analysed=total_count,
        cost_by_model=cost_by_model,
        cost_by_session=cost_by_session,
    )
```

- [ ] **Step 3: Run test**

Run: `cd backend && python -m pytest tests/api/test_llm_jobs_api.py -x -v`
Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/routers/llm_jobs.py backend/tests/api/test_llm_jobs_api.py
git commit -m "feat(llm): add trigger, job status, and cost summary API endpoints"
```

### Task 9.4 — Register all routers in FastAPI app

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add router imports and registration**

```python
# Add to existing imports in app/main.py:
from app.api.v1.routers.llm_strategies import router as llm_strategies_router
from app.api.v1.routers.llm_templates import router as llm_templates_router
from app.api.v1.routers.llm_jobs import router as llm_jobs_router

# Add inside create_app() or at module level:
app.include_router(llm_strategies_router, prefix="/api/v1")
app.include_router(llm_templates_router, prefix="/api/v1")
app.include_router(llm_jobs_router, prefix="/api/v1")
```

- [ ] **Step 2: Run full test suite**

Run: `cd backend && python -m pytest tests/ -x --tb=short`
Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(llm): register LLM strategies, templates, and jobs routers"
```

---

## Phase 10 — Final Integration Check

### Task 10.1 — Run full test suite

- [ ] **Step 1: Run all tests**

```bash
cd backend && python -m pytest tests/ -v --tb=short
# Expected: all tests pass, 0 failures
```

### Task 10.2 — Verify Celery task registration

- [ ] **Step 2: Check task is registered**

```bash
cd backend && celery -A app.celery_app inspect registered
# Expected output includes: tasks.analysis.run_llm_judge
```

### Task 10.3 — Verify API routes exist

- [ ] **Step 3: Check OpenAPI schema**

```bash
cd backend && python -c "
from app.main import app
routes = [r.path for r in app.routes]
assert '/api/v1/llm/trigger' in routes or any('trigger' in r for r in routes)
assert '/api/v1/llm/strategies' in routes or any('strategies' in r for r in routes)
assert '/api/v1/llm/prompt-templates' in routes or any('prompt-templates' in r for r in routes)
assert '/api/v1/llm/cost-summary' in routes or any('cost-summary' in r for r in routes)
assert '/api/v1/llm/jobs' in routes or any('/llm/jobs' in r for r in routes)
print('All LLM routes registered OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "chore(llm): final integration checks for LLM Judge Agent"
```

---

## Dependencies on Earlier Plans

| Symbol | Location | Used by |
|---|---|---|
| `Base` (DeclarativeBase) | `app/db/base.py` | ORM model imports |
| `get_db` (session dep) | `app/db/session.py` | All API routers |
| `get_db_session` (sync context mgr) | `app/db/session.py` | Celery task (must be sync Session) |
| `require_role` | `app/api/v1/deps.py` | All API routers (Analyst+) |
| `app` (FastAPI) | `app/main.py` | Router registration |
| `EvalRecord` | `app/models/eval_record.py` | Record queries |
| `AnalysisResult` | `app/models/analysis_result.py` | DB writes |
| `ErrorTag` | `app/models/error_tag.py` | DB writes |
| `AnalysisStrategy` | `app/models/analysis_strategy.py` | Strategy loading |
| `PromptTemplate` | `app/models/prompt_template.py` | Template loading |
| `TaxonomyTree` | `app/rules/taxonomy.py` | Output validation |
| Celery app | `app/celery_app.py` | `@shared_task` |
| `analysis_results`, `error_tags`, `analysis_strategies`, `prompt_templates` tables | Alembic migration | ORM models |
