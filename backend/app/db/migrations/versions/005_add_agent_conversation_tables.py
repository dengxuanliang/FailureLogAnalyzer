"""add agent conversation tables

Revision ID: 005_add_agent_conversations
Revises: 004_add_provider_secrets
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005_add_agent_conversations"
down_revision = "004_add_provider_secrets"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_conversations",
        sa.Column("conversation_id", sa.String(length=64), primary_key=True),
        sa.Column("owner_subject", sa.String(length=128), nullable=True),
        sa.Column("intent", sa.String(length=64), nullable=False, server_default="query"),
        sa.Column("current_step", sa.String(length=64), nullable=False, server_default="start"),
        sa.Column("last_message", sa.Text(), nullable=True),
        sa.Column("needs_human_input", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "target_session_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "target_filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_agent_conversations_owner_subject",
        "agent_conversations",
        ["owner_subject"],
    )

    op.create_table(
        "agent_conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(length=64),
            sa.ForeignKey("agent_conversations.conversation_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("action", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_agent_conversation_messages_conversation_id",
        "agent_conversation_messages",
        ["conversation_id"],
    )
    op.create_unique_constraint(
        "uq_agent_conversation_messages_sequence",
        "agent_conversation_messages",
        ["conversation_id", "sequence_no"],
    )


def downgrade():
    op.drop_constraint("uq_agent_conversation_messages_sequence", "agent_conversation_messages")
    op.drop_index("ix_agent_conversation_messages_conversation_id", table_name="agent_conversation_messages")
    op.drop_table("agent_conversation_messages")
    op.drop_index("ix_agent_conversations_owner_subject", table_name="agent_conversations")
    op.drop_table("agent_conversations")
