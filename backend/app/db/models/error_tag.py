import uuid
from sqlalchemy import String, Integer, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import TagSource

class ErrorTag(Base, TimestampMixin):
    __tablename__ = "error_tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_records.id", ondelete="CASCADE"), nullable=False
    )
    analysis_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_results.id", ondelete="SET NULL"), nullable=True
    )
    tag_path: Mapped[str] = mapped_column(String(512), nullable=False)
    tag_level: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[TagSource] = mapped_column(SAEnum(TagSource, name="tag_source"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    record: Mapped["EvalRecord"] = relationship(back_populates="error_tags")
    analysis_result: Mapped["AnalysisResult"] = relationship(back_populates="error_tags")
