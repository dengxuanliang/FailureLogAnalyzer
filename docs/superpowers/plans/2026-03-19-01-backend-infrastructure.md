# Backend Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a fully-tested FastAPI + PostgreSQL + Redis backend skeleton with JWT authentication, Alembic-managed schema, and a Docker Compose dev environment that Plans 2 (Ingestion + Rule Engine) and 3 (LLM Judge + Agent Orchestration) can build directly on top of.

**Architecture:** A single Python 3.11 FastAPI application (`backend/`) wired to PostgreSQL 15 (all domain tables) and Redis, managed via Alembic migrations. Authentication uses JWT (python-jose + passlib[bcrypt]) with role-based dependency injection. Docker Compose runs three services: `api`, `postgres`, and `redis`.

**Tech Stack:** Python 3.11, FastAPI 0.111, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 15, Redis 7, python-jose[cryptography], passlib[bcrypt], pytest + pytest-asyncio, Docker Compose v2

---

## Phase 0 — Repository Bootstrap

### Task 0.1 — Create top-level folder skeleton
- [ ] Create directories (do NOT create files yet):
  ```
  backend/
    app/
      api/
        v1/
      core/
      db/
        models/
        migrations/
          versions/
      schemas/
      tests/
        unit/
        integration/
    alembic.ini         ← Alembic root config
  ```
- [ ] Expected result: `ls backend/app/` shows `api/ core/ db/ schemas/ tests/`

### Task 0.2 — Create `pyproject.toml` (dependency manifest)
- [ ] Create `backend/pyproject.toml`:
  ```toml
  [build-system]
  requires = ["setuptools>=68"]
  build-backend = "setuptools.backends.legacy:build"

  [project]
  name = "failure-log-analyzer"
  version = "0.1.0"
  requires-python = ">=3.11"
  dependencies = [
      "fastapi==0.111.0",
      "uvicorn[standard]==0.29.0",
      "sqlalchemy[asyncio]==2.0.30",
      "asyncpg==0.29.0",
      "alembic==1.13.1",
      "python-jose[cryptography]==3.3.0",
      "passlib[bcrypt]==1.7.4",
      "pydantic[email]==2.7.1",
      "pydantic-settings==2.2.1",
      "redis==5.0.4",
      "structlog==24.1.0",
      "python-multipart==0.0.9",
  ]

  [project.optional-dependencies]
  dev = [
      "pytest==8.2.0",
      "pytest-asyncio==0.23.6",
      "httpx==0.27.0",
      "pytest-cov==5.0.0",
  ]
  ```
- [ ] Install: `cd backend && pip install -e ".[dev]"`
- [ ] Verify: `python -c "import fastapi, sqlalchemy, alembic; print('OK')"` → prints `OK`

### Task 0.3 — Create `.env.example` and `backend/.env` for local dev
- [ ] Create `backend/.env.example`:
  ```
  DATABASE_URL=postgresql+asyncpg://fla:fla@localhost:5432/fla
  REDIS_URL=redis://localhost:6379/0
  SECRET_KEY=change-me-in-production-at-least-32-chars
  ACCESS_TOKEN_EXPIRE_MINUTES=60
  ENVIRONMENT=development
  ```
- [ ] Copy to `backend/.env` with actual dev values (git-ignored).
- [ ] Add `backend/.env` to `.gitignore` (root level).

---

## Phase 1 — Core Configuration

### Task 1.1 — Write failing test for settings loading
- [ ] Create `backend/app/tests/unit/test_settings.py`:
  ```python
  import pytest
  from app.core.config import Settings

  def test_settings_loads_from_env(monkeypatch):
      monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
      monkeypatch.setenv("SECRET_KEY", "a" * 32)
      s = Settings()
      assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
      assert len(s.SECRET_KEY) >= 32
  ```
- [ ] Run: `cd backend && pytest app/tests/unit/test_settings.py -v`
- [ ] Expected: **FAILED** (ImportError — `app.core.config` does not exist yet)

### Task 1.2 — Implement `app/core/config.py`
- [ ] Create `backend/app/core/config.py`:
  ```python
  from pydantic_settings import BaseSettings, SettingsConfigDict

  class Settings(BaseSettings):
      model_config = SettingsConfigDict(env_file=".env", extra="ignore")

      DATABASE_URL: str
      REDIS_URL: str = "redis://localhost:6379/0"
      SECRET_KEY: str
      ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
      ENVIRONMENT: str = "development"

  settings = Settings()
  ```
- [ ] Run: `cd backend && pytest app/tests/unit/test_settings.py -v`
- [ ] Expected: **PASSED**
- [ ] Commit: `git commit -m "feat: add core settings via pydantic-settings"`

---

## Phase 2 — Database Engine & Session

### Task 2.1 — Write failing test for async DB engine
- [ ] Create `backend/app/tests/unit/test_database.py`:
  ```python
  import pytest
  from sqlalchemy.ext.asyncio import AsyncEngine
  from app.db.engine import engine

  def test_engine_is_async():
      assert isinstance(engine, AsyncEngine)

  def test_engine_url_contains_asyncpg():
      assert "asyncpg" in str(engine.url)
  ```
- [ ] Run: `pytest app/tests/unit/test_database.py -v` → **FAILED**

### Task 2.2 — Implement `app/db/engine.py` and `app/db/session.py`
- [ ] Create `backend/app/db/engine.py`:
  ```python
  from sqlalchemy.ext.asyncio import create_async_engine
  from app.core.config import settings

  engine = create_async_engine(
      settings.DATABASE_URL,
      pool_size=10,
      max_overflow=20,
      echo=settings.ENVIRONMENT == "development",
  )
  ```
- [ ] Create `backend/app/db/session.py`:
  ```python
  from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
  from app.db.engine import engine

  AsyncSessionLocal = async_sessionmaker(
      engine, class_=AsyncSession, expire_on_commit=False
  )

  async def get_db() -> AsyncSession:
      async with AsyncSessionLocal() as session:
          yield session
  ```
- [ ] Run: `pytest app/tests/unit/test_database.py -v` → **PASSED**
- [ ] Commit: `git commit -m "feat: add async SQLAlchemy engine and session factory"`

---

## Phase 3 — SQLAlchemy ORM Models

### Task 3.1 — Write failing tests for model imports
- [ ] Create `backend/app/tests/unit/test_models.py`:
  ```python
  import pytest
  from app.db.models import (
      User, EvalSession, EvalRecord, AnalysisResult,
      ErrorTag, AnalysisRule, AnalysisStrategy, PromptTemplate,
  )

  def test_all_models_importable():
      assert User.__tablename__ == "users"
      assert EvalSession.__tablename__ == "eval_sessions"
      assert EvalRecord.__tablename__ == "eval_records"
      assert AnalysisResult.__tablename__ == "analysis_results"
      assert ErrorTag.__tablename__ == "error_tags"
      assert AnalysisRule.__tablename__ == "analysis_rules"
      assert AnalysisStrategy.__tablename__ == "analysis_strategies"
      assert PromptTemplate.__tablename__ == "prompt_templates"

  def test_user_columns():
      cols = {c.name for c in User.__table__.columns}
      assert {"id", "username", "email", "password_hash", "role",
              "is_active", "created_at", "updated_at"}.issubset(cols)

  def test_eval_record_has_jsonb_fields():
      cols = {c.name: c for c in EvalRecord.__table__.columns}
      assert "metadata" in cols
      assert "raw_json" in cols
  ```
- [ ] Run: `pytest app/tests/unit/test_models.py -v` → **FAILED**

### Task 3.2 — Create `app/db/models/__init__.py` base and enums
- [ ] Create `backend/app/db/models/base.py`:
  ```python
  import uuid
  from datetime import datetime, timezone
  from sqlalchemy import DateTime
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

  def utcnow():
      return datetime.now(timezone.utc)

  class Base(DeclarativeBase):
      pass

  class TimestampMixin:
      created_at: Mapped[datetime] = mapped_column(
          DateTime(timezone=True), default=utcnow, nullable=False
      )
  ```
- [ ] Create `backend/app/db/models/enums.py`:
  ```python
  import enum

  class UserRole(str, enum.Enum):
      admin = "admin"
      analyst = "analyst"
      viewer = "viewer"

  class AnalysisType(str, enum.Enum):
      rule = "rule"
      llm = "llm"
      manual = "manual"

  class SeverityLevel(str, enum.Enum):
      high = "high"
      medium = "medium"
      low = "low"

  class TagSource(str, enum.Enum):
      rule = "rule"
      llm = "llm"

  class StrategyType(str, enum.Enum):
      full = "full"
      fallback = "fallback"
      sample = "sample"
      manual = "manual"
  ```

