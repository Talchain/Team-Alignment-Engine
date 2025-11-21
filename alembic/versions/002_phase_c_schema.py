"""Phase C schema: Intelligent Assistance & Learning

Revision ID: 002
Revises: 001
Create Date: 2025-01-15 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Phase C tables and columns."""

    # Update sessions table for multi-round deliberation
    op.add_column(
        'sessions',
        sa.Column('parent_session_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'sessions',
        sa.Column('reopened_from_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'sessions',
        sa.Column('chain_depth', sa.Integer(), nullable=False, server_default='0')
    )
    op.create_index('ix_sessions_parent_session_id', 'sessions', ['parent_session_id'])

    # Update options table for AI-powered option creation
    op.add_column(
        'options',
        sa.Column('ai_generation_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        'options',
        sa.Column('synthesis_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        'options',
        sa.Column('tuning_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )

    # Create assumption_validations table
    op.create_table(
        'assumption_validations',
        sa.Column('validation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assumption_id', sa.String(200), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('validation_method', sa.String(100), nullable=False),
        sa.Column('validation_result', sa.String(50), nullable=False),
        sa.Column('validation_notes', sa.String(2000), nullable=False),
        sa.Column('validated_at', sa.DateTime(), nullable=False),
        sa.Column('validated_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('updated_assumption', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('validation_id')
    )
    op.create_index('ix_assumption_validations_assumption_id', 'assumption_validations', ['assumption_id'])
    op.create_index('ix_assumption_validations_session_id', 'assumption_validations', ['session_id'])

    # Create decision_retrospectives table
    op.create_table(
        'decision_retrospectives',
        sa.Column('retrospective_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('brief_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actual_outcomes', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('outcome_comparison', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('assumption_results', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('assumption_analysis', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('narrative', sa.String(5000), nullable=False),
        sa.Column('lessons_learned', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('recorded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('retrospective_id')
    )
    op.create_index('ix_decision_retrospectives_session_id', 'decision_retrospectives', ['session_id'])
    op.create_index('ix_decision_retrospectives_brief_id', 'decision_retrospectives', ['brief_id'])


def downgrade() -> None:
    """Remove Phase C tables and columns."""

    # Drop tables
    op.drop_index('ix_decision_retrospectives_brief_id', table_name='decision_retrospectives')
    op.drop_index('ix_decision_retrospectives_session_id', table_name='decision_retrospectives')
    op.drop_table('decision_retrospectives')

    op.drop_index('ix_assumption_validations_session_id', table_name='assumption_validations')
    op.drop_index('ix_assumption_validations_assumption_id', table_name='assumption_validations')
    op.drop_table('assumption_validations')

    # Remove columns from options
    op.drop_column('options', 'tuning_metadata')
    op.drop_column('options', 'synthesis_metadata')
    op.drop_column('options', 'ai_generation_metadata')

    # Remove columns from sessions
    op.drop_index('ix_sessions_parent_session_id', table_name='sessions')
    op.drop_column('sessions', 'chain_depth')
    op.drop_column('sessions', 'reopened_from_id')
    op.drop_column('sessions', 'parent_session_id')
