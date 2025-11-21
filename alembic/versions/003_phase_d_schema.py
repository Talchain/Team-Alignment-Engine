"""Phase D schema: Organizational Intelligence

Revision ID: 003
Revises: 002
Create Date: 2025-01-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Phase D tables for organizational intelligence."""

    # D3: Decision Dependencies Table
    op.create_table(
        'decision_dependencies',
        sa.Column('dependency_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dependency_type', sa.String(50), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('dependency_id'),
        sa.ForeignKeyConstraint(['source_session_id'], ['sessions.session_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_session_id'], ['sessions.session_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_dependencies_source_session', 'decision_dependencies', ['source_session_id'])
    op.create_index('ix_dependencies_target_session', 'decision_dependencies', ['target_session_id'])
    op.create_index('ix_dependencies_resolved', 'decision_dependencies', ['resolved_at'])

    # D4: Pattern Analysis Cache Table (for performance)
    op.create_table(
        'pattern_analysis_cache',
        sa.Column('cache_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('decision_type', sa.String(100), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),  # success, failure, neutral
        sa.Column('sample_size', sa.Integer(), nullable=False),
        sa.Column('common_characteristics', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('avg_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('analysis_period_days', sa.Integer(), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('cache_id')
    )
    op.create_index('ix_pattern_cache_org_type', 'pattern_analysis_cache', ['organization_id', 'decision_type'])
    op.create_index('ix_pattern_cache_expires', 'pattern_analysis_cache', ['expires_at'])

    # D6: Coordination Groups Table
    op.create_table(
        'coordination_groups',
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.String(1000), nullable=False),
        sa.Column('session_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('group_id')
    )
    op.create_index('ix_coordination_groups_created', 'coordination_groups', ['created_at'])
    op.create_index('ix_coordination_groups_archived', 'coordination_groups', ['archived_at'])

    # D6: Conflict Detection Table
    op.create_table(
        'detected_conflicts',
        sa.Column('conflict_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conflict_type', sa.String(50), nullable=False),  # temporal, resource, dependency, scope
        sa.Column('session_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),  # high, medium, low
        sa.Column('description', sa.String(1000), nullable=False),
        sa.Column('resolution_suggestions', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_description', sa.String(1000), nullable=True),
        sa.PrimaryKeyConstraint('conflict_id')
    )
    op.create_index('ix_conflicts_type_severity', 'detected_conflicts', ['conflict_type', 'severity'])
    op.create_index('ix_conflicts_resolved', 'detected_conflicts', ['resolved_at'])
    op.create_index('ix_conflicts_detected', 'detected_conflicts', ['detected_at'])

    # D5: Analytics Cache Table (for trend analysis and benchmarks)
    op.create_table(
        'analytics_cache',
        sa.Column('cache_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),  # trend, benchmark
        sa.Column('metric_name', sa.String(100), nullable=True),
        sa.Column('decision_type', sa.String(100), nullable=True),
        sa.Column('result_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('cache_id')
    )
    op.create_index('ix_analytics_cache_org_type', 'analytics_cache', ['organization_id', 'analysis_type'])
    op.create_index('ix_analytics_cache_expires', 'analytics_cache', ['expires_at'])

    # Add organization_id to sessions table for Phase D filtering
    op.add_column(
        'sessions',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index('ix_sessions_organization_id', 'sessions', ['organization_id'])

    # Add quality and satisfaction ratings to retrospectives (for analytics)
    op.add_column(
        'decision_retrospectives',
        sa.Column('quality_rating', sa.Float(), nullable=True)  # 1-10 scale
    )
    op.add_column(
        'decision_retrospectives',
        sa.Column('satisfaction_rating', sa.Float(), nullable=True)  # 1-10 scale
    )
    op.add_column(
        'decision_retrospectives',
        sa.Column('would_repeat_decision', sa.Boolean(), nullable=True)
    )


def downgrade() -> None:
    """Remove Phase D tables and columns."""

    # Remove columns from retrospectives
    op.drop_column('decision_retrospectives', 'would_repeat_decision')
    op.drop_column('decision_retrospectives', 'satisfaction_rating')
    op.drop_column('decision_retrospectives', 'quality_rating')

    # Remove column from sessions
    op.drop_index('ix_sessions_organization_id', table_name='sessions')
    op.drop_column('sessions', 'organization_id')

    # Drop analytics cache table
    op.drop_index('ix_analytics_cache_expires', table_name='analytics_cache')
    op.drop_index('ix_analytics_cache_org_type', table_name='analytics_cache')
    op.drop_table('analytics_cache')

    # Drop conflicts table
    op.drop_index('ix_conflicts_detected', table_name='detected_conflicts')
    op.drop_index('ix_conflicts_resolved', table_name='detected_conflicts')
    op.drop_index('ix_conflicts_type_severity', table_name='detected_conflicts')
    op.drop_table('detected_conflicts')

    # Drop coordination groups table
    op.drop_index('ix_coordination_groups_archived', table_name='coordination_groups')
    op.drop_index('ix_coordination_groups_created', table_name='coordination_groups')
    op.drop_table('coordination_groups')

    # Drop pattern cache table
    op.drop_index('ix_pattern_cache_expires', table_name='pattern_analysis_cache')
    op.drop_index('ix_pattern_cache_org_type', table_name='pattern_analysis_cache')
    op.drop_table('pattern_analysis_cache')

    # Drop dependencies table
    op.drop_index('ix_dependencies_resolved', table_name='decision_dependencies')
    op.drop_index('ix_dependencies_target_session', table_name='decision_dependencies')
    op.drop_index('ix_dependencies_source_session', table_name='decision_dependencies')
    op.drop_table('decision_dependencies')
