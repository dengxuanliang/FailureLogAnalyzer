# Orchestrator Agent (LangGraph) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Orchestrator Agent — a LangGraph StateGraph that receives user instructions (natural language or structured API calls), identifies intent, routes to the correct subgraph (Ingest / Analyze / Compare / Query / Report), coordinates Celery task dispatch, manages conversation state via LangGraph Checkpointer, supports Human-in-the-Loop for low-confidence results, and exposes a REST + WebSocket API for agent conversations.

**Architecture:** The Orchestrator is a LangGraph `StateGraph` with typed `OrchestratorState` using `Annotated` reducers for list fields. An intent router node classifies user input into one of five intents (ingest, analyze, compare, query, report). Each intent maps to a subgraph node that orchestrates the corresponding Celery tasks (from Plans 2–5). LangGraph's `MemorySaver` (dev) / `PostgresSaver` (prod) checkpointer persists state across turns and enables Human-in-the-Loop via `interrupt_before`. A conversation API (`POST /api/v1/agent/chat`, `WS /api/v1/ws/agent`) accepts messages and streams node transitions back to the client. All nodes return **partial state update dicts** (never mutate input state), following LangGraph's reducer-based state management.

**Tech Stack:** Python 3.11, LangGraph 0.2+, FastAPI, SQLAlchemy 2 (async), Alembic, Celery 5 + Redis, langgraph-checkpoint-postgres (prod), pytest + pytest-asyncio

---

## Prerequisites (Plans 1–5 must be complete)

Plan 1 provides:
- `/backend/app/db/` — SQLAlchemy async engine, `Base`, session factories
- `/backend/app/db/session.py` — `async def get_db() -> AsyncSession` (async generator)
- `/backend/app/core/config.py` — `settings = Settings()` (module-level singleton)
- `/backend/app/celery_app.py` — Celery application instance
- `/backend/app/api/v1/deps.py` — `require_role(minimum_role: UserRole)` (takes single enum, not list)
- `/backend/app/main.py` — FastAPI app with router registration

Plan 2 provides:
- `/backend/app/tasks/ingest.py` — `parse_file` Celery task

Plan 3 provides:
- `/backend/app/tasks/analysis.py` — `run_rules` Celery task
- `/backend/app/rules/taxonomy.py` — `TaxonomyTree`

Plan 4 provides:
- `/backend/app/tasks/analysis.py` — `run_llm_judge` Celery task
- `/backend/app/llm/record_selector.py` — strategy-based record selection

Plan 5 provides:
- `/backend/app/services/analysis_query.py` — query services (async)
- `/backend/app/services/compare.py` — version comparison services (async)
- `/backend/app/services/cross_benchmark.py` — cross-benchmark services (async)
- `/backend/app/tasks/report.py` — `generate_report` Celery task

---

## File Structure After This Plan

```
backend/app/
  agent/
    __init__.py
    state.py              # OrchestratorState TypedDict with Annotated reducers
    intent_router.py      # Intent classification node
    nodes/
      __init__.py
      ingest_node.py      # Ingest subgraph: dispatch parse_file, poll status
      analyze_node.py     # Analyze subgraph: run_rules → strategy decision → run_llm_judge
      compare_node.py     # Compare subgraph: call comparison services
      query_node.py       # Query subgraph: call analysis_query / cross_benchmark services
      report_node.py      # Report subgraph: dispatch generate_report
      human_review_node.py # Human-in-the-loop pause node
    graph.py              # Build and compile the StateGraph
    checkpointer.py       # Checkpointer factory (memory dev / postgres prod)
  schemas/
    agent.py              # Pydantic schemas for agent API
  api/v1/routers/
    agent.py              # POST /agent/chat, GET /agent/conversations, WS /ws/agent

tests/
  agent/
    __init__.py
    test_state.py
    test_intent_router.py
    test_ingest_node.py
    test_analyze_node.py
    test_compare_node.py
    test_query_node.py
    test_graph.py
  api/
    test_agent_api.py
```

---

## Phase 1 — OrchestratorState

### Task 1.1 — Write failing test for OrchestratorState

**Files:**
- Create: `backend/tests/agent/__init__.py`
- Create: `backend/tests/agent/test_state.py`
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/agent/state.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agent/test_state.py
"""Tests for OrchestratorState TypedDict validation."""
import pytest
from app.agent.state import OrchestratorState, create_initial_state


def test_create_initial_state_has_required_fields():
    state = create_initial_state()
    assert state["user_input"] == ""
    assert state["intent"] == ""
    assert state["conversation_history"] == []
    assert state["current_step"] == "start"
    assert state["errors"] == []
    assert state["needs_human_input"] is False
    assert state["analyzed_count"] == 0
    assert state["total_count"] == 0


def test_create_initial_state_with_user_input():
    state = create_initial_state(user_input="分析一下 mmlu 的错题")
    assert state["user_input"] == "分析一下 mmlu 的错题"


def test_state_can_be_updated():
    state = create_initial_state()
    state["intent"] = "analyze"
    state["current_step"] = "rule_analysis"
    assert state["intent"] == "analyze"
    assert state["current_step"] == "rule_analysis"


