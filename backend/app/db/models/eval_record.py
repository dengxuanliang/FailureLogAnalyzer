import uuid
from sqlalchemy import String, Boolean, Float, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import Base, TimestampMixin

class EvalRecord(Base, TimestampMixin):
    __tablename__ = "eval_records"
    __table_args__ = (
        Index("ix_eval_records_benchmark_correct", "benchmark", "is_correct"),
        Index("ix_eval_records_session_correct", "session_id", "is_correct"),
        Index("ix_eval_records_task_category", "task_category"),
        Index("ix_eval_records_model_version_benchmark", "model_version", "benchmark"),
        Index("ix_eval_records_question_model_version", "question_id", "model_version"),
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
    dedup_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)

    session: Mapped["EvalSession"] = relationship(back_populates="records")
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(back_populates="record")
    error_tags: Mapped[list["ErrorTag"]] = relationship(back_populates="record")