### Task 3.3 — Implement `users` model
- [ ] Create `backend/app/db/models/user.py`:
  ```python
  import uuid
  from datetime import datetime, timezone
  from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import Mapped, mapped_column
  from app.db.models.base import Base, TimestampMixin
  from app.db.models.enums import UserRole

  class User(Base, TimestampMixin):
      __tablename__ = "users"

      id: Mapped[uuid.UUID] = mapped_column(
          UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
      )
      username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
      email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
      password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
      role: Mapped[UserRole] = mapped_column(
          SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.viewer
      )
      is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
      updated_at: Mapped[datetime] = mapped_column(
          DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
          onupdate=lambda: datetime.now(timezone.utc), nullable=False
      )
  ```

### Task 3.4 — Implement `eval_sessions` and `eval_records` models
- [ ] Create `backend/app/db/models/eval_session.py`:
  ```python
  import uuid
  from sqlalchemy import String, Integer, Float, ARRAY
  from sqlalchemy.dialects.postgresql import UUID, JSONB
  from sqlalchemy.orm import Mapped, mapped_column, relationship
  from app.db.models.base import Base, TimestampMixin

  class EvalSession(Base, TimestampMixin):
      __tablename__ = "eval_sessions"

      id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      model: Mapped[str] = mapped_column(String(128), nullable=False)
      model_version: Mapped[str] = mapped_column(String(64), nullable=False)
      benchmark: Mapped[str] = mapped_column(String(64), nullable=False)
      dataset_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
      total_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
      error_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
      accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
      config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
      tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

      records: Mapped[list["EvalRecord"]] = relationship(back_populates="session")
  ```
- [ ] Create `backend/app/db/models/eval_record.py`:

  **设计说明：** `eval_records` 按 `benchmark` LIST 分区，每个分区内再按 `created_at` 月度 RANGE 子分区（见设计文档 7.3）。SQLAlchemy ORM 仅声明主表结构和索引；实际的分区 DDL 在 Task 4.2 的手写迁移中用 `op.execute()` 执行，不依赖 autogenerate。

  ```python
  import uuid
  from sqlalchemy import String, Boolean, Float, Text, ForeignKey, Index
  from sqlalchemy.dialects.postgresql import UUID, JSONB
  from sqlalchemy.orm import Mapped, mapped_column, relationship
  from app.db.models.base import Base, TimestampMixin

  class EvalRecord(Base, TimestampMixin):
      __tablename__ = "eval_records"
      __table_args__ = (
          # 复合索引（设计文档 7.4）
          Index("ix_eval_records_benchmark_correct", "benchmark", "is_correct"),
          Index("ix_eval_records_session_correct", "session_id", "is_correct"),
          Index("ix_eval_records_task_category", "task_category"),
          Index("ix_eval_records_model_version_benchmark", "model_version", "benchmark"),
          # 版本 Diff 核心索引：跨版本同题对比
          Index("ix_eval_records_question_model_version", "question_id", "model_version"),
          # 全文搜索索引（GIN，设计文档 7.4）——声明为 postgresql_using
          Index(
              "ix_eval_records_question_fts",
              "question",
              postgresql_using="gin",
              postgresql_ops={"question": "to_tsvector('simple', question)"},
          ),
          Index(
              "ix_eval_records_model_answer_fts",
              "model_answer",
              postgresql_using="gin",
              postgresql_ops={"model_answer": "to_tsvector('simple', model_answer)"},
          ),
          # 分区表声明（postgresql_partition_by 告知 Alembic 此表为分区父表，
          # 实际 CREATE TABLE ... PARTITION BY LIST (benchmark) 在手写迁移中执行）
          {"postgresql_partition_by": "LIST (benchmark)"},
      )

      id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      session_id: Mapped[uuid.UUID] = mapped_column(
          UUID(as_uuid=True), ForeignKey("eval_sessions.id", ondelete="CASCADE"), nullable=False
      )
      benchmark: Mapped[str] = mapped_column(String(64), nullable=False)
      model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
      task_category: Mapped[str | None] = mapped_column(String(256), nullable=True)
      question_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
      question: Mapped[str | None] = mapped_column(Text, nullable=True)
      expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
      model_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
      is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
      score: Mapped[float | None] = mapped_column(Float, nullable=True)
      extracted_code: Mapped[str | None] = mapped_column(Text, nullable=True)
      metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
      raw_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

      session: Mapped["EvalSession"] = relationship(back_populates="records")
      analysis_results: Mapped[list["AnalysisResult"]] = relationship(back_populates="record")
      error_tags: Mapped[list["ErrorTag"]] = relationship(back_populates="record")
  ```

### Task 3.5 — Implement `analysis_results` and `error_tags` models

  **设计说明：** `analysis_results` 和 `error_tags` 均按 `record_id` HASH 分区（8 个分区桶，见设计文档 7.3），与 `eval_records` 对齐以优化 JOIN 性能。实际分区 DDL 在 Task 4.2 手写迁移中执行。

- [ ] Create `backend/app/db/models/analysis_result.py`:
  ```python
  import uuid
  from sqlalchemy import String, Float, Text, ForeignKey, Index, Enum as SAEnum, ARRAY
  from sqlalchemy.dialects.postgresql import UUID, JSONB
  from sqlalchemy.orm import Mapped, mapped_column, relationship
  from app.db.models.base import Base, TimestampMixin
  from app.db.models.enums import AnalysisType, SeverityLevel

  class AnalysisResult(Base, TimestampMixin):
      __tablename__ = "analysis_results"
      __table_args__ = (
          # record_id 索引加速级联查询
          Index("ix_analysis_results_record_id", "record_id"),
          # 分区表声明（HASH 8 桶，实际 DDL 在 Task 4.2 手写迁移中执行）
          {"postgresql_partition_by": "HASH (record_id)"},
      )

      id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      record_id: Mapped[uuid.UUID] = mapped_column(
          UUID(as_uuid=True), ForeignKey("eval_records.id", ondelete="CASCADE"), nullable=False
      )
      analysis_type: Mapped[AnalysisType] = mapped_column(
          SAEnum(AnalysisType, name="analysis_type"), nullable=False
      )
      error_types: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
      root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
      severity: Mapped[SeverityLevel | None] = mapped_column(
          SAEnum(SeverityLevel, name="severity_level"), nullable=True
      )
      confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
      evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
      suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
      llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
      llm_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
      prompt_template: Mapped[str | None] = mapped_column(String(256), nullable=True)
      raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
      unmatched_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

      record: Mapped["EvalRecord"] = relationship(back_populates="analysis_results")
      error_tags: Mapped[list["ErrorTag"]] = relationship(back_populates="analysis_result")
  ```
- [ ] Create `backend/app/db/models/error_tag.py`:
  ```python
  import uuid
  from sqlalchemy import String, Integer, Float, ForeignKey, Index, Enum as SAEnum
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import Mapped, mapped_column, relationship
  from app.db.models.base import Base, TimestampMixin
  from app.db.models.enums import TagSource

  class ErrorTag(Base, TimestampMixin):
      __tablename__ = "error_tags"
      __table_args__ = (
          # tag_path 索引加速按标签路径查询
          Index("ix_error_tags_tag_path", "tag_path"),
          # record_id 索引（与 analysis_results HASH 分区对齐，优化 JOIN）
          Index("ix_error_tags_record_id", "record_id"),
          # 分区表声明（HASH 8 桶，实际 DDL 在 Task 4.2 手写迁移中执行）
          {"postgresql_partition_by": "HASH (record_id)"},
      )

      id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      record_id: Mapped[uuid.UUID] = mapped_column(
          UUID(as_uuid=True), ForeignKey("eval_records.id", ondelete="CASCADE"), nullable=False
      )
      analysis_result_id: Mapped[uuid.UUID | None] = mapped_column(
          UUID(as_uuid=True), ForeignKey("analysis_results.id", ondelete="SET NULL"), nullable=True
      )
      tag_path: Mapped[str] = mapped_column(String(512), nullable=False)
      tag_level: Mapped[int] = mapped_column(Integer, nullable=False)
      source: Mapped[TagSource] = mapped_column(
          SAEnum(TagSource, name="tag_source"), nullable=False
      )
      confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

      record: Mapped["EvalRecord"] = relationship(back_populates="error_tags")
      analysis_result: Mapped["AnalysisResult"] = relationship(back_populates="error_tags")
  ```

### Task 3.6 — Implement config/strategy/template models
- [ ] Create `backend/app/db/models/analysis_rule.py`:
  ```python
  import uuid
  from datetime import datetime, timezone
  from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ARRAY
  from sqlalchemy.dialects.postgresql import UUID, JSONB
  from sqlalchemy.orm import Mapped, mapped_column
  from app.db.models.base import Base, TimestampMixin

  class AnalysisRule(Base, TimestampMixin):
      __tablename__ = "analysis_rules"

      id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
      description: Mapped[str | None] = mapped_column(Text, nullable=True)
      field: Mapped[str] = mapped_column(String(128), nullable=False)
      condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
      tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
      confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
      priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
      is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
      created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
      updated_at: Mapped[datetime] = mapped_column(
          DateTime(timezone=True),
          default=lambda: datetime.now(timezone.utc),
          onupdate=lambda: datetime.now(timezone.utc), nullable=False
      )
  ```