def test_state_has_annotated_list_fields():
    """Verify that list fields use Annotated reducers for LangGraph."""
    import typing
    hints = typing.get_type_hints(OrchestratorState, include_extras=True)
    # conversation_history and errors should have Annotated metadata
    for field in ("conversation_history", "errors"):
        assert hasattr(hints[field], "__metadata__"), (
            f"{field} should use Annotated with a reducer for LangGraph"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/agent/test_state.py -x`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.agent'`

### Task 1.2 — Implement OrchestratorState

- [ ] **Step 3: Create directory and `__init__.py` files**

```bash
mkdir -p backend/app/agent/nodes backend/tests/agent
touch backend/app/agent/__init__.py backend/app/agent/nodes/__init__.py backend/tests/agent/__init__.py
```

- [ ] **Step 4: Write `app/agent/state.py`**

```python
# backend/app/agent/state.py
"""Orchestrator Agent shared state definition (LangGraph StateGraph state).

IMPORTANT: LangGraph nodes MUST return partial state update dicts.
List fields use Annotated[..., operator.add] reducers so that
returned lists are appended to (not replaced).
"""
from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict


class Message(TypedDict):
    role: str       # "user" | "assistant" | "system"
    content: str


class OrchestratorState(TypedDict):
    # User interaction
    user_input: str
    intent: str     # "ingest" | "analyze" | "compare" | "query" | "report" | ""
    conversation_history: Annotated[list[Message], operator.add]

    # Data ingestion
    ingest_job_id: Optional[str]
    ingest_status: Optional[str]   # pending / running / done / failed

    # Analysis context
    target_session_ids: list[str]
    target_filters: dict
    analysis_strategy: str          # full / fallback / sampling / manual

    # Analysis results (references only — actual data in PostgreSQL)
    rule_job_id: Optional[str]
    llm_job_id: Optional[str]
    rule_summary: Optional[dict]
    llm_summary: Optional[dict]
    analyzed_count: int
    total_count: int

    # Report
    report_id: Optional[str]
    report_status: Optional[str]   # pending / generating / done

    # Flow control
    current_step: str
    errors: Annotated[list[str], operator.add]
    needs_human_input: bool


def create_initial_state(user_input: str = "") -> OrchestratorState:
    """Create a fresh OrchestratorState with sensible defaults."""
    return OrchestratorState(
        user_input=user_input,
        intent="",
        conversation_history=[],
        ingest_job_id=None,
        ingest_status=None,
        target_session_ids=[],
        target_filters={},
        analysis_strategy="fallback",
        rule_job_id=None,
        llm_job_id=None,
        rule_summary=None,
        llm_summary=None,
        analyzed_count=0,
        total_count=0,
        report_id=None,
        report_status=None,
        current_step="start",
        errors=[],
        needs_human_input=False,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/agent/test_state.py -x -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/ backend/tests/agent/
git commit -m "feat(agent): add OrchestratorState TypedDict with Annotated reducers"
```

---

## Phase 2 — Intent Router

### Task 2.1 — Write failing test for intent router

**Files:**
- Create: `backend/tests/agent/test_intent_router.py`
- Create: `backend/app/agent/intent_router.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agent/test_intent_router.py
"""Tests for intent classification from user input."""
import pytest
from app.agent.intent_router import classify_intent


@pytest.mark.parametrize("user_input,expected_intent", [
    # Ingest intent
    ("上传文件 mmlu_results.jsonl", "ingest"),
    ("导入这个评测数据", "ingest"),
    ("upload this file", "ingest"),
    ("解析 /data/results/ 目录", "ingest"),
    # Analyze intent
    ("分析一下这批数据的错因", "analyze"),
    ("帮我看看错题原因", "analyze"),
    ("run error analysis", "analyze"),
    ("触发 LLM 分析", "analyze"),
    ("规则分析 session abc", "analyze"),
    # Compare intent
    ("对比 v1 和 v2", "compare"),
    ("版本对比", "compare"),
    ("compare v2.0 with v2.1", "compare"),
    ("v1 vs v2 有什么变化", "compare"),
    # Query intent
    ("查看错误分布", "query"),
    ("展示 mmlu 的分析结果", "query"),
    ("show me the error summary", "query"),
    ("错误率趋势", "query"),
    ("跨 benchmark 分析", "query"),
    # Report intent
    ("生成报告", "report"),
    ("generate a report", "report"),
    ("导出分析报告", "report"),
])
def test_classify_intent(user_input, expected_intent):
    intent = classify_intent(user_input)
    assert intent == expected_intent, f"Input: {user_input!r} → got {intent!r}, expected {expected_intent!r}"


def test_classify_intent_unknown_defaults_to_query():
    intent = classify_intent("你好")
    assert intent == "query"  # fallback to query for generic input


def test_classify_intent_empty_string():
    intent = classify_intent("")
    assert intent == "query"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/agent/test_intent_router.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 2.2 — Implement intent router

- [ ] **Step 3: Write `app/agent/intent_router.py`**

```python
# backend/app/agent/intent_router.py
"""Rule-based intent classification for user input.

Uses keyword matching for fast, deterministic routing.
Can be upgraded to LLM-based classification later.
"""
from __future__ import annotations
import re

# Keyword patterns per intent (Chinese + English)
_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("ingest", [
        r"上传", r"导入", r"upload", r"import", r"解析",
        r"摄入", r"ingest", r"文件", r"file", r"目录",
        r"directory", r"parse",
    ]),
    ("analyze", [
        r"分析.*错", r"错因", r"错题", r"analyze",
        r"analysis", r"规则分析", r"rule", r"llm.*分析",
        r"触发.*分析", r"trigger.*analy",
    ]),
    ("compare", [
        r"对比", r"比较", r"compare", r"vs\b", r"diff",
        r"版本.*对比", r"version.*compar", r"变化",
    ]),
    ("report", [
        r"报告", r"report", r"导出", r"export",
        r"生成.*报告", r"generate.*report",
    ]),
    ("query", [
        r"查看", r"展示", r"show", r"display",
        r"分布", r"distribution", r"趋势", r"trend",
        r"统计", r"summary", r"概览", r"overview",
        r"跨.*benchmark", r"cross.?bench", r"热力图", r"heatmap",
        r"矩阵", r"matrix", r"弱点", r"weakness",
    ]),
]

# Compile patterns
_COMPILED: list[tuple[str, list[re.Pattern]]] = [
    (intent, [re.compile(p, re.IGNORECASE) for p in patterns])
    for intent, patterns in _INTENT_PATTERNS
]


def classify_intent(user_input: str) -> str:
    """
    Classify user input into an intent string.

    Returns one of: 'ingest', 'analyze', 'compare', 'query', 'report'.
    Falls back to 'query' for unrecognized input.
    """
    if not user_input.strip():
        return "query"

    # Score each intent by number of pattern matches
    scores: dict[str, int] = {}
    for intent, patterns in _COMPILED:
        score = sum(1 for p in patterns if p.search(user_input))
        if score > 0:
            scores[intent] = score

    if not scores:
        return "query"  # fallback

    return max(scores, key=scores.get)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/agent/test_intent_router.py -x -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/intent_router.py backend/tests/agent/test_intent_router.py
git commit -m "feat(agent): add keyword-based intent router with Chinese/English support"
```

---

## Phase 3 — Subgraph Nodes

> **Key design rule:** All LangGraph nodes accept `(state, config)` and return a **partial state update dict** containing only changed keys. List fields (`conversation_history`, `errors`) return new items only — the `Annotated[..., operator.add]` reducer appends them automatically. Nodes NEVER mutate the input `state`.

### Task 3.1 — Write failing test for ingest node

**Files:**
- Create: `backend/tests/agent/test_ingest_node.py`
- Create: `backend/app/agent/nodes/ingest_node.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agent/test_ingest_node.py
"""Tests for the ingest subgraph node."""
import pytest
from unittest.mock import patch, MagicMock
from app.agent.state import create_initial_state
from app.agent.nodes.ingest_node import ingest_node


