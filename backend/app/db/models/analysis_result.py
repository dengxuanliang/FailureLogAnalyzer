import uuid
from sqlalchemy import String, Float, Text, ForeignKey, Enum as SAEnum, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import AnalysisType, SeverityLevel

class AnalysisResult(Base, TimestampMixin):
    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_records.id", ondelete="CASCADE"), nullable=False
    )
    analysis_type: Mapped[AnalysisType] = mapped_column(SAEnum(AnalysisType, name="analysis_type"), nullable=False)
    error_types: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[SeverityLevel | None] = mapped_column(SAEnum(SeverityLevel, name="severity_level"), nullable=True)
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