- [ ] Create `backend/app/db/models/analysis_strategy.py`:
  ```python
  import uuid
  from datetime import datetime, timezone
  from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
  from sqlalchemy.dialects.postgresql import UUID, JSONB
  from sqlalchemy.orm import Mapped, mapped_column
  from app.db.models.base import Base, TimestampMixin
  from app.db.models.enums import StrategyType

  class AnalysisStrategy(Base, TimestampMixin):
      __tablename__ = "analysis_strategies"

      id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      name: Mapped[str] = mapped_column(String(128), nullable=False)
      strategy_type: Mapped[StrategyType] = mapped_column(
          SAEnum(StrategyType, name="strategy_type"), nullable=False
      )
      config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
      llm_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
      llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
      prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
          UUID(as_uuid=True), ForeignKey("prompt_templates.id", ondelete="SET NULL"), nullable=True
      )
      max_concurrent: Mapped[int | None] = mapped_column(Integer, nullable=True)
      daily_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
      is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
      created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
      updated_at: Mapped[datetime] = mapped_column(
          DateTime(timezone=True),
          default=lambda: datetime.now(timezone.utc),
          onupdate=lambda: datetime.now(timezone.utc), nullable=False
      )
  ```
- [ ] Create `backend/app/db/models/prompt_template.py`:
  ```python
  import uuid
  from sqlalchemy import String, Text, Integer, Boolean
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import Mapped, mapped_column
  from app.db.models.base import Base, TimestampMixin

  class PromptTemplate(Base, TimestampMixin):
      __tablename__ = "prompt_templates"

      id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      name: Mapped[str] = mapped_column(String(128), nullable=False)
      benchmark: Mapped[str | None] = mapped_column(String(64), nullable=True)
      template: Mapped[str] = mapped_column(Text, nullable=False)
      version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
      is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
      created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
  ```

### Task 3.7 — Create models `__init__.py` re-export
- [ ] Create `backend/app/db/models/__init__.py`:
  ```python
  from app.db.models.base import Base
  from app.db.models.enums import UserRole, AnalysisType, SeverityLevel, TagSource, StrategyType
  from app.db.models.user import User
  from app.db.models.eval_session import EvalSession
  from app.db.models.eval_record import EvalRecord
  from app.db.models.analysis_result import AnalysisResult
  from app.db.models.error_tag import ErrorTag
  from app.db.models.analysis_rule import AnalysisRule
  from app.db.models.prompt_template import PromptTemplate
  from app.db.models.analysis_strategy import AnalysisStrategy

  __all__ = [
      "Base", "UserRole", "AnalysisType", "SeverityLevel", "TagSource", "StrategyType",
      "User", "EvalSession", "EvalRecord", "AnalysisResult",
      "ErrorTag", "AnalysisRule", "PromptTemplate", "AnalysisStrategy",
  ]
  ```
- [ ] Run: `pytest app/tests/unit/test_models.py -v` → **PASSED** (all 3 tests)
- [ ] Commit: `git commit -m "feat: add all ORM models for 8 domain tables"`

---

## Phase 4 — Alembic Setup and Initial Migration

### Task 4.1 — Initialize Alembic
- [ ] From `backend/`: `alembic init app/db/migrations`
- [ ] Edit `backend/alembic.ini`: set `script_location = app/db/migrations`
- [ ] Edit `backend/app/db/migrations/env.py` to:
  - Import `settings` from `app.core.config`
  - Set `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))`  
    (Alembic uses sync URL for migration; replace asyncpg with psycopg2 or use `run_sync`)
  - Import `Base` and all models: `from app.db.models import Base`
  - Set `target_metadata = Base.metadata`
  - Use the async `run_migrations_online` pattern with `asyncpg`:
    ```python
    from sqlalchemy.ext.asyncio import async_engine_from_config
    # ... standard async alembic env.py pattern
    ```
- [ ] Verify env.py by running: `alembic check` (should report "No new upgrade operations detected" since no migration exists yet)

### Task 4.2 — Hand-write initial migration (partitioned schema)

  **为什么手写？** PostgreSQL 声明式分区（`PARTITION BY LIST/HASH`）的 DDL 不由 Alembic `--autogenerate` 生成。必须手写迁移文件，用 `op.execute()` 执行原始 SQL，确保分区表、子分区、GIN 索引全部正确创建。

- [ ] Create migration file manually (do NOT run `--autogenerate`):
  ```
  cd backend && alembic revision -m "initial_schema"
  ```
  This creates an empty revision file at `app/db/migrations/versions/<hash>_initial_schema.py`.