def test_ingest_node_dispatches_celery_task():
    state = create_initial_state(user_input="上传 /data/mmlu.jsonl")
    state["target_filters"] = {"file_path": "/data/mmlu.jsonl", "adapter": "auto"}

    with patch("app.agent.nodes.ingest_node.parse_file") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "celery-ingest-123"
        mock_task.apply_async.return_value = mock_result

        updates = ingest_node(state, config={})

    assert updates["ingest_job_id"] == "celery-ingest-123"
    assert updates["ingest_status"] == "pending"
    assert updates["current_step"] == "ingest_dispatched"
    mock_task.apply_async.assert_called_once()
    # Verify it's a partial update, not the full state
    assert "intent" not in updates


def test_ingest_node_records_error_on_missing_file_path():
    state = create_initial_state(user_input="上传文件")
    state["target_filters"] = {}  # no file_path

    updates = ingest_node(state, config={})

    assert len(updates["errors"]) > 0
    assert "file_path" in updates["errors"][0].lower() or "文件" in updates["errors"][0]
    assert updates["current_step"] == "error"


def test_ingest_node_appends_assistant_message():
    state = create_initial_state(user_input="上传 /data/test.jsonl")
    state["target_filters"] = {"file_path": "/data/test.jsonl"}

    with patch("app.agent.nodes.ingest_node.parse_file") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "job-456"
        mock_task.apply_async.return_value = mock_result

        updates = ingest_node(state, config={})

    # Should return new conversation messages (reducer will append)
    assert any(m["role"] == "assistant" for m in updates["conversation_history"])


def test_ingest_node_does_not_mutate_input_state():
    state = create_initial_state(user_input="上传 /data/test.jsonl")
    state["target_filters"] = {"file_path": "/data/test.jsonl"}
    original_history_len = len(state["conversation_history"])

    with patch("app.agent.nodes.ingest_node.parse_file") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "job-789"
        mock_task.apply_async.return_value = mock_result

        ingest_node(state, config={})

    # Input state must not be mutated
    assert len(state["conversation_history"]) == original_history_len
    assert state["current_step"] == "start"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/agent/test_ingest_node.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 3.2 — Implement ingest node

- [ ] **Step 3: Write `app/agent/nodes/ingest_node.py`**

```python
# backend/app/agent/nodes/ingest_node.py
"""Ingest subgraph node — dispatches parse_file Celery task."""
from __future__ import annotations
from typing import Any
from app.agent.state import OrchestratorState
from app.tasks.ingest import parse_file


def ingest_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """
    LangGraph node: dispatch a file ingestion Celery task.

    Returns a partial state update dict (never mutates input state).
    Expects state["target_filters"]["file_path"] to be set.
    """
    filters = state.get("target_filters", {})
    file_path = filters.get("file_path")

    if not file_path:
        return {
            "errors": ["Ingest failed: no file_path specified in target_filters"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "请指定要导入的文件路径。"},
            ],
        }

    adapter = filters.get("adapter", "auto")

    result = parse_file.apply_async(
        kwargs=dict(file_path=file_path, adapter=adapter),
    )

    return {
        "ingest_job_id": result.id,
        "ingest_status": "pending",
        "current_step": "ingest_dispatched",
        "conversation_history": [
            {
                "role": "assistant",
                "content": f"已开始导入文件 {file_path}（任务ID: {result.id}）。正在解析中...",
            },
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/agent/test_ingest_node.py -x -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/nodes/ingest_node.py backend/tests/agent/test_ingest_node.py
git commit -m "feat(agent): add ingest subgraph node dispatching parse_file task"
```

### Task 3.3 — Write failing test for analyze node

**Files:**
- Create: `backend/tests/agent/test_analyze_node.py`
- Create: `backend/app/agent/nodes/analyze_node.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agent/test_analyze_node.py
"""Tests for the analyze subgraph node."""
import pytest
from unittest.mock import patch, MagicMock
from app.agent.state import create_initial_state
from app.agent.nodes.analyze_node import analyze_node


def test_analyze_node_dispatches_rule_task():
    state = create_initial_state(user_input="分析错题")
    state["target_session_ids"] = ["session-uuid-1"]

    with patch("app.agent.nodes.analyze_node.run_rules") as mock_rules:
        mock_result = MagicMock()
        mock_result.id = "celery-rule-123"
        mock_rules.apply_async.return_value = mock_result

        updates = analyze_node(state, config={})

    assert updates["rule_job_id"] == "celery-rule-123"
    assert updates["current_step"] == "rule_analysis_dispatched"
    mock_rules.apply_async.assert_called_once()


def test_analyze_node_errors_on_no_session():
    state = create_initial_state(user_input="分析")
    state["target_session_ids"] = []

    updates = analyze_node(state, config={})

    assert len(updates["errors"]) > 0
    assert updates["current_step"] == "error"


def test_analyze_node_appends_message():
    state = create_initial_state(user_input="分析错题")
    state["target_session_ids"] = ["session-1"]

    with patch("app.agent.nodes.analyze_node.run_rules") as mock_rules:
        mock_result = MagicMock()
        mock_result.id = "job-789"
        mock_rules.apply_async.return_value = mock_result

        updates = analyze_node(state, config={})

    assert any(m["role"] == "assistant" for m in updates["conversation_history"])


def test_analyze_node_does_not_mutate_input_state():
    state = create_initial_state(user_input="分析错题")
    state["target_session_ids"] = ["session-1"]
    original_errors = list(state["errors"])

    with patch("app.agent.nodes.analyze_node.run_rules") as mock_rules:
        mock_result = MagicMock()
        mock_result.id = "job-999"
        mock_rules.apply_async.return_value = mock_result

        analyze_node(state, config={})

    assert state["errors"] == original_errors
    assert state["current_step"] == "start"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/agent/test_analyze_node.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 3.4 — Implement analyze node

- [ ] **Step 3: Write `app/agent/nodes/analyze_node.py`**

```python
# backend/app/agent/nodes/analyze_node.py
"""Analyze subgraph node — dispatches run_rules (and optionally run_llm_judge)."""
from __future__ import annotations
from typing import Any
from app.agent.state import OrchestratorState
from app.tasks.analysis import run_rules


