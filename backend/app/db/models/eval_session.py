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