- [ ] Replace the generated file content with the following complete migration:

  ```python
  """initial_schema

  Revision ID: 0001
  Revises:
  Create Date: 2026-03-19
  """
  from alembic import op
  import sqlalchemy as sa
  from sqlalchemy.dialects import postgresql

  revision = "0001"
  down_revision = None
  branch_labels = None
  depends_on = None


  def upgrade() -> None:
      # ── 1. ENUMs ──────────────────────────────────────────────────────────────
      op.execute("CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'viewer')")
      op.execute("CREATE TYPE analysis_type AS ENUM ('rule', 'llm', 'manual')")
      op.execute("CREATE TYPE severity_level AS ENUM ('high', 'medium', 'low')")
      op.execute("CREATE TYPE tag_source AS ENUM ('rule', 'llm')")
      op.execute("CREATE TYPE strategy_type AS ENUM ('full', 'fallback', 'sample', 'manual')")

      # ── 2. Non-partitioned tables ─────────────────────────────────────────────
      op.create_table(
          "users",
          sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
          sa.Column("username", sa.String(64), nullable=False, unique=True),
          sa.Column("email", sa.String(256), nullable=False, unique=True),
          sa.Column("password_hash", sa.String(256), nullable=False),
          sa.Column("role", sa.Enum("admin", "analyst", "viewer", name="user_role"), nullable=False),
          sa.Column("is_active", sa.Boolean, nullable=False, default=True),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
          sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
      )

      op.create_table(
          "eval_sessions",
          sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
          sa.Column("model", sa.String(128), nullable=False),
          sa.Column("model_version", sa.String(64), nullable=False),
          sa.Column("benchmark", sa.String(64), nullable=False),
          sa.Column("dataset_name", sa.String(256), nullable=True),
          sa.Column("total_count", sa.Integer, nullable=True),
          sa.Column("error_count", sa.Integer, nullable=True),
          sa.Column("accuracy", sa.Float, nullable=True),
          sa.Column("config", postgresql.JSONB, nullable=True),
          sa.Column("tags", postgresql.ARRAY(sa.String), nullable=True),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
      )

      op.create_table(
          "prompt_templates",
          sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
          sa.Column("name", sa.String(128), nullable=False),
          sa.Column("benchmark", sa.String(64), nullable=True),
          sa.Column("template", sa.Text, nullable=False),
          sa.Column("version", sa.Integer, nullable=False, default=1),
          sa.Column("is_active", sa.Boolean, nullable=False, default=True),
          sa.Column("created_by", sa.String(128), nullable=True),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
      )

      op.create_table(
          "analysis_rules",
          sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
          sa.Column("name", sa.String(128), nullable=False, unique=True),
          sa.Column("description", sa.Text, nullable=True),
          sa.Column("field", sa.String(128), nullable=False),
          sa.Column("condition", postgresql.JSONB, nullable=False),
          sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False),
          sa.Column("confidence", sa.Float, nullable=False, default=1.0),
          sa.Column("priority", sa.Integer, nullable=False, default=100),
          sa.Column("is_active", sa.Boolean, nullable=False, default=True),
          sa.Column("created_by", sa.String(128), nullable=True),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
          sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
      )

      op.create_table(
          "analysis_strategies",
          sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
          sa.Column("name", sa.String(128), nullable=False),
          sa.Column("strategy_type", sa.Enum("full", "fallback", "sample", "manual", name="strategy_type"), nullable=False),
          sa.Column("config", postgresql.JSONB, nullable=True),
          sa.Column("llm_provider", sa.String(64), nullable=True),
          sa.Column("llm_model", sa.String(128), nullable=True),
          sa.Column("prompt_template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_templates.id", ondelete="SET NULL"), nullable=True),
          sa.Column("max_concurrent", sa.Integer, nullable=True),
          sa.Column("daily_budget", sa.Float, nullable=True),
          sa.Column("is_active", sa.Boolean, nullable=False, default=True),
          sa.Column("created_by", sa.String(128), nullable=True),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
          sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
      )

      # ── 3. eval_records — LIST partitioned by benchmark ───────────────────────
      # 父表：PARTITION BY LIST (benchmark)
      op.execute("""
          CREATE TABLE eval_records (
              id          UUID NOT NULL,
              session_id  UUID NOT NULL REFERENCES eval_sessions(id) ON DELETE CASCADE,
              benchmark   VARCHAR(64) NOT NULL,
              model_version VARCHAR(64),
              task_category VARCHAR(256),
              question_id  VARCHAR(256),
              question     TEXT,
              expected_answer TEXT,
              model_answer TEXT,
              is_correct   BOOLEAN,
              score        FLOAT,
              extracted_code TEXT,
              metadata     JSONB,
              raw_json     JSONB,
              created_at   TIMESTAMPTZ NOT NULL,
              PRIMARY KEY (id, benchmark)
          ) PARTITION BY LIST (benchmark)
      """)

      # 按常见 benchmark 创建 LIST 子分区（各分区内再按月 RANGE 子分区）
      # mmlu
      op.execute("""
          CREATE TABLE eval_records_mmlu
              PARTITION OF eval_records
              FOR VALUES IN ('mmlu')
              PARTITION BY RANGE (created_at)
      """)
      op.execute("""
          CREATE TABLE eval_records_mmlu_2026_01
              PARTITION OF eval_records_mmlu
              FOR VALUES FROM ('2026-01-01') TO ('2026-02-01')
      """)
      op.execute("""
          CREATE TABLE eval_records_mmlu_2026_02
              PARTITION OF eval_records_mmlu
              FOR VALUES FROM ('2026-02-01') TO ('2026-03-01')
      """)
      op.execute("""
          CREATE TABLE eval_records_mmlu_2026_03
              PARTITION OF eval_records_mmlu
              FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
      """)

      # gsm8k
      op.execute("""
          CREATE TABLE eval_records_gsm8k
              PARTITION OF eval_records
              FOR VALUES IN ('gsm8k')
              PARTITION BY RANGE (created_at)
      """)
      op.execute("""
          CREATE TABLE eval_records_gsm8k_2026_01
              PARTITION OF eval_records_gsm8k
              FOR VALUES FROM ('2026-01-01') TO ('2026-02-01')
      """)
      op.execute("""
          CREATE TABLE eval_records_gsm8k_2026_02
              PARTITION OF eval_records_gsm8k
              FOR VALUES FROM ('2026-02-01') TO ('2026-03-01')
      """)
      op.execute("""
          CREATE TABLE eval_records_gsm8k_2026_03
              PARTITION OF eval_records_gsm8k
              FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
      """)

      # humaneval
      op.execute("""
          CREATE TABLE eval_records_humaneval
              PARTITION OF eval_records
              FOR VALUES IN ('humaneval')
              PARTITION BY RANGE (created_at)
      """)
      op.execute("""
          CREATE TABLE eval_records_humaneval_2026_01
              PARTITION OF eval_records_humaneval
              FOR VALUES FROM ('2026-01-01') TO ('2026-02-01')
      """)
      op.execute("""
          CREATE TABLE eval_records_humaneval_2026_02
              PARTITION OF eval_records_humaneval
              FOR VALUES FROM ('2026-02-01') TO ('2026-03-01')
      """)
      op.execute("""
          CREATE TABLE eval_records_humaneval_2026_03
              PARTITION OF eval_records_humaneval
              FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
      """)

      # bbh (BIG-Bench Hard)
      op.execute("""
          CREATE TABLE eval_records_bbh
              PARTITION OF eval_records
              FOR VALUES IN ('bbh')
              PARTITION BY RANGE (created_at)
      """)
      op.execute("""
          CREATE TABLE eval_records_bbh_2026_03
              PARTITION OF eval_records_bbh
              FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
      """)

      # default 分区（捕获所有未知 benchmark）
      op.execute("""
          CREATE TABLE eval_records_default
              PARTITION OF eval_records
              DEFAULT
      """)

      # ── 4. eval_records 索引（在父表上创建，自动传播到所有子分区）─────────────
      op.execute("CREATE INDEX ix_eval_records_benchmark_correct ON eval_records (benchmark, is_correct)")
      op.execute("CREATE INDEX ix_eval_records_session_correct ON eval_records (session_id, is_correct)")
      op.execute("CREATE INDEX ix_eval_records_task_category ON eval_records (task_category)")
      op.execute("CREATE INDEX ix_eval_records_model_version_benchmark ON eval_records (model_version, benchmark)")
      op.execute("CREATE INDEX ix_eval_records_question_model_version ON eval_records (question_id, model_version)")

      # GIN 索引：metadata JSONB（设计文档 7.4）
      op.execute("CREATE INDEX ix_eval_records_metadata_gin ON eval_records USING gin (metadata)")

      # GIN 全文搜索索引：question 和 model_answer（设计文档 7.4）
      op.execute("""
          CREATE INDEX ix_eval_records_question_fts
              ON eval_records
              USING gin (to_tsvector('simple', coalesce(question, '')))
      """)
      op.execute("""
          CREATE INDEX ix_eval_records_model_answer_fts
              ON eval_records
              USING gin (to_tsvector('simple', coalesce(model_answer, '')))
      """)

      # ── 5. analysis_results — HASH partitioned by record_id (8 buckets) ───────
      op.execute("""
          CREATE TABLE analysis_results (
              id               UUID NOT NULL,
              record_id        UUID NOT NULL REFERENCES eval_records(id) ON DELETE CASCADE,
              analysis_type    analysis_type NOT NULL,
              error_types      TEXT[],
              root_cause       TEXT,
              severity         severity_level,
              confidence       FLOAT,
              evidence         TEXT,
              suggestion       TEXT,
              llm_model        VARCHAR(128),
              llm_cost         FLOAT,
              prompt_template  VARCHAR(256),
              raw_response     JSONB,
              unmatched_tags   TEXT[],
              created_at       TIMESTAMPTZ NOT NULL,
              PRIMARY KEY (id, record_id)
          ) PARTITION BY HASH (record_id)
      """)

      for i in range(8):
          op.execute(f"""
              CREATE TABLE analysis_results_p{i}
                  PARTITION OF analysis_results
                  FOR VALUES WITH (modulus 8, remainder {i})
          """)

      op.execute("CREATE INDEX ix_analysis_results_record_id ON analysis_results (record_id)")

      # ── 6. error_tags — HASH partitioned by record_id (8 buckets) ────────────
      op.execute("""
          CREATE TABLE error_tags (
              id                  UUID NOT NULL,
              record_id           UUID NOT NULL REFERENCES eval_records(id) ON DELETE CASCADE,
              analysis_result_id  UUID REFERENCES analysis_results(id) ON DELETE SET NULL,
              tag_path            VARCHAR(512) NOT NULL,
              tag_level           INTEGER NOT NULL,
              source              tag_source NOT NULL,
              confidence          FLOAT,
              created_at          TIMESTAMPTZ NOT NULL,
              PRIMARY KEY (id, record_id)
          ) PARTITION BY HASH (record_id)
      """)

      for i in range(8):
          op.execute(f"""
              CREATE TABLE error_tags_p{i}
                  PARTITION OF error_tags
                  FOR VALUES WITH (modulus 8, remainder {i})
          """)

      op.execute("CREATE INDEX ix_error_tags_record_id ON error_tags (record_id)")
      op.execute("CREATE INDEX ix_error_tags_tag_path ON error_tags (tag_path)")


  def downgrade() -> None:
      # 删除顺序：子表 → 父表 → 依赖表（反向）
      op.execute("DROP TABLE IF EXISTS error_tags CASCADE")
      op.execute("DROP TABLE IF EXISTS analysis_results CASCADE")
      op.execute("DROP TABLE IF EXISTS eval_records CASCADE")
      op.execute("DROP TABLE IF EXISTS analysis_strategies CASCADE")
      op.execute("DROP TABLE IF EXISTS analysis_rules CASCADE")
      op.execute("DROP TABLE IF EXISTS prompt_templates CASCADE")
      op.execute("DROP TABLE IF EXISTS eval_sessions CASCADE")
      op.execute("DROP TABLE IF EXISTS users CASCADE")

      op.execute("DROP TYPE IF EXISTS strategy_type")
      op.execute("DROP TYPE IF EXISTS tag_source")
      op.execute("DROP TYPE IF EXISTS severity_level")
      op.execute("DROP TYPE IF EXISTS analysis_type")
      op.execute("DROP TYPE IF EXISTS user_role")
  ```

- [ ] Commit: `git commit -m "feat: add hand-written Alembic migration with partitioned tables and GIN indexes"`

