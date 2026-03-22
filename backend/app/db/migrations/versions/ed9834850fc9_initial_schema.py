"""initial_schema

Revision ID: ed9834850fc9
Revises:
Create Date: 2026-03-19 16:38:25.535977

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ed9834850fc9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types first
    user_role = postgresql.ENUM('admin', 'analyst', 'viewer', name='user_role', create_type=True)
    analysis_type = postgresql.ENUM('rule', 'llm', 'manual', name='analysis_type', create_type=True)
    severity_level = postgresql.ENUM('high', 'medium', 'low', name='severity_level', create_type=True)
    tag_source = postgresql.ENUM('rule', 'llm', name='tag_source', create_type=True)
    strategy_type = postgresql.ENUM('full', 'fallback', 'sample', 'manual', name='strategy_type', create_type=True)

    user_role.create(op.get_bind(), checkfirst=True)
    analysis_type.create(op.get_bind(), checkfirst=True)
    severity_level.create(op.get_bind(), checkfirst=True)
    tag_source.create(op.get_bind(), checkfirst=True)
    strategy_type.create(op.get_bind(), checkfirst=True)

    # users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(64), nullable=False, unique=True),
        sa.Column('email', sa.String(256), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'analyst', 'viewer', name='user_role', create_type=False), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # prompt_templates (must be before analysis_strategies due to FK)
    op.create_table(
        'prompt_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('benchmark', sa.String(64), nullable=True),
        sa.Column('template', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # eval_sessions
    op.create_table(
        'eval_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('model', sa.String(128), nullable=False),
        sa.Column('model_version', sa.String(64), nullable=False),
        sa.Column('benchmark', sa.String(64), nullable=False),
        sa.Column('dataset_name', sa.String(256), nullable=True),
        sa.Column('total_count', sa.Integer(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # eval_records
    op.create_table(
        'eval_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('eval_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('benchmark', sa.String(64), nullable=False),
        sa.Column('model_version', sa.String(64), nullable=True),
        sa.Column('task_category', sa.String(256), nullable=True),
        sa.Column('question_id', sa.String(256), nullable=True),
        sa.Column('question', sa.Text(), nullable=True),
        sa.Column('expected_answer', sa.Text(), nullable=True),
        sa.Column('model_answer', sa.Text(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('extracted_code', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('raw_json', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_eval_records_benchmark_correct', 'eval_records', ['benchmark', 'is_correct'])
    op.create_index('ix_eval_records_session_correct', 'eval_records', ['session_id', 'is_correct'])
    op.create_index('ix_eval_records_task_category', 'eval_records', ['task_category'])
    op.create_index('ix_eval_records_model_version_benchmark', 'eval_records', ['model_version', 'benchmark'])
    op.create_index('ix_eval_records_question_model_version', 'eval_records', ['question_id', 'model_version'])

    # analysis_results
    op.create_table(
        'analysis_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('eval_records.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_type', postgresql.ENUM('rule', 'llm', 'manual', name='analysis_type', create_type=False), nullable=False),
        sa.Column('error_types', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('severity', postgresql.ENUM('high', 'medium', 'low', name='severity_level', create_type=False), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('suggestion', sa.Text(), nullable=True),
        sa.Column('llm_model', sa.String(128), nullable=True),
        sa.Column('llm_cost', sa.Float(), nullable=True),
        sa.Column('prompt_template', sa.String(256), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(), nullable=True),
        sa.Column('unmatched_tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # error_tags
    op.create_table(
        'error_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('eval_records.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_result_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_results.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tag_path', sa.String(512), nullable=False),
        sa.Column('tag_level', sa.Integer(), nullable=False),
        sa.Column('source', postgresql.ENUM('rule', 'llm', name='tag_source', create_type=False), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # analysis_rules
    op.create_table(
        'analysis_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('field', sa.String(128), nullable=False),
        sa.Column('condition', postgresql.JSONB(), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # analysis_strategies
    op.create_table(
        'analysis_strategies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('strategy_type', postgresql.ENUM('full', 'fallback', 'sample', 'manual', name='strategy_type', create_type=False), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('llm_provider', sa.String(64), nullable=True),
        sa.Column('llm_model', sa.String(128), nullable=True),
        sa.Column('prompt_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('max_concurrent', sa.Integer(), nullable=True),
        sa.Column('daily_budget', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('analysis_strategies')
    op.drop_table('analysis_rules')
    op.drop_table('error_tags')
    op.drop_table('analysis_results')
    op.drop_index('ix_eval_records_question_model_version', table_name='eval_records')
    op.drop_index('ix_eval_records_model_version_benchmark', table_name='eval_records')
    op.drop_index('ix_eval_records_task_category', table_name='eval_records')
    op.drop_index('ix_eval_records_session_correct', table_name='eval_records')
    op.drop_index('ix_eval_records_benchmark_correct', table_name='eval_records')
    op.drop_table('eval_records')
    op.drop_table('eval_sessions')
    op.drop_table('prompt_templates')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS strategy_type')
    op.execute('DROP TYPE IF EXISTS tag_source')
    op.execute('DROP TYPE IF EXISTS severity_level')
    op.execute('DROP TYPE IF EXISTS analysis_type')
    op.execute('DROP TYPE IF EXISTS user_role')
