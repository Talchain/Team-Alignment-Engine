"""Add performance indexes for common queries.

Revision ID: 007_performance_indexes
Revises: 006_phase_5_autonomous_learning
Create Date: 2025-01-31

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_performance_indexes'
down_revision = '006_phase_5_autonomous_learning'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for common query patterns."""

    # Composite indexes for deliberation queries
    # Improves: "Get all submissions for a round" queries
    op.create_index(
        'ix_deliberation_submissions_session_round',
        'deliberation_submissions',
        ['session_id', 'round_id'],
        unique=False
    )

    # Improves: "Get all votes for a round" queries
    op.create_index(
        'ix_deliberation_votes_session_round',
        'deliberation_votes',
        ['session_id', 'round_id'],
        unique=False
    )

    # Composite indexes for outcome measurements
    # Improves: "Get all measurements for an outcome by metric" queries
    op.create_index(
        'ix_outcome_measurements_outcome_metric',
        'outcome_measurements',
        ['outcome_id', 'metric'],
        unique=False
    )

    # Composite indexes for user accuracy tracking
    # Improves: "Get user accuracy for specific domain" queries
    op.create_index(
        'ix_user_accuracy_user_domain',
        'user_accuracy_history',
        ['user_id', 'domain'],
        unique=False
    )

    # Improves: "Get recent user predictions" queries
    op.create_index(
        'ix_user_accuracy_user_predicted',
        'user_accuracy_history',
        ['user_id', 'predicted_at'],
        unique=False
    )

    # Composite indexes for user domain expertise
    # Improves: "Lookup user expertise for domain" queries
    op.create_index(
        'ix_user_domain_expertise_user_domain',
        'user_domain_expertise',
        ['user_id', 'domain'],
        unique=True  # Each user has one expertise record per domain
    )

    # Index for cache cleanup queries
    # Improves: "Delete expired cache entries" queries
    op.create_index(
        'ix_pattern_analysis_cache_expires',
        'pattern_analysis_cache',
        ['expires_at'],
        unique=False
    )

    op.create_index(
        'ix_analytics_cache_expires',
        'analytics_cache',
        ['expires_at'],
        unique=False
    )

    # Index for conflict detection queries
    # Improves: "Find unresolved conflicts" queries
    op.create_index(
        'ix_detected_conflicts_severity_resolved',
        'detected_conflicts',
        ['severity', 'resolved_at'],
        unique=False
    )

    # Index for decision dependency queries
    # Improves: "Find blocking dependencies" queries
    op.create_index(
        'ix_decision_dependencies_source_resolved',
        'decision_dependencies',
        ['source_session_id', 'resolved_at'],
        unique=False
    )

    op.create_index(
        'ix_decision_dependencies_target_resolved',
        'decision_dependencies',
        ['target_session_id', 'resolved_at'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""

    # Drop indexes in reverse order
    op.drop_index('ix_decision_dependencies_target_resolved', table_name='decision_dependencies')
    op.drop_index('ix_decision_dependencies_source_resolved', table_name='decision_dependencies')
    op.drop_index('ix_detected_conflicts_severity_resolved', table_name='detected_conflicts')
    op.drop_index('ix_analytics_cache_expires', table_name='analytics_cache')
    op.drop_index('ix_pattern_analysis_cache_expires', table_name='pattern_analysis_cache')
    op.drop_index('ix_user_domain_expertise_user_domain', table_name='user_domain_expertise')
    op.drop_index('ix_user_accuracy_user_predicted', table_name='user_accuracy_history')
    op.drop_index('ix_user_accuracy_user_domain', table_name='user_accuracy_history')
    op.drop_index('ix_outcome_measurements_outcome_metric', table_name='outcome_measurements')
    op.drop_index('ix_deliberation_votes_session_round', table_name='deliberation_votes')
    op.drop_index('ix_deliberation_submissions_session_round', table_name='deliberation_submissions')