### Task 4.3 — Write migration smoke test (with partition + index assertions)
- [ ] Create `backend/app/tests/integration/test_migrations.py`:
  ```python
  """
  Smoke test: run alembic upgrade head + downgrade base against a real DB.
  Also asserts that partitioned tables and GIN indexes were created correctly.
  Requires TEST_DATABASE_URL env var pointing to a scratch postgres DB.
  Skip if not available.
  """
  import os
  import subprocess
  import pytest
  import psycopg2

  pytestmark = pytest.mark.skipif(
      not os.getenv("TEST_DATABASE_URL"),
      reason="TEST_DATABASE_URL not set — skipping migration integration test"
  )

  def _sync_url(url: str) -> str:
      """Convert asyncpg URL to psycopg2 URL for direct assertions."""
      return url.replace("postgresql+asyncpg://", "postgresql://")

  def test_alembic_upgrade_and_downgrade():
      db_url = os.environ["TEST_DATABASE_URL"]
      env = {**os.environ, "DATABASE_URL": db_url}

      result = subprocess.run(
          ["alembic", "upgrade", "head"],
          capture_output=True, text=True, cwd="backend", env=env
      )
      assert result.returncode == 0, result.stderr

      # ── Assert partitioned tables exist ───────────────────────────────────────
      conn = psycopg2.connect(_sync_url(db_url))
      conn.autocommit = True
      cur = conn.cursor()

      # eval_records should be a partitioned table
      cur.execute("""
          SELECT relkind FROM pg_class
          WHERE relname = 'eval_records' AND relkind = 'p'
      """)
      assert cur.fetchone() is not None, "eval_records is not a partitioned table"

      # analysis_results should be a partitioned table
      cur.execute("""
          SELECT relkind FROM pg_class
          WHERE relname = 'analysis_results' AND relkind = 'p'
      """)
      assert cur.fetchone() is not None, "analysis_results is not a partitioned table"

      # error_tags should be a partitioned table
      cur.execute("""
          SELECT relkind FROM pg_class
          WHERE relname = 'error_tags' AND relkind = 'p'
      """)
      assert cur.fetchone() is not None, "error_tags is not a partitioned table"

      # eval_records sub-partitions for known benchmarks
      for partition in ("eval_records_mmlu", "eval_records_gsm8k", "eval_records_humaneval",
                        "eval_records_bbh", "eval_records_default"):
          cur.execute("SELECT relname FROM pg_class WHERE relname = %s", (partition,))
          assert cur.fetchone() is not None, f"Missing partition: {partition}"

      # analysis_results HASH sub-partitions (p0 .. p7)
      for i in range(8):
          cur.execute("SELECT relname FROM pg_class WHERE relname = %s", (f"analysis_results_p{i}",))
          assert cur.fetchone() is not None, f"Missing analysis_results_p{i}"

      # error_tags HASH sub-partitions (p0 .. p7)
      for i in range(8):
          cur.execute("SELECT relname FROM pg_class WHERE relname = %s", (f"error_tags_p{i}",))
          assert cur.fetchone() is not None, f"Missing error_tags_p{i}"

      # ── Assert GIN indexes exist ───────────────────────────────────────────────
      for idx in (
          "ix_eval_records_metadata_gin",
          "ix_eval_records_question_fts",
          "ix_eval_records_model_answer_fts",
      ):
          cur.execute("SELECT indexname FROM pg_indexes WHERE indexname = %s", (idx,))
          assert cur.fetchone() is not None, f"Missing GIN index: {idx}"

      cur.close()
      conn.close()

      # ── Downgrade ─────────────────────────────────────────────────────────────
      result = subprocess.run(
          ["alembic", "downgrade", "base"],
          capture_output=True, text=True, cwd="backend", env=env
      )
      assert result.returncode == 0, result.stderr

      # Verify tables are gone after downgrade
      conn = psycopg2.connect(_sync_url(db_url))
      cur = conn.cursor()
      cur.execute("SELECT tablename FROM pg_tables WHERE tablename = 'eval_records'")
      assert cur.fetchone() is None, "eval_records should not exist after downgrade"
      cur.close()
      conn.close()
  ```
- [ ] Add `psycopg2-binary` to dev dependencies in `pyproject.toml`:
  ```toml
  dev = [
      ...,
      "psycopg2-binary==2.9.9",
  ]
  ```
- [ ] Run with real DB: `TEST_DATABASE_URL=postgresql+asyncpg://fla:fla@localhost/fla_test pytest app/tests/integration/test_migrations.py -v`
- [ ] Expected: **PASSED** (upgrade, partition/index assertions, downgrade all pass)

---

## Phase 5 — JWT Authentication

### Task 5.1 — Write failing tests for auth utilities
- [ ] Create `backend/app/tests/unit/test_auth.py`:
  ```python
  import pytest
  from datetime import timedelta
  from app.core.auth import (
      hash_password, verify_password,
      create_access_token, decode_access_token,
  )

  def test_password_hash_and_verify():
      hashed = hash_password("secret123")
      assert hashed != "secret123"
      assert verify_password("secret123", hashed)
      assert not verify_password("wrong", hashed)

  def test_create_and_decode_token():
      token = create_access_token({"sub": "user-uuid-1", "role": "analyst"})
      payload = decode_access_token(token)
      assert payload["sub"] == "user-uuid-1"
      assert payload["role"] == "analyst"

  def test_expired_token_raises():
      token = create_access_token(
          {"sub": "user-uuid-1"}, expires_delta=timedelta(seconds=-1)
      )
      with pytest.raises(Exception):
          decode_access_token(token)

  def test_invalid_token_raises():
      with pytest.raises(Exception):
          decode_access_token("not.a.valid.jwt")
  ```
- [ ] Run: `pytest app/tests/unit/test_auth.py -v` → **FAILED**

### Task 5.2 — Implement `app/core/auth.py`
- [ ] Create `backend/app/core/auth.py`:
  ```python
  from datetime import datetime, timedelta, timezone
  from typing import Any
  from jose import jwt, JWTError
  from passlib.context import CryptContext
  from app.core.config import settings

  ALGORITHM = "HS256"

  _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

  def hash_password(password: str) -> str:
      return _pwd_ctx.hash(password)

  def verify_password(plain: str, hashed: str) -> bool:
      return _pwd_ctx.verify(plain, hashed)

  def create_access_token(
      data: dict[str, Any],
      expires_delta: timedelta | None = None,
  ) -> str:
      expire = datetime.now(timezone.utc) + (
          expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
      )
      payload = {**data, "exp": expire}
      return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

  def decode_access_token(token: str) -> dict[str, Any]:
      try:
          return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
      except JWTError as exc:
          raise ValueError(f"Invalid token: {exc}") from exc
  ```
- [ ] Run: `pytest app/tests/unit/test_auth.py -v` → **PASSED** (4 tests)
- [ ] Commit: `git commit -m "feat: add JWT auth utilities (hash, verify, encode, decode)"`

### Task 5.3 — Write failing tests for FastAPI auth dependency
- [ ] Create `backend/app/tests/unit/test_auth_deps.py`:
  ```python
  import pytest
  from fastapi import HTTPException
  from unittest.mock import AsyncMock, MagicMock
  from app.api.v1.deps import get_current_user, require_role
  from app.db.models.enums import UserRole

  # Tests are written as unit tests against the dependency functions directly.

  @pytest.mark.asyncio
  async def test_require_role_passes_when_role_matches():
      mock_user = MagicMock()
      mock_user.role = UserRole.analyst
      checker = require_role(UserRole.analyst)
      # Should not raise
      result = await checker(current_user=mock_user)
      assert result == mock_user

  @pytest.mark.asyncio
  async def test_require_role_raises_403_for_insufficient_role():
      mock_user = MagicMock()
      mock_user.role = UserRole.viewer
      checker = require_role(UserRole.analyst)
      with pytest.raises(HTTPException) as exc_info:
          await checker(current_user=mock_user)
      assert exc_info.value.status_code == 403
  ```
- [ ] Run: `pytest app/tests/unit/test_auth_deps.py -v` → **FAILED**

### Task 5.4 — Implement `app/api/v1/deps.py` (auth dependencies)
- [ ] Create `backend/app/api/v1/deps.py`:
  ```python
  from fastapi import Depends, HTTPException, status
  from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select
  from app.db.session import get_db
  from app.db.models.user import User
  from app.db.models.enums import UserRole
  from app.core.auth import decode_access_token

  _bearer = HTTPBearer()

  ROLE_ORDER = [UserRole.viewer, UserRole.analyst, UserRole.admin]

  async def get_current_user(
      credentials: HTTPAuthorizationCredentials = Depends(_bearer),
      db: AsyncSession = Depends(get_db),
  ) -> User:
      try:
          payload = decode_access_token(credentials.credentials)
          user_id: str = payload.get("sub")
          if not user_id:
              raise ValueError("Missing sub")
      except ValueError:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Invalid authentication token",
              headers={"WWW-Authenticate": "Bearer"},
          )
      result = await db.execute(select(User).where(User.id == user_id))
      user = result.scalar_one_or_none()
      if user is None or not user.is_active:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
      return user

  def require_role(minimum_role: UserRole):
      """Returns a dependency that enforces minimum role level."""
      async def _check(current_user: User = Depends(get_current_user)) -> User:
          if ROLE_ORDER.index(current_user.role) < ROLE_ORDER.index(minimum_role):
              raise HTTPException(
                  status_code=status.HTTP_403_FORBIDDEN,
                  detail=f"Role '{minimum_role.value}' or higher required",
              )
          return current_user
      return _check
  ```
