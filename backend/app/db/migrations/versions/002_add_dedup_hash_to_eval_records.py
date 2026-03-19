"""add dedup_hash to eval_records

Revision ID: 002_add_dedup_hash
Revises: ed9834850fc9
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_dedup_hash"
down_revision = "ed9834850fc9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("eval_records", sa.Column("dedup_hash", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_eval_records_dedup_hash", "eval_records", ["dedup_hash"])
    op.create_index("ix_eval_records_dedup_hash", "eval_records", ["dedup_hash"])


def downgrade():
    op.drop_index("ix_eval_records_dedup_hash", table_name="eval_records")
    op.drop_constraint("uq_eval_records_dedup_hash", "eval_records")
    op.drop_column("eval_records", "dedup_hash")