def analyze_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """
    LangGraph node: start rule-based analysis for target sessions.

    Returns a partial state update dict (never mutates input state).
    LLM analysis is a separate step triggered after rules complete,
    based on the configured analysis_strategy.
    """
    session_ids = state.get("target_session_ids", [])

    if not session_ids:
        return {
            "errors": ["Analyze failed: no target_session_ids specified"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "请先选择要分析的评测批次。"},
            ],
        }

    # Dispatch rule analysis for the first session (batch processing)
    session_id = session_ids[0]
    result = run_rules.apply_async(
        kwargs=dict(session_id=session_id, rule_ids=None),
    )

    return {
        "rule_job_id": result.id,
        "current_step": "rule_analysis_dispatched",
        "conversation_history": [
            {
                "role": "assistant",
                "content": f"已开始规则分析（任务ID: {result.id}），正在对评测批次 {session_id} 进行错因匹配...",
            },
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/agent/test_analyze_node.py -x -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/nodes/analyze_node.py backend/tests/agent/test_analyze_node.py
git commit -m "feat(agent): add analyze subgraph node dispatching run_rules task"
```

### Task 3.5 — Write failing test for compare node

**Files:**
- Create: `backend/tests/agent/test_compare_node.py`
- Create: `backend/app/agent/nodes/compare_node.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agent/test_compare_node.py
"""Tests for the compare subgraph node."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.agent.state import create_initial_state
from app.agent.nodes.compare_node import compare_node


def test_compare_node_calls_service():
    state = create_initial_state(user_input="对比 v1 和 v2")
    state["target_filters"] = {
        "version_a": "v1",
        "version_b": "v2",
        "benchmark": None,
    }

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.compare_node.compare_versions") as mock_cmp:
        mock_cmp.return_value = {
            "version_a": "v1",
            "version_b": "v2",
            "benchmark": None,
            "metrics_a": {"total": 100, "errors": 30, "accuracy": 0.7},
            "metrics_b": {"total": 100, "errors": 20, "accuracy": 0.8},
        }
        with patch("app.agent.nodes.compare_node.get_version_diff") as mock_diff:
            mock_diff.return_value = {
                "regressed": [], "improved": [],
                "new_errors": [], "resolved_errors": [],
            }
            updates = compare_node(state, config)

    assert updates["current_step"] == "compare_done"
    assert any(m["role"] == "assistant" for m in updates["conversation_history"])


def test_compare_node_errors_on_missing_versions():
    state = create_initial_state(user_input="对比")
    state["target_filters"] = {}

    config = {"configurable": {"db": MagicMock()}}
    updates = compare_node(state, config)

    assert len(updates["errors"]) > 0
    assert updates["current_step"] == "error"


def test_compare_node_does_not_mutate_input_state():
    state = create_initial_state(user_input="对比")
    state["target_filters"] = {}
    original_step = state["current_step"]

    config = {"configurable": {"db": MagicMock()}}
    compare_node(state, config)

    assert state["current_step"] == original_step
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/agent/test_compare_node.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 3.6 — Implement compare node

- [ ] **Step 3: Write `app/agent/nodes/compare_node.py`**

```python
# backend/app/agent/nodes/compare_node.py
"""Compare subgraph node — calls version comparison services."""
from __future__ import annotations
from typing import Any
from app.agent.state import OrchestratorState
from app.services.compare import compare_versions, get_version_diff


def compare_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """
    LangGraph node: run version comparison.

    Returns a partial state update dict (never mutates input state).
    Expects state["target_filters"]["version_a"] and ["version_b"].
    Extracts db session from config["configurable"]["db"].
    """
    filters = state.get("target_filters", {})
    version_a = filters.get("version_a")
    version_b = filters.get("version_b")

    if not version_a or not version_b:
        return {
            "errors": ["Compare failed: version_a and version_b required in target_filters"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "请指定要对比的两个模型版本（如 v1 和 v2）。"},
            ],
        }

    db = config.get("configurable", {}).get("db")
    benchmark = filters.get("benchmark")

    comparison = compare_versions(db, version_a, version_b, benchmark)
    diff = get_version_diff(db, version_a, version_b, benchmark)

    metrics_a = comparison.get("metrics_a", {})
    metrics_b = comparison.get("metrics_b", {})
    regressed_count = len(diff.get("regressed", []))
    improved_count = len(diff.get("improved", []))

    summary = (
        f"版本对比结果 ({version_a} vs {version_b}):\n"
        f"- {version_a}: 准确率 {metrics_a.get('accuracy', 0):.1%}, {metrics_a.get('errors', 0)} 道错题\n"
        f"- {version_b}: 准确率 {metrics_b.get('accuracy', 0):.1%}, {metrics_b.get('errors', 0)} 道错题\n"
        f"- 退化: {regressed_count} 题, 进步: {improved_count} 题"
    )

    return {
        "current_step": "compare_done",
        "conversation_history": [
            {"role": "assistant", "content": summary},
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/agent/test_compare_node.py -x -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/nodes/compare_node.py backend/tests/agent/test_compare_node.py
git commit -m "feat(agent): add compare subgraph node calling version comparison services"
```

### Task 3.7 — Write failing test for query node

**Files:**
- Create: `backend/tests/agent/test_query_node.py`
- Create: `backend/app/agent/nodes/query_node.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agent/test_query_node.py
"""Tests for the query subgraph node."""
import pytest
from unittest.mock import patch, MagicMock
from app.agent.state import create_initial_state
from app.agent.nodes.query_node import query_node


def test_query_node_returns_summary():
    state = create_initial_state(user_input="查看分析概览")
    state["target_filters"] = {"query_type": "summary"}

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.query_node.get_analysis_summary") as mock_summary:
        mock_summary.return_value = {
            "total_sessions": 5,
            "total_records": 1000,
            "total_errors": 300,
            "accuracy": 0.7,
            "llm_analysed_count": 50,
            "llm_total_cost": 1.23,
        }
        updates = query_node(state, config)

    assert updates["current_step"] == "query_done"
    assert any(m["role"] == "assistant" for m in updates["conversation_history"])


def test_query_node_returns_distribution():
    state = create_initial_state(user_input="错误分布")
    state["target_filters"] = {"query_type": "distribution", "group_by": "error_type"}

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.query_node.get_error_distribution") as mock_dist:
        mock_dist.return_value = [
            {"label": "推理性错误", "count": 100, "percentage": 33.3},
            {"label": "知识性错误", "count": 80, "percentage": 26.7},
        ]
        updates = query_node(state, config)

    assert updates["current_step"] == "query_done"


def test_query_node_defaults_to_summary():
    state = create_initial_state(user_input="查看结果")
    state["target_filters"] = {}

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.query_node.get_analysis_summary") as mock_summary:
        mock_summary.return_value = {
            "total_sessions": 0, "total_records": 0, "total_errors": 0,
            "accuracy": 0.0, "llm_analysed_count": 0, "llm_total_cost": 0.0,
        }
        updates = query_node(state, config)

    assert updates["current_step"] == "query_done"


def test_query_node_does_not_mutate_input_state():
    state = create_initial_state(user_input="查看结果")
    state["target_filters"] = {}
    original_step = state["current_step"]

    mock_db = MagicMock()
    config = {"configurable": {"db": mock_db}}
    with patch("app.agent.nodes.query_node.get_analysis_summary") as mock_summary:
        mock_summary.return_value = {
            "total_sessions": 0, "total_records": 0, "total_errors": 0,
            "accuracy": 0.0, "llm_analysed_count": 0, "llm_total_cost": 0.0,
        }
        query_node(state, config)

    assert state["current_step"] == original_step
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/agent/test_query_node.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 3.8 — Implement query node

- [ ] **Step 3: Write `app/agent/nodes/query_node.py`**

```python
# backend/app/agent/nodes/query_node.py
"""Query subgraph node — calls analysis_query and cross_benchmark services."""
from __future__ import annotations
from typing import Any
from app.agent.state import OrchestratorState
from app.services.analysis_query import get_analysis_summary, get_error_distribution


def query_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """
    LangGraph node: run a query and format results as a conversation message.

    Returns a partial state update dict (never mutates input state).
    Extracts db session from config["configurable"]["db"].

    Supported query_type values in target_filters:
    - 'summary' (default): analysis overview metrics
    - 'distribution': error type distribution
    """
    filters = state.get("target_filters", {})
    query_type = filters.get("query_type", "summary")
    benchmark = filters.get("benchmark")
    model_version = filters.get("model_version")

    db = config.get("configurable", {}).get("db")

    if query_type == "distribution":
        group_by = filters.get("group_by", "error_type")
        result = get_error_distribution(
            db=db,
            group_by=group_by,
            benchmark=benchmark,
            model_version=model_version,
        )
        if result:
            lines = [f"错误分布 (按 {group_by}):"]
            for item in result[:10]:  # top 10
                lines.append(f"  - {item['label']}: {item['count']} ({item['percentage']:.1f}%)")
            content = "\n".join(lines)
        else:
            content = "当前没有错误分布数据。"
    else:
        # Default: summary
        result = get_analysis_summary(
            db=db,
            benchmark=benchmark,
            model_version=model_version,
            time_range_start=None,
            time_range_end=None,
        )
        content = (
            f"分析概览:\n"
            f"- 评测批次: {result['total_sessions']}\n"
            f"- 总记录数: {result['total_records']}\n"
            f"- 错题数: {result['total_errors']}\n"
            f"- 准确率: {result['accuracy']:.1%}\n"
            f"- LLM 已分析: {result['llm_analysed_count']}\n"
            f"- LLM 总成本: ${result['llm_total_cost']:.4f}"
        )

    return {
        "current_step": "query_done",
        "conversation_history": [
            {"role": "assistant", "content": content},
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/agent/test_query_node.py -x -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/nodes/query_node.py backend/tests/agent/test_query_node.py
git commit -m "feat(agent): add query subgraph node for summary and distribution queries"
```

### Task 3.9 — Implement report node and human review node

**Files:**
- Create: `backend/app/agent/nodes/report_node.py`
- Create: `backend/app/agent/nodes/human_review_node.py`

- [ ] **Step 1: Write `app/agent/nodes/report_node.py`**

```python
# backend/app/agent/nodes/report_node.py
"""Report subgraph node — dispatches generate_report Celery task."""
from __future__ import annotations
import uuid
from typing import Any
from app.agent.state import OrchestratorState
from app.tasks.report import generate_report


def report_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """
    LangGraph node: dispatch a report generation Celery task.

    Returns a partial state update dict (never mutates input state).
    """
    filters = state.get("target_filters", {})
    report_type = filters.get("report_type", "summary")

    if not filters.get("benchmark") and not state.get("target_session_ids"):
        return {
            "errors": ["Report failed: specify benchmark or session_ids"],
            "current_step": "error",
            "conversation_history": [
                {"role": "assistant", "content": "请指定要生成报告的 benchmark 或评测批次。"},
            ],
        }

    report_id = str(uuid.uuid4())

    report_config = {
        "title": filters.get("title", f"Agent-generated {report_type} report"),
        "benchmark": filters.get("benchmark"),
        "model_version": filters.get("model_version"),
        "session_ids": state.get("target_session_ids"),
    }
    if report_type == "comparison":
        report_config["version_a"] = filters.get("version_a")
        report_config["version_b"] = filters.get("version_b")

    generate_report.apply_async(
        kwargs=dict(
            report_id=report_id,
            report_type=report_type,
            config=report_config,
        ),
    )

    return {
        "report_id": report_id,
        "report_status": "pending",
        "current_step": "report_dispatched",
        "conversation_history": [
            {"role": "assistant", "content": f"正在生成{report_type}报告（ID: {report_id}）..."},
        ],
    }
```

- [ ] **Step 2: Write `app/agent/nodes/human_review_node.py`**

```python
# backend/app/agent/nodes/human_review_node.py
"""Human-in-the-loop pause node.

When LLM analysis produces low-confidence results, the graph pauses
BEFORE this node via LangGraph's interrupt_before mechanism. The
checkpointer persists state so the conversation can resume after review.

This node runs AFTER the human resumes the graph, confirming
the review is complete and the flow can continue.
"""
from __future__ import annotations
from typing import Any
from app.agent.state import OrchestratorState


def human_review_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """
    LangGraph node: mark human review as complete and resume flow.

    The actual pause happens via interrupt_before=["human_review"]
    in the compiled graph. When the user resumes, this node executes
    to reset the needs_human_input flag and continue.
    """
    return {
        "needs_human_input": False,
        "current_step": "human_review_done",
        "conversation_history": [
            {
                "role": "assistant",
                "content": "人工审核已完成，分析流程继续。",
            },
        ],
    }
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/agent/nodes/report_node.py backend/app/agent/nodes/human_review_node.py
git commit -m "feat(agent): add report and human-review subgraph nodes"
```

---

## Phase 4 — LangGraph StateGraph Assembly

### Task 4.1 — Write failing test for graph assembly

**Files:**
- Create: `backend/tests/agent/test_graph.py`
- Create: `backend/app/agent/graph.py`
- Create: `backend/app/agent/checkpointer.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agent/test_graph.py
"""Tests for the compiled LangGraph StateGraph."""
import pytest
from unittest.mock import patch, MagicMock
from app.agent.graph import build_graph
from app.agent.state import create_initial_state


def test_build_graph_returns_compiled_graph():
    graph = build_graph()
    assert graph is not None
    # LangGraph CompiledGraph has an invoke method
    assert hasattr(graph, "invoke")


def test_graph_routes_to_query_for_summary_input():
    graph = build_graph()
    state = create_initial_state(user_input="查看分析概览")
    state["target_filters"] = {"query_type": "summary"}

    mock_db = MagicMock()
    with patch("app.agent.nodes.query_node.get_analysis_summary") as mock_summary:
        mock_summary.return_value = {
            "total_sessions": 5, "total_records": 1000,
            "total_errors": 300, "accuracy": 0.7,
            "llm_analysed_count": 50, "llm_total_cost": 1.23,
        }
        result = graph.invoke(state, config={"configurable": {"db": mock_db}})

    assert result["intent"] == "query"
    assert result["current_step"] == "query_done"


def test_graph_routes_to_ingest():
    graph = build_graph()
    state = create_initial_state(user_input="上传 /data/test.jsonl")
    state["target_filters"] = {"file_path": "/data/test.jsonl"}

    with patch("app.agent.nodes.ingest_node.parse_file") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "job-1"
        mock_task.apply_async.return_value = mock_result

        result = graph.invoke(state, config={"configurable": {}})

    assert result["intent"] == "ingest"
    assert result["current_step"] == "ingest_dispatched"


def test_graph_routes_to_analyze():
    graph = build_graph()
    state = create_initial_state(user_input="分析错题")
    state["target_session_ids"] = ["session-1"]

    with patch("app.agent.nodes.analyze_node.run_rules") as mock_rules:
        mock_result = MagicMock()
        mock_result.id = "rule-job-1"
        mock_rules.apply_async.return_value = mock_result

        result = graph.invoke(state, config={"configurable": {}})

    assert result["intent"] == "analyze"
    assert result["current_step"] == "rule_analysis_dispatched"


def test_graph_routes_to_compare():
    graph = build_graph()
    state = create_initial_state(user_input="对比 v1 和 v2")
    state["target_filters"] = {
        "version_a": "v1",
        "version_b": "v2",
    }

    mock_db = MagicMock()
    with patch("app.agent.nodes.compare_node.compare_versions") as mock_cmp:
        mock_cmp.return_value = {
            "version_a": "v1", "version_b": "v2", "benchmark": None,
            "metrics_a": {"total": 100, "errors": 30, "accuracy": 0.7},
            "metrics_b": {"total": 100, "errors": 20, "accuracy": 0.8},
        }
        with patch("app.agent.nodes.compare_node.get_version_diff") as mock_diff:
            mock_diff.return_value = {
                "regressed": [], "improved": [],
                "new_errors": [], "resolved_errors": [],
            }
            result = graph.invoke(state, config={"configurable": {"db": mock_db}})

    assert result["intent"] == "compare"
    assert result["current_step"] == "compare_done"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/agent/test_graph.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 4.2 — Implement checkpointer factory

- [ ] **Step 3: Write `app/agent/checkpointer.py`**

```python
# backend/app/agent/checkpointer.py
"""Factory for LangGraph checkpointer (memory for dev, postgres for prod)."""
from __future__ import annotations
from typing import Optional
from app.core.config import settings


def create_checkpointer(connection_string: Optional[str] = None):
    """
    Create a LangGraph checkpointer.

    - Dev / test: MemorySaver (in-memory)
    - Production: PostgresSaver (uses LANGGRAPH_CHECKPOINTER_URL or DATABASE_URL)

    Falls back to MemorySaver if no persistence backend is available.
    """
    if connection_string is None:
        connection_string = getattr(settings, "LANGGRAPH_CHECKPOINTER_URL", None)

    if connection_string and connection_string.startswith("postgres"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            return PostgresSaver.from_conn_string(connection_string)
        except ImportError:
            pass  # fall through to MemorySaver

    # Fallback: in-memory (no persistence across restarts)
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()
```

### Task 4.3 — Implement graph assembly

- [ ] **Step 4: Write `app/agent/graph.py`**

```python
# backend/app/agent/graph.py
"""Build and compile the Orchestrator Agent LangGraph StateGraph."""
from __future__ import annotations
from typing import Any, Literal
from langgraph.graph import StateGraph, END

from app.agent.state import OrchestratorState
from app.agent.intent_router import classify_intent
from app.agent.checkpointer import create_checkpointer
from app.agent.nodes.ingest_node import ingest_node
from app.agent.nodes.analyze_node import analyze_node
from app.agent.nodes.compare_node import compare_node
from app.agent.nodes.query_node import query_node
from app.agent.nodes.report_node import report_node
from app.agent.nodes.human_review_node import human_review_node


# ---------------------------------------------------------------------------
# Route node
# ---------------------------------------------------------------------------

def route_node(state: OrchestratorState, config: dict[str, Any]) -> dict:
    """Classify intent and record user message. Returns partial update."""
    intent = classify_intent(state["user_input"])
    return {
        "intent": intent,
        "conversation_history": [
            {"role": "user", "content": state["user_input"]},
        ],
    }


# ---------------------------------------------------------------------------
# Conditional edge functions
# ---------------------------------------------------------------------------

def route_by_intent(
    state: OrchestratorState,
) -> Literal["ingest", "analyze", "compare", "query", "report"]:
    """Route to the correct subgraph based on classified intent."""
    intent = state.get("intent", "query")
    if intent in ("ingest", "analyze", "compare", "query", "report"):
        return intent
    return "query"  # fallback


def check_human_review(
    state: OrchestratorState,
) -> Literal["human_review", "end"]:
    """After analysis, check if human review is needed."""
    if state.get("needs_human_input", False):
        return "human_review"
    return "end"


# ---------------------------------------------------------------------------
# Graph builder (singleton)
# ---------------------------------------------------------------------------

_compiled_graph = None


def build_graph(checkpointer=None):
    """
    Construct and compile the Orchestrator StateGraph.

    The compiled graph is cached as a module-level singleton.
    Pass checkpointer=... to override (useful for testing).

    Graph structure:
        START → route → {ingest | analyze | compare | query | report}
        analyze → check_human → {human_review | END}
        ingest / compare / query / report → END

    Human-in-the-Loop: The graph uses interrupt_before=["human_review"]
    so that execution pauses before the human_review node. The checkpointer
    persists state, and the graph can be resumed with graph.invoke(None, config).
    """
    global _compiled_graph
    if _compiled_graph is not None and checkpointer is None:
        return _compiled_graph

    graph = StateGraph(OrchestratorState)

    # Add nodes — all accept (state, config)
    graph.add_node("route", route_node)
    graph.add_node("ingest", ingest_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("compare", compare_node)
    graph.add_node("query", query_node)
    graph.add_node("report", report_node)
    graph.add_node("human_review", human_review_node)

    # Set entry point
    graph.set_entry_point("route")

    # Route → intent-based subgraph
    graph.add_conditional_edges(
        "route",
        route_by_intent,
        {
            "ingest": "ingest",
            "analyze": "analyze",
            "compare": "compare",
            "query": "query",
            "report": "report",
        },
    )

    # Ingest / Compare / Query / Report → END
    graph.add_edge("ingest", END)
    graph.add_edge("compare", END)
    graph.add_edge("query", END)
    graph.add_edge("report", END)

    # Analyze → check if human review needed → END or human_review
    graph.add_conditional_edges(
        "analyze",
        check_human_review,
        {
            "human_review": "human_review",
            "end": END,
        },
    )
    graph.add_edge("human_review", END)

    # Use provided checkpointer or create default
    if checkpointer is None:
        checkpointer = create_checkpointer()

    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )

    if checkpointer is not None:
        _compiled_graph = compiled

    return compiled
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/agent/test_graph.py -x -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/graph.py backend/app/agent/checkpointer.py backend/tests/agent/test_graph.py
git commit -m "feat(agent): assemble and compile Orchestrator StateGraph with checkpointer and HITL"
```

---

## Phase 5 — Agent API Schemas

### Task 5.1 — Write agent Pydantic schemas

**Files:**
- Create: `backend/app/schemas/agent.py`

- [ ] **Step 1: Write `app/schemas/agent.py`**

```python
# backend/app/schemas/agent.py
"""Pydantic schemas for the Agent conversation API."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None  # None = new conversation
    # Optional overrides for target context
    session_ids: Optional[list[str]] = None
    filters: Optional[dict[str, Any]] = None


class AgentMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str
    timestamp: Optional[datetime] = None


class AgentChatResponse(BaseModel):
    conversation_id: str
    messages: list[AgentMessage]
    current_step: str
    intent: str
    needs_human_input: bool = False


class ConversationListItem(BaseModel):
    conversation_id: str
    last_message: str
    intent: str
    current_step: str
    updated_at: datetime
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/agent.py
git commit -m "feat(agent): add Pydantic schemas for agent conversation API"
```

---

## Phase 6 — Agent REST API

### Task 6.1 — Write failing test for agent API

**Files:**
- Create: `backend/tests/api/test_agent_api.py`
- Create: `backend/app/api/v1/routers/agent.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_agent_api.py
"""Tests for the Agent conversation REST API."""
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-analyst-token"}


@pytest.mark.asyncio
async def test_agent_chat_new_conversation(async_client: AsyncClient, auth_headers):
    with patch("app.api.v1.routers.agent.get_graph") as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "user_input": "查看概览",
            "intent": "query",
            "conversation_history": [
                {"role": "user", "content": "查看概览"},
                {"role": "assistant", "content": "分析概览:\n- 评测批次: 5"},
            ],
            "current_step": "query_done",
            "needs_human_input": False,
            "errors": [],
            "ingest_job_id": None, "ingest_status": None,
            "target_session_ids": [], "target_filters": {},
            "analysis_strategy": "fallback",
            "rule_job_id": None, "llm_job_id": None,
            "rule_summary": None, "llm_summary": None,
            "analyzed_count": 0, "total_count": 0,
            "report_id": None, "report_status": None,
        }
        mock_get_graph.return_value = mock_graph

        resp = await async_client.post(
            "/api/v1/agent/chat",
            json={"message": "查看概览"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_id" in data
    assert data["intent"] == "query"
    assert len(data["messages"]) >= 1


@pytest.mark.asyncio
async def test_agent_chat_with_existing_conversation(async_client: AsyncClient, auth_headers):
    with patch("app.api.v1.routers.agent.get_graph") as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "user_input": "错误分布",
            "intent": "query",
            "conversation_history": [
                {"role": "user", "content": "错误分布"},
                {"role": "assistant", "content": "错误分布:"},
            ],
            "current_step": "query_done",
            "needs_human_input": False,
            "errors": [],
            "ingest_job_id": None, "ingest_status": None,
            "target_session_ids": [], "target_filters": {},
            "analysis_strategy": "fallback",
            "rule_job_id": None, "llm_job_id": None,
            "rule_summary": None, "llm_summary": None,
            "analyzed_count": 0, "total_count": 0,
            "report_id": None, "report_status": None,
        }
        mock_get_graph.return_value = mock_graph

        resp = await async_client.post(
            "/api/v1/agent/chat",
            json={
                "message": "错误分布",
                "conversation_id": "conv-existing-123",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == "conv-existing-123"


@pytest.mark.asyncio
async def test_agent_chat_requires_auth(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/agent/chat",
        json={"message": "hello"},
    )
    assert resp.status_code in (401, 403)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_agent_api.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 6.2 — Implement agent API router

- [ ] **Step 3: Write `app/api/v1/routers/agent.py`**

```python
# backend/app/api/v1/routers/agent.py
"""Agent conversation REST + WebSocket API."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.deps import require_role
from app.db.models.enums import UserRole
from app.agent.graph import build_graph
from app.agent.state import create_initial_state
from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentMessage,
)

router = APIRouter(prefix="/agent", tags=["agent"])

# Module-level graph singleton — compiled once, reused per request.
_graph = None


def get_graph():
    """Return the compiled graph singleton."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.viewer)),
):
    """
    Send a message to the Orchestrator Agent and get a response.

    If conversation_id is provided, resumes that conversation via the
    LangGraph checkpointer. Otherwise, starts a new one.
    """
    conv_id = payload.conversation_id or str(uuid.uuid4())

    state = create_initial_state(user_input=payload.message)

    # Apply optional overrides
    if payload.session_ids:
        state["target_session_ids"] = payload.session_ids
    if payload.filters:
        state["target_filters"].update(payload.filters)

    # Run the graph with thread_id for checkpointer-based conversation tracking
    graph = get_graph()
    result = graph.invoke(
        state,
        config={
            "configurable": {
                "thread_id": conv_id,
                "db": db,
            },
        },
    )

    # Format response
    messages = [
        AgentMessage(
            role=m["role"],
            content=m["content"],
            timestamp=datetime.now(timezone.utc),
        )
        for m in result.get("conversation_history", [])
    ]

    return AgentChatResponse(
        conversation_id=conv_id,
        messages=messages,
        current_step=result.get("current_step", ""),
        intent=result.get("intent", ""),
        needs_human_input=result.get("needs_human_input", False),
    )


@router.websocket("/ws")
async def agent_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for streaming agent conversations.

    Authentication: pass token as query parameter (?token=...).

    Protocol:
    - Client sends JSON: {"message": "...", "conversation_id": "..." | null, "filters": {...}}
    - Server sends JSON: {"type": "message", "data": AgentChatResponse}
    - Server sends JSON: {"type": "step", "data": {"step": "...", "intent": "..."}}
    """
    # TODO: Validate token (e.g., decode JWT) before accepting.
    # For now, reject connections without a token.
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    await websocket.accept()
    conv_id = str(uuid.uuid4())

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            conv_id = data.get("conversation_id", conv_id)

            state = create_initial_state(user_input=message)

            if data.get("session_ids"):
                state["target_session_ids"] = data["session_ids"]
            if data.get("filters"):
                state["target_filters"].update(data["filters"])

            # Send step update
            await websocket.send_json({
                "type": "step",
                "data": {"step": "routing", "intent": ""},
            })

            # Run graph with db session from async context
            async with get_db() as db:
                graph = get_graph()
                result = graph.invoke(
                    state,
                    config={
                        "configurable": {
                            "thread_id": conv_id,
                            "db": db,
                        },
                    },
                )

            # Send result
            messages = [
                {"role": m["role"], "content": m["content"]}
                for m in result.get("conversation_history", [])
            ]

            await websocket.send_json({
                "type": "message",
                "data": {
                    "conversation_id": conv_id,
                    "messages": messages,
                    "current_step": result.get("current_step", ""),
                    "intent": result.get("intent", ""),
                    "needs_human_input": result.get("needs_human_input", False),
                },
            })

    except WebSocketDisconnect:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_agent_api.py -x -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/routers/agent.py backend/tests/api/test_agent_api.py
git commit -m "feat(agent): add REST + WebSocket API for agent conversations"
```

---

## Phase 7 — Register Router + Final Integration

### Task 7.1 — Register agent router in FastAPI app

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add router import and registration**

```python
# Add to existing imports in app/main.py:
from app.api.v1.routers.agent import router as agent_router

# Add inside create_app() or at module level:
app.include_router(agent_router, prefix="/api/v1")
```

- [ ] **Step 2: Run full test suite**

Run: `cd backend && python -m pytest tests/ -x --tb=short`
Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(agent): register Orchestrator Agent router in FastAPI app"
```

### Task 7.2 — Verify API routes exist

- [ ] **Step 4: Check all agent routes**

```bash
cd backend && python -c "
from app.main import app
routes = [r.path for r in app.routes]
expected = ['/api/v1/agent/chat']
for ep in expected:
    match = any(ep in r for r in routes)
    status = 'OK' if match else 'MISSING'
    print(f'  {status}: {ep}')
assert all(any(ep in r for r in routes) for ep in expected), 'Some routes missing!'
print('All agent routes registered OK')
"
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "chore(agent): final integration checks for Orchestrator Agent"
```

---

## Dependencies on Earlier Plans

| Symbol | Location | Used by |
|---|---|---|
| `get_db` (async) | `app/db/session.py` | Agent API router |
| `require_role(UserRole.viewer)` | `app/api/v1/deps.py` | Agent API router |
| `UserRole` enum | `app/db/models/enums.py` | Agent API router |
| `settings` (singleton) | `app/core/config.py` | `checkpointer.py` |
| `parse_file` (Celery task) | `app/tasks/ingest.py` | `ingest_node` |
| `run_rules` (Celery task) | `app/tasks/analysis.py` | `analyze_node` |
| `run_llm_judge` (Celery task) | `app/tasks/analysis.py` | future `llm_strategy_node` |
| `compare_versions`, `get_version_diff` | `app/services/compare.py` | `compare_node` |
| `get_analysis_summary`, `get_error_distribution` | `app/services/analysis_query.py` | `query_node` |
| `generate_report` (Celery task) | `app/tasks/report.py` | `report_node` |
| FastAPI app | `app/main.py` | Router registration |

---

## Review Issues Fixed

This plan addresses the following issues identified in code review:

### CRITICAL fixes:
- **C1**: All nodes now return partial state update dicts instead of mutating input state
- **C2**: API router uses `AsyncSession` from `get_db()` (async); endpoint is `async def`
- **C3**: `require_role(UserRole.viewer)` uses single enum value, not list of strings
- **C4**: `from app.core.config import settings` (module-level singleton, not `get_settings()`)
- **C5**: All nodes accept `(state, config)` signature for LangGraph compatibility

### IMPORTANT fixes:
- **I1**: `build_graph()` return type documentation corrected (returns CompiledGraph)
- **I2**: Conversation state managed via LangGraph checkpointer with thread_id (no in-memory dict)
- **I3**: Graph compiled once and cached as module-level singleton via `get_graph()`
- **I4**: REST endpoint is `async def` consistent with project convention
- **I5**: All nodes use standard `(state, config)` signature; no `_wrap_with_db` needed
- **I6**: WebSocket requires token query parameter for authentication
- **I7**: WebSocket passes `db` session in config via `get_db()` context manager
- **I8**: Checkpointer wired into `build_graph()` via `graph.compile(checkpointer=...)`
- **I9**: HITL uses `interrupt_before=["human_review"]`; human_review_node resets flag on resume
- **I10**: All graph tests pass config with `configurable` consistently

### MINOR fixes:
- **M1**: `OrchestratorState` uses `Annotated[list[...], operator.add]` reducers for list fields
- **M6**: `datetime.now(timezone.utc)` instead of deprecated `datetime.utcnow()`
- **M7**: Tests use `@pytest.mark.asyncio` (project convention) instead of `@pytest.mark.anyio`
- **M5**: `report_node` validates required parameters before dispatching