- [ ] Run: `pytest app/tests/unit/test_auth_deps.py -v` → **PASSED**
- [ ] Commit: `git commit -m "feat: add FastAPI auth dependency with role enforcement"`

### Task 5.5 — Write and implement auth router (login + register)
- [ ] Write failing test first — `backend/app/tests/unit/test_auth_router.py`:
  ```python
  import pytest
  from httpx import AsyncClient, ASGITransport
  from unittest.mock import AsyncMock, patch, MagicMock
  from app.main import app

  @pytest.mark.asyncio
  async def test_login_returns_token_shape():
      """Test that /auth/login returns access_token and token_type."""
      mock_user = MagicMock()
      mock_user.id = "test-uuid"
      mock_user.role.value = "analyst"
      mock_user.is_active = True
      mock_user.password_hash = "$2b$12$placeholder"

      with patch("app.api.v1.routers.auth.authenticate_user", return_value=mock_user):
          async with AsyncClient(
              transport=ASGITransport(app=app), base_url="http://test"
          ) as client:
              resp = await client.post(
                  "/api/v1/auth/login",
                  data={"username": "test", "password": "pass"}
              )
          assert resp.status_code == 200
          body = resp.json()
          assert "access_token" in body
          assert body["token_type"] == "bearer"
  ```
- [ ] Run: `pytest app/tests/unit/test_auth_router.py -v` → **FAILED**
- [ ] Create `backend/app/api/v1/routers/auth.py`:
  ```python
  from fastapi import APIRouter, Depends, HTTPException, status
  from fastapi.security import OAuth2PasswordRequestForm
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select
  from pydantic import BaseModel
  from app.db.session import get_db
  from app.db.models.user import User
  from app.core.auth import verify_password, create_access_token

  router = APIRouter(prefix="/auth", tags=["auth"])

  class TokenResponse(BaseModel):
      access_token: str
      token_type: str = "bearer"

  async def authenticate_user(username: str, password: str, db: AsyncSession) -> User | None:
      result = await db.execute(select(User).where(User.username == username))
      user = result.scalar_one_or_none()
      if not user or not verify_password(password, user.password_hash):
          return None
      return user

  @router.post("/login", response_model=TokenResponse)
  async def login(
      form: OAuth2PasswordRequestForm = Depends(),
      db: AsyncSession = Depends(get_db),
  ):
      user = await authenticate_user(form.username, form.password, db)
      if not user or not user.is_active:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Incorrect username or password",
              headers={"WWW-Authenticate": "Bearer"},
          )
      token = create_access_token({"sub": str(user.id), "role": user.role.value})
      return TokenResponse(access_token=token)
  ```
- [ ] Run: `pytest app/tests/unit/test_auth_router.py -v` → **PASSED**
- [ ] Commit: `git commit -m "feat: add /api/v1/auth/login endpoint"`

### Task 5.6 — Write and implement user management endpoints (Admin CRUD)

Design doc §11 requires Admin to manage users (create/edit/deactivate/role-assign). These endpoints complement the auth router.

- [ ] Write failing test — `backend/app/tests/unit/test_users_router.py`:
  ```python
  import pytest
  from httpx import AsyncClient, ASGITransport
  from unittest.mock import AsyncMock, patch, MagicMock
  from app.main import app
  from app.db.models.enums import UserRole


  def _make_admin_user():
      user = MagicMock()
      user.id = "admin-uuid"
      user.username = "admin"
      user.email = "admin@example.com"
      user.role = UserRole.admin
      user.is_active = True
      return user


  def _make_analyst_user():
      user = MagicMock()
      user.id = "analyst-uuid"
      user.username = "analyst"
      user.email = "analyst@example.com"
      user.role = UserRole.analyst
      user.is_active = True
      return user


  @pytest.mark.asyncio
  async def test_list_users_admin_ok():
      """Admin can list all users."""
      mock_users = [_make_admin_user(), _make_analyst_user()]
      with patch("app.api.v1.deps.get_current_user", return_value=_make_admin_user()), \
           patch("app.api.v1.routers.users.list_all_users", return_value=mock_users):
          async with AsyncClient(
              transport=ASGITransport(app=app), base_url="http://test"
          ) as client:
              resp = await client.get("/api/v1/users")
          assert resp.status_code == 200
          assert len(resp.json()) == 2


  @pytest.mark.asyncio
  async def test_list_users_analyst_forbidden():
      """Non-admin users cannot list users."""
      with patch("app.api.v1.deps.get_current_user", return_value=_make_analyst_user()):
          async with AsyncClient(
              transport=ASGITransport(app=app), base_url="http://test"
          ) as client:
              resp = await client.get("/api/v1/users")
          assert resp.status_code == 403


  @pytest.mark.asyncio
  async def test_create_user_admin_ok():
      """Admin can create a new user."""
      new_user = MagicMock()
      new_user.id = "new-uuid"
      new_user.username = "newuser"
      new_user.email = "new@example.com"
      new_user.role = UserRole.analyst
      new_user.is_active = True
      new_user.created_at = "2026-01-01T00:00:00"
      new_user.updated_at = "2026-01-01T00:00:00"

      with patch("app.api.v1.deps.get_current_user", return_value=_make_admin_user()), \
           patch("app.api.v1.routers.users.create_user_in_db", return_value=new_user):
          async with AsyncClient(
              transport=ASGITransport(app=app), base_url="http://test"
          ) as client:
              resp = await client.post("/api/v1/users", json={
                  "username": "newuser",
                  "email": "new@example.com",
                  "password": "securepass123",
                  "role": "analyst",
              })
          assert resp.status_code == 201
          assert resp.json()["username"] == "newuser"


  @pytest.mark.asyncio
  async def test_update_user_role():
      """Admin can change a user's role."""
      updated = _make_analyst_user()
      updated.role = UserRole.viewer

      with patch("app.api.v1.deps.get_current_user", return_value=_make_admin_user()), \
           patch("app.api.v1.routers.users.update_user_in_db", return_value=updated):
          async with AsyncClient(
              transport=ASGITransport(app=app), base_url="http://test"
          ) as client:
              resp = await client.patch("/api/v1/users/analyst-uuid", json={
                  "role": "viewer",
              })
          assert resp.status_code == 200


  @pytest.mark.asyncio
  async def test_deactivate_user():
      """Admin can deactivate a user."""
      deactivated = _make_analyst_user()
      deactivated.is_active = False

      with patch("app.api.v1.deps.get_current_user", return_value=_make_admin_user()), \
           patch("app.api.v1.routers.users.update_user_in_db", return_value=deactivated):
          async with AsyncClient(
              transport=ASGITransport(app=app), base_url="http://test"
          ) as client:
              resp = await client.patch("/api/v1/users/analyst-uuid", json={
                  "is_active": False,
              })
          assert resp.status_code == 200


  @pytest.mark.asyncio
  async def test_admin_cannot_deactivate_self():
      """Admin cannot deactivate their own account."""
      with patch("app.api.v1.deps.get_current_user", return_value=_make_admin_user()):
          async with AsyncClient(
              transport=ASGITransport(app=app), base_url="http://test"
          ) as client:
              resp = await client.patch("/api/v1/users/admin-uuid", json={
                  "is_active": False,
              })
          assert resp.status_code == 400
  ```

- [ ] Run: `pytest app/tests/unit/test_users_router.py -v` → **FAILED**

- [ ] Create `backend/app/schemas/user.py`:
  ```python
  from __future__ import annotations
  from pydantic import BaseModel, EmailStr
  from app.db.models.enums import UserRole


  class UserResponse(BaseModel):
      id: str
      username: str
      email: str
      role: UserRole
      is_active: bool
      created_at: str
      updated_at: str

      model_config = {"from_attributes": True}


  class UserCreate(BaseModel):
      username: str
      email: EmailStr
      password: str
      role: UserRole = UserRole.analyst


  class UserUpdate(BaseModel):
      username: str | None = None
      email: EmailStr | None = None
      password: str | None = None
      role: UserRole | None = None
      is_active: bool | None = None
  ```

