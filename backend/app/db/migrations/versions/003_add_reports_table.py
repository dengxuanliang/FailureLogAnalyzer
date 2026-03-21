"""add reports table

Revision ID: 003_add_reports_table
Revises: 002_add_dedup_hash
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "003_add_reports_table"
down_revision = "002_add_dedup_hash"
branch_labels = None
depends_on = None


def upgrade():
    report_type_enum = postgresql.ENUM(
        "summary",
        "comparison",
        "cross_benchmark",
        "custom",
        name="report_type_enum",
        create_type=True,
    )
    report_status_enum = postgresql.ENUM(
        "pending",
        "generating",
        "done",
        "failed",
        name="report_status_enum",
        create_type=True,
    )
    report_type_enum.create(op.get_bind(), checkfirst=True)
    report_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column(
            "report_type",
            sa.Enum("summary", "comparison", "cross_benchmark", "custom", name="report_type_enum"),
            nullable=False,
            server_default="summary",
        ),
        sa.Column("session_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("benchmark", sa.String(length=255), nullable=True),
        sa.Column("model_version", sa.String(length=255), nullable=True),
        sa.Column("time_range_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_range_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "status",
            sa.Enum("pending", "generating", "done", "failed", name="report_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_table("reports")
    op.execute("DROP TYPE IF EXISTS report_status_enum")
    op.execute("DROP TYPE IF EXISTS report_type_enum")
