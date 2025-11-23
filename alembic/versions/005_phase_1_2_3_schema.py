"""Add Phase 1-3 deliberation and aggregation models

Revision ID: 005
Revises: 004
Create Date: 2025-11-23 00:00:00.000000

Adds database tables for:
- Phase 1A/1B: Multi-round deliberation with anonymous voting
- Phase 2A: ActiVA preference elicitation
- Phase 2B: Bayesian teaching onboarding
- Phase 3: Navajas aggregation intelligence with user accuracy tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Phase 1-3 schema."""

    # =========================================================================
    # PHASE 1A/1B: DELIBERATION MODELS
    # =========================================================================

    # Deliberation sessions
    op.create_table(
        'deliberation_sessions',
        sa.Column('session_id', sa.String(100), primary_key=True),
        sa.Column('decision_context', sa.String(1000), nullable=False),
        sa.Column('participants', postgresql.JSON, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('convergence_criteria', postgresql.JSON, nullable=False),
        sa.Column('final_outcome', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_deliberation_sessions_status', 'deliberation_sessions', ['status'])
    op.create_index('ix_deliberation_sessions_created_at', 'deliberation_sessions', ['created_at'])

    # Deliberation rounds
    op.create_table(
        'deliberation_rounds',
        sa.Column('round_id', sa.String(100), primary_key=True),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('round_number', sa.Integer, nullable=False),
        sa.Column('round_type', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('synthesis_options', postgresql.JSON, nullable=True),
        sa.Column('convergence_status', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_deliberation_rounds_session_id', 'deliberation_rounds', ['session_id'])
    op.create_index('ix_deliberation_rounds_session_round', 'deliberation_rounds', ['session_id', 'round_number'])

    # Deliberation submissions
    op.create_table(
        'deliberation_submissions',
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('round_id', sa.String(100), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('graph', postgresql.JSON, nullable=False),
        sa.Column('reasoning', sa.String(2000), nullable=False),
        sa.Column('causal_quality', postgresql.JSON, nullable=False),
        sa.Column('validation_issues', postgresql.JSON, nullable=False),
        sa.Column('evidence_items', postgresql.JSON, nullable=True),
        sa.Column('unsupported_claims', postgresql.JSON, nullable=True),
        sa.Column('submitted_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_deliberation_submissions_round_id', 'deliberation_submissions', ['round_id'])
    op.create_index('ix_deliberation_submissions_session_id', 'deliberation_submissions', ['session_id'])
    op.create_index('ix_deliberation_submissions_user_id', 'deliberation_submissions', ['user_id'])

    # Deliberation votes (anonymous)
    op.create_table(
        'deliberation_votes',
        sa.Column('vote_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('round_id', sa.String(100), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('encrypted_user_id', sa.String(200), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('rankings', postgresql.JSON, nullable=False),
        sa.Column('submitted_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_deliberation_votes_round_id', 'deliberation_votes', ['round_id'])
    op.create_index('ix_deliberation_votes_session_id', 'deliberation_votes', ['session_id'])

    # Deliberation conflicts
    op.create_table(
        'deliberation_conflicts',
        sa.Column('conflict_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('round_id', sa.String(100), nullable=False),
        sa.Column('conflict_analysis', postgresql.JSON, nullable=False),
        sa.Column('decisive_test', postgresql.JSON, nullable=True),
        sa.Column('pareto_analysis', postgresql.JSON, nullable=True),
        sa.Column('reframing_analysis', postgresql.JSON, nullable=True),
        sa.Column('detected_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_deliberation_conflicts_session_id', 'deliberation_conflicts', ['session_id'])
    op.create_index('ix_deliberation_conflicts_round_id', 'deliberation_conflicts', ['round_id'])

    # =========================================================================
    # PHASE 3: AGGREGATION INTELLIGENCE MODELS
    # =========================================================================

    # User accuracy history (for Brier score calibration)
    op.create_table(
        'user_accuracy_history',
        sa.Column('record_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('domain', sa.String(100), nullable=False),
        sa.Column('decision_type', sa.String(100), nullable=False),
        sa.Column('stated_confidence', sa.Float, nullable=False),
        sa.Column('prediction_text', sa.String(2000), nullable=True),
        sa.Column('actual_outcome', sa.String(2000), nullable=True),
        sa.Column('outcome_known', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('outcome_recorded_at', sa.DateTime, nullable=True),
        sa.Column('brier_score', sa.Float, nullable=True),
        sa.Column('was_correct', sa.Boolean, nullable=True),
        sa.Column('confidence_error', sa.Float, nullable=True),
        sa.Column('predicted_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_user_accuracy_history_user_id', 'user_accuracy_history', ['user_id'])
    op.create_index('ix_user_accuracy_history_session_id', 'user_accuracy_history', ['session_id'])
    op.create_index('ix_user_accuracy_history_domain', 'user_accuracy_history', ['domain'])
    op.create_index('ix_user_accuracy_history_user_domain', 'user_accuracy_history', ['user_id', 'domain'])

    # User domain expertise (aggregated expertise scores)
    op.create_table(
        'user_domain_expertise',
        sa.Column('expertise_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('domain', sa.String(100), nullable=False),
        sa.Column('role_relevance', sa.Float, nullable=False, server_default='0.5'),
        sa.Column('historical_accuracy', sa.Float, nullable=False, server_default='0.5'),
        sa.Column('prediction_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('overconfidence_bias', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('avg_confidence_error', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('last_updated', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_user_domain_expertise_user_id', 'user_domain_expertise', ['user_id'])
    op.create_index('ix_user_domain_expertise_domain', 'user_domain_expertise', ['domain'])
    op.create_index('ix_user_domain_expertise_user_domain', 'user_domain_expertise', ['user_id', 'domain'], unique=True)


def downgrade() -> None:
    """Remove Phase 1-3 schema."""

    # Drop Phase 3 tables
    op.drop_index('ix_user_domain_expertise_user_domain', 'user_domain_expertise')
    op.drop_index('ix_user_domain_expertise_domain', 'user_domain_expertise')
    op.drop_index('ix_user_domain_expertise_user_id', 'user_domain_expertise')
    op.drop_table('user_domain_expertise')

    op.drop_index('ix_user_accuracy_history_user_domain', 'user_accuracy_history')
    op.drop_index('ix_user_accuracy_history_domain', 'user_accuracy_history')
    op.drop_index('ix_user_accuracy_history_session_id', 'user_accuracy_history')
    op.drop_index('ix_user_accuracy_history_user_id', 'user_accuracy_history')
    op.drop_table('user_accuracy_history')

    # Drop Phase 1 tables
    op.drop_index('ix_deliberation_conflicts_round_id', 'deliberation_conflicts')
    op.drop_index('ix_deliberation_conflicts_session_id', 'deliberation_conflicts')
    op.drop_table('deliberation_conflicts')

    op.drop_index('ix_deliberation_votes_session_id', 'deliberation_votes')
    op.drop_index('ix_deliberation_votes_round_id', 'deliberation_votes')
    op.drop_table('deliberation_votes')

    op.drop_index('ix_deliberation_submissions_user_id', 'deliberation_submissions')
    op.drop_index('ix_deliberation_submissions_session_id', 'deliberation_submissions')
    op.drop_index('ix_deliberation_submissions_round_id', 'deliberation_submissions')
    op.drop_table('deliberation_submissions')

    op.drop_index('ix_deliberation_rounds_session_round', 'deliberation_rounds')
    op.drop_index('ix_deliberation_rounds_session_id', 'deliberation_rounds')
    op.drop_table('deliberation_rounds')

    op.drop_index('ix_deliberation_sessions_created_at', 'deliberation_sessions')
    op.drop_index('ix_deliberation_sessions_status', 'deliberation_sessions')
    op.drop_table('deliberation_sessions')