- [ ] Create `backend/app/api/v1/routers/users.py`:
  ```python
  from fastapi import APIRouter, Depends, HTTPException, status
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select
  from app.db.session import get_db
  from app.db.models.user import User
  from app.db.models.enums import UserRole
  from app.core.auth import hash_password
  from app.api.v1.deps import get_current_user, require_role
  from app.schemas.user import UserCreate, UserUpdate, UserResponse

  router = APIRouter(prefix="/users", tags=["users"])


  async def list_all_users(db: AsyncSession) -> list[User]:
      result = await db.execute(select(User).order_by(User.created_at.desc()))
      return list(result.scalars().all())


  async def create_user_in_db(db: AsyncSession, data: UserCreate) -> User:
      # Check uniqueness
      existing = await db.execute(
          select(User).where(
              (User.username == data.username) | (User.email == data.email)
          )
      )
      if existing.scalar_one_or_none():
          raise HTTPException(
              status_code=status.HTTP_409_CONFLICT,
              detail="Username or email already exists",
          )
      user = User(
          username=data.username,
          email=data.email,
          password_hash=hash_password(data.password),
          role=data.role,
      )
      db.add(user)
      await db.commit()
      await db.refresh(user)
      return user


  async def update_user_in_db(
      db: AsyncSession, user_id: str, data: UserUpdate
  ) -> User:
      result = await db.execute(select(User).where(User.id == user_id))
      user = result.scalar_one_or_none()
      if not user:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"User {user_id!r} not found",
          )
      update_fields = data.model_dump(exclude_unset=True)
      if "password" in update_fields:
          update_fields["password_hash"] = hash_password(update_fields.pop("password"))
      for field, value in update_fields.items():
          setattr(user, field, value)
      await db.commit()
      await db.refresh(user)
      return user


  @router.get("", response_model=list[UserResponse])
  async def list_users(
      current_user=Depends(require_role(UserRole.admin)),
      db: AsyncSession = Depends(get_db),
  ):
      """GET /api/v1/users — List all users (Admin only)."""
      return await list_all_users(db)


  @router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
  async def create_user(
      body: UserCreate,
      current_user=Depends(require_role(UserRole.admin)),
      db: AsyncSession = Depends(get_db),
  ):
      """POST /api/v1/users — Create a new user (Admin only)."""
      return await create_user_in_db(db, body)


  @router.patch("/{user_id}", response_model=UserResponse)
  async def update_user(
      user_id: str,
      body: UserUpdate,
      current_user=Depends(require_role(UserRole.admin)),
      db: AsyncSession = Depends(get_db),
  ):
      """PATCH /api/v1/users/{id} — Update user fields (Admin only)."""
      # Prevent admin from deactivating themselves
      if user_id == str(current_user.id) and body.is_active is False:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Cannot deactivate your own account",
          )
      return await update_user_in_db(db, user_id, body)


  @router.get("/{user_id}", response_model=UserResponse)
  async def get_user(
      user_id: str,
      current_user=Depends(require_role(UserRole.admin)),
      db: AsyncSession = Depends(get_db),
  ):
      """GET /api/v1/users/{id} — Get user details (Admin only)."""
      result = await db.execute(select(User).where(User.id == user_id))
      user = result.scalar_one_or_none()
      if not user:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"User {user_id!r} not found",
          )
      return user
  ```

- [ ] Register the router in `backend/app/api/v1/routers/__init__.py` (Modify):
  ```python
  from app.api.v1.routers import users
  api_router.include_router(users.router)
  ```

- [ ] Run: `pytest app/tests/unit/test_users_router.py -v` → **PASSED** (6 tests)
- [ ] Commit: `git commit -m "feat: add user management CRUD endpoints (Admin only)"`

---

## Phase 6 — Health Check Endpoint

### Task 6.1 — Write failing test for health endpoint
- [ ] Create `backend/app/tests/unit/test_health.py`:
  ```python
  import pytest
  from httpx import AsyncClient, ASGITransport
  from unittest.mock import patch, AsyncMock

  @pytest.mark.asyncio
  async def test_health_returns_200_when_all_ok():
      from app.main import app
      # Mock DB and Redis checks so test runs without real services
      with patch("app.api.v1.routers.health.check_db", new_callable=AsyncMock, return_value=True), \
           patch("app.api.v1.routers.health.check_redis", new_callable=AsyncMock, return_value=True):
          async with AsyncClient(
              transport=ASGITransport(app=app), base_url="http://test"
          ) as client:
              resp = await client.get("/api/v1/health")
          assert resp.status_code == 200
          body = resp.json()
          assert body["status"] == "ok"
          assert body["checks"]["db"] is True
          assert body["checks"]["redis"] is True

  @pytest.mark.asyncio
  async def test_health_returns_503_when_db_down():
      from app.main import app
      with patch("app.api.v1.routers.health.check_db", new_callable=AsyncMock, return_value=False), \
           patch("app.api.v1.routers.health.check_redis", new_callable=AsyncMock, return_value=True):
          async with AsyncClient(
              transport=ASGITransport(app=app), base_url="http://test"
          ) as client:
              resp = await client.get("/api/v1/health")
          assert resp.status_code == 503
          assert resp.json()["status"] == "degraded"
  ```
- [ ] Run: `pytest app/tests/unit/test_health.py -v` → **FAILED**

### Task 6.2 — Implement health router
- [ ] Create `backend/app/api/v1/routers/health.py`:
  ```python
  from fastapi import APIRouter
  from fastapi.responses import JSONResponse
  from sqlalchemy import text
  from sqlalchemy.ext.asyncio import AsyncSession
  import redis.asyncio as aioredis
  from app.db.engine import engine
  from app.core.config import settings

  router = APIRouter(tags=["health"])

  async def check_db() -> bool:
      try:
          async with engine.connect() as conn:
              await conn.execute(text("SELECT 1"))
          return True
      except Exception:
          return False

  async def check_redis() -> bool:
      try:
          r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
          await r.ping()
          await r.aclose()
          return True
      except Exception:
          return False

  @router.get("/health")
  async def health_check():
      db_ok = await check_db()
      redis_ok = await check_redis()
      all_ok = db_ok and redis_ok
      payload = {
          "status": "ok" if all_ok else "degraded",
          "checks": {"db": db_ok, "redis": redis_ok},
      }
      return JSONResponse(content=payload, status_code=200 if all_ok else 503)
  ```
- [ ] Run: `pytest app/tests/unit/test_health.py -v` → **PASSED**
- [ ] Commit: `git commit -m "feat: add GET /api/v1/health endpoint with db + redis checks"`

---

## Phase 7 — FastAPI Application Assembly

### Task 7.1 — Write failing integration test for app startup
- [ ] Create `backend/app/tests/unit/test_main.py`:
  ```python
  import pytest
  from httpx import AsyncClient, ASGITransport

  @pytest.mark.asyncio
  async def test_openapi_schema_available():
      from app.main import app
      async with AsyncClient(
          transport=ASGITransport(app=app), base_url="http://test"
      ) as client:
          resp = await client.get("/openapi.json")
      assert resp.status_code == 200
      schema = resp.json()
      assert "/api/v1/health" in schema["paths"]
      assert "/api/v1/auth/login" in schema["paths"]
  ```
- [ ] Run: `pytest app/tests/unit/test_main.py -v` → **FAILED**

### Task 7.2 — Create `app/main.py`
- [ ] Create `backend/app/main.py`:
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  from app.api.v1.routers import health, auth

  app = FastAPI(
      title="FailureLogAnalyzer API",
      version="0.1.0",
      docs_url="/api/docs",
      openapi_url="/openapi.json",
  )

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  app.include_router(health.router, prefix="/api/v1")
  app.include_router(auth.router, prefix="/api/v1")
  ```
- [ ] Create `backend/app/api/v1/routers/__init__.py` (empty)
- [ ] Create `backend/app/api/__init__.py` (empty)
- [ ] Create `backend/app/api/v1/__init__.py` (empty)
- [ ] Create `backend/app/__init__.py` (empty)
- [ ] Run: `pytest app/tests/unit/test_main.py -v` → **PASSED**
- [ ] Run full unit suite: `cd backend && pytest app/tests/unit/ -v`
- [ ] Expected: all unit tests pass
- [ ] Commit: `git commit -m "feat: assemble FastAPI app with health + auth routers"`

### Task 7.3 — Create `pytest.ini` and `conftest.py`
- [ ] Create `backend/pytest.ini`:
  ```ini
  [pytest]
  asyncio_mode = auto
  testpaths = app/tests
  ```
- [ ] Create `backend/app/tests/__init__.py` (empty)
- [ ] Create `backend/app/tests/unit/__init__.py` (empty)
- [ ] Create `backend/app/tests/integration/__init__.py` (empty)
- [ ] Create `backend/app/tests/conftest.py`:
  ```python
  import os
  import pytest
  # Set test env vars before any app import
  os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://fla:fla@localhost/fla_test")
  os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-characters-long")
  os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
  ```
- [ ] Run: `pytest -v --tb=short` → all tests pass

---

## Phase 8 — Docker Compose

### Task 8.1 — Write failing smoke test for docker-compose config validity
- [ ] Create `backend/app/tests/unit/test_docker_compose.py`:
  ```python
  import subprocess
  import pytest

  def test_docker_compose_config_is_valid():
      """docker compose config validates YAML syntax and image references."""
      result = subprocess.run(
          ["docker", "compose", "-f", "docker-compose.yml", "config", "--quiet"],
          capture_output=True, text=True, cwd="."  # repo root
      )
      assert result.returncode == 0, (
          f"docker compose config failed:\n{result.stderr}"
      )
  ```
- [ ] Run: `pytest app/tests/unit/test_docker_compose.py -v` → **FAILED** (no `docker-compose.yml`)

### Task 8.2 — Create `docker-compose.yml` at repo root
- [ ] Create `docker-compose.yml` at `/Users/deng/开发/FailureLogAnalyzer/docker-compose.yml`:
  ```yaml
  services:
    postgres:
      image: postgres:15-alpine
      environment:
        POSTGRES_USER: fla
        POSTGRES_PASSWORD: fla
        POSTGRES_DB: fla
      ports:
        - "5432:5432"
      volumes:
        - postgres_data:/var/lib/postgresql/data
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U fla"]
        interval: 5s
        timeout: 5s
        retries: 5

    redis:
      image: redis:7-alpine
      ports:
        - "6379:6379"
      healthcheck:
        test: ["CMD", "redis-cli", "ping"]
        interval: 5s
        timeout: 3s
        retries: 5

    api:
      build:
        context: ./backend
        dockerfile: Dockerfile
      ports:
        - "8000:8000"
      environment:
        DATABASE_URL: postgresql+asyncpg://fla:fla@postgres:5432/fla
        REDIS_URL: redis://redis:6379/0
        SECRET_KEY: ${SECRET_KEY:-change-me-in-production-use-32-chars-min}
        ACCESS_TOKEN_EXPIRE_MINUTES: 60
        ENVIRONMENT: development
      depends_on:
        postgres:
          condition: service_healthy
        redis:
          condition: service_healthy
      volumes:
        - ./backend:/app
      command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  volumes:
    postgres_data:
  ```

### Task 8.3 — Create `backend/Dockerfile`
- [ ] Create `backend/Dockerfile`:
  ```dockerfile
  FROM python:3.11-slim

  WORKDIR /app

  COPY pyproject.toml .
  RUN pip install --no-cache-dir -e ".[dev]"

  COPY . .

  EXPOSE 8000
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- [ ] Run: `pytest app/tests/unit/test_docker_compose.py -v` → **PASSED** (requires Docker installed)
- [ ] Commit: `git commit -m "feat: add Docker Compose with api/postgres/redis services"`

