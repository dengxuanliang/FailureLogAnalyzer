"""add provider secrets table

Revision ID: 004_add_provider_secrets
Revises: 003_add_reports_table
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004_add_provider_secrets"
down_revision = "003_add_reports_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "provider_secrets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column("secret_mask", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "name", name="uq_provider_secret_provider_name"),
    )
    op.create_index(
        "ix_provider_secrets_provider_created_at",
        "provider_secrets",
        ["provider", "created_at"],
    )


def downgrade():
    op.drop_index("ix_provider_secrets_provider_created_at", table_name="provider_secrets")
    op.drop_table("provider_secrets")