### Task 8.4 — End-to-end Docker smoke test
- [ ] Start services: `docker compose up --build -d`
- [ ] Wait for healthy: `docker compose ps` — all services show `healthy` or `running`
- [ ] Apply migrations: `docker compose exec api alembic upgrade head`
- [ ] Expected output: `Running upgrade -> <hash>, initial_schema`
- [ ] Hit health endpoint: `curl -s http://localhost:8000/api/v1/health | python3 -m json.tool`
- [ ] Expected:
  ```json
  {
    "status": "ok",
    "checks": {
      "db": true,
      "redis": true
    }
  }
  ```
- [ ] Stop services: `docker compose down`
- [ ] Commit: `git commit -m "chore: verify docker compose e2e health check passes"`

---

## Phase 9 — Structured Logging

### Task 9.1 — Write failing test for logger setup
- [ ] Create `backend/app/tests/unit/test_logging.py`:
  ```python
  import logging
  from app.core.logging import configure_logging, get_logger

  def test_configure_logging_does_not_raise():
      configure_logging()  # Should complete without error

  def test_get_logger_returns_bound_logger():
      configure_logging()
      logger = get_logger("test.module")
      assert logger is not None
      # Should be able to log without raising
      logger.info("test message", key="value")
  ```
- [ ] Run: `pytest app/tests/unit/test_logging.py -v` → **FAILED**

### Task 9.2 — Implement `app/core/logging.py`
- [ ] Create `backend/app/core/logging.py`:
  ```python
  import logging
  import structlog

  def configure_logging() -> None:
      structlog.configure(
          processors=[
              structlog.contextvars.merge_contextvars,
              structlog.processors.add_log_level,
              structlog.processors.TimeStamper(fmt="iso"),
              structlog.dev.ConsoleRenderer() if True else structlog.processors.JSONRenderer(),
          ],
          wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
          context_class=dict,
          logger_factory=structlog.PrintLoggerFactory(),
      )

  def get_logger(name: str):
      return structlog.get_logger(name)
  ```
- [ ] Add `configure_logging()` call to `app/main.py` lifespan/startup.
- [ ] Run: `pytest app/tests/unit/test_logging.py -v` → **PASSED**
- [ ] Commit: `git commit -m "feat: add structlog structured logging setup"`

---

## Phase 10 — Final Integration Check

### Task 10.1 — Run complete test suite
- [ ] `cd backend && pytest -v --cov=app --cov-report=term-missing`
- [ ] Expected: all unit tests pass; integration tests skipped (no `TEST_DATABASE_URL`)
- [ ] Coverage should be > 80% for `app/core/` and `app/api/v1/routers/`

### Task 10.2 — Verify Alembic history is clean
- [ ] `cd backend && alembic history --verbose`
- [ ] Expected: one revision listed — `initial_schema`
- [ ] `alembic current` (against running DB): should show `head`

### Task 10.3 — Document startup commands in `README.md`
- [ ] Create `backend/README.md`:
  ```markdown
  # FailureLogAnalyzer — Backend

  ## Quick Start (Docker)

  ```bash
  cp backend/.env.example backend/.env
  # Edit SECRET_KEY in .env
  docker compose up --build -d
  docker compose exec api alembic upgrade head
  # Health check
  curl http://localhost:8000/api/v1/health
  # API docs
  open http://localhost:8000/api/docs
  ```

  ## Local Dev (without Docker)

  ```bash
  cd backend
  python3.11 -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"
  cp .env.example .env  # edit DATABASE_URL / REDIS_URL
  alembic upgrade head
  uvicorn app.main:app --reload
  ```

  ## Tests

  ```bash
  pytest -v                          # unit tests only
  TEST_DATABASE_URL=... pytest -v    # include integration tests
  ```
  ```
- [ ] Commit: `git commit -m "docs: add backend README with quick start instructions"`

---

## Final File Structure

After all tasks complete, the repo should look like:

```
FailureLogAnalyzer/
├── docker-compose.yml
├── .gitignore
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-03-18-failure-log-analyzer-design.md
│       └── plans/
│           └── 2026-03-19-01-backend-infrastructure.md
└── backend/
    ├── Dockerfile
    ├── pyproject.toml
    ├── pytest.ini
    ├── alembic.ini
    ├── .env.example
    ├── README.md
    └── app/
        ├── __init__.py
        ├── main.py
        ├── api/
        │   ├── __init__.py
        │   └── v1/
        │       ├── __init__.py
        │       ├── deps.py
        │       └── routers/
        │           ├── __init__.py
        │           ├── auth.py
        │           ├── health.py
        │           └── users.py
        ├── core/
        │   ├── auth.py
        │   ├── config.py
        │   └── logging.py
        ├── schemas/
        │   └── user.py
        ├── db/
        │   ├── engine.py
        │   ├── session.py
        │   ├── migrations/
        │   │   ├── env.py
        │   │   ├── script.py.mako
        │   │   └── versions/
        │   │       └── <hash>_initial_schema.py
        │   └── models/
        │       ├── __init__.py
        │       ├── base.py
        │       ├── enums.py
        │       ├── user.py
        │       ├── eval_session.py
        │       ├── eval_record.py
        │       ├── analysis_result.py
        │       ├── error_tag.py
        │       ├── analysis_rule.py
        │       ├── analysis_strategy.py
        │       └── prompt_template.py
        └── tests/
            ├── __init__.py
            ├── conftest.py
            ├── unit/
            │   ├── __init__.py
            │   ├── test_settings.py
            │   ├── test_database.py
            │   ├── test_models.py
            │   ├── test_auth.py
            │   ├── test_auth_deps.py
            │   ├── test_auth_router.py
            │   ├── test_users_router.py
            │   ├── test_health.py
            │   ├── test_main.py
            │   ├── test_logging.py
            │   └── test_docker_compose.py
            └── integration/
                ├── __init__.py
                └── test_migrations.py
```

---

## Handoff Contract for Plans 2 and 3

Plan 2 (Ingestion + Rule Engine) and Plan 3 (LLM Judge + Agent Orchestration) can rely on:

- **Database session**: `from app.db.session import get_db` — async SQLAlchemy session
- **All ORM models**: `from app.db.models import EvalSession, EvalRecord, AnalysisResult, ErrorTag, AnalysisRule, AnalysisStrategy, PromptTemplate`
- **Auth dependency**: `from app.api.v1.deps import get_current_user, require_role`
- **User management**: `GET/POST /api/v1/users`, `GET/PATCH /api/v1/users/{id}` — Admin-only CRUD for user accounts and role assignment
- **User schemas**: `from app.schemas.user import UserCreate, UserUpdate, UserResponse`
- **Settings**: `from app.core.config import settings` — DATABASE_URL, REDIS_URL, SECRET_KEY
- **Logger**: `from app.core.logging import get_logger`
- **Router registration**: add new routers via `app.include_router(...)` in `app/main.py`
- **Docker Compose**: `docker compose up` brings up api + postgres + redis; run migrations with `docker compose exec api alembic upgrade head`
