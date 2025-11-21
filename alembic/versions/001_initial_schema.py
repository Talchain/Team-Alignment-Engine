"""Initial schema for Team Alignment Engine

Revision ID: 001
Revises:
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables."""

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('decision_topic', sa.String(500), nullable=False),
        sa.Column('decision_context', sa.String(2000), nullable=False),
        sa.Column('decision_type', sa.String(50), nullable=False),
        sa.Column('alignment_mode', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('stakeholders', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('shared_ground', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('disagreement_map', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('scenario_model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scenario_parameter_deltas', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('selected_option_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index('ix_sessions_team_id', 'sessions', ['team_id'])

    # Create profiles table
    op.create_table(
        'profiles',
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(100), nullable=False),
        sa.Column('stakeholder_role', sa.String(50), nullable=False),
        sa.Column('desired_outcome', sa.String(1000), nullable=False),
        sa.Column('key_concerns', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('preferred_option', sa.String(1000), nullable=True),
        sa.Column('goal_weights', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('risk_tolerance', sa.String(50), nullable=False),
        sa.Column('time_horizon', sa.String(50), nullable=False),
        sa.Column('must_have_constraints', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('red_lines', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('extraction_confidence', sa.Float(), nullable=False),
        sa.Column('extraction_source', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('profile_id')
    )
    op.create_index('ix_profiles_session_id', 'profiles', ['session_id'])
    op.create_index('ix_profiles_user_id', 'profiles', ['user_id'])

    # Create options table
    op.create_table(
        'options',
        sa.Column('option_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('proposed_by', sa.String(100), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.String(2000), nullable=False),
        sa.Column('expected_outcome', sa.String(1000), nullable=False),
        sa.Column('causal_rationale', sa.String(2000), nullable=False),
        sa.Column('addresses_goals', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('trade_offs', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('key_assumptions', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('scenario_link', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_baseline', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('option_id')
    )
    op.create_index('ix_options_session_id', 'options', ['session_id'])

    # Create validations table
    op.create_table(
        'validations',
        sa.Column('validation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('option_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_identifiable', sa.Boolean(), nullable=False),
        sa.Column('validation_status', sa.String(50), nullable=False),
        sa.Column('data_sufficiency', sa.String(50), nullable=False),
        sa.Column('predicted_outcomes', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('key_assumptions', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('warnings', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('quality_concerns', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('sensitivity_factors', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('isl_response', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('isl_request_id', sa.String(100), nullable=True),
        sa.Column('validated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('validation_id')
    )
    op.create_index('ix_validations_option_id', 'validations', ['option_id'])

    # Create fits table
    op.create_table(
        'fits',
        sa.Column('fit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('option_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stakeholder_fits', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('overall_alignment', sa.Float(), nullable=False),
        sa.Column('consensus_level', sa.String(50), nullable=False),
        sa.Column('calculated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('fit_id')
    )
    op.create_index('ix_fits_option_id', 'fits', ['option_id'])

    # Create concerns table
    op.create_table(
        'concerns',
        sa.Column('concern_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('option_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('raised_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('concern_text', sa.String(1000), nullable=False),
        sa.Column('concern_type', sa.String(50), nullable=False),
        sa.Column('assumption_id_tested', sa.String(100), nullable=True),
        sa.Column('sensitivity_tested', sa.Boolean(), nullable=False),
        sa.Column('causal_validation', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('resolution', sa.String(2000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('concern_id')
    )
    op.create_index('ix_concerns_option_id', 'concerns', ['option_id'])

    # Create decision_briefs table
    op.create_table(
        'decision_briefs',
        sa.Column('brief_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chosen_option', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('decision_rationale', sa.String(2000), nullable=False),
        sa.Column('stakeholder_support', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('consensus_strength', sa.Float(), nullable=False),
        sa.Column('validated_outcomes', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('accepted_assumptions', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('monitored_risks', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('minority_concerns_raised', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('minority_concerns_addressed', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('review_date', sa.DateTime(), nullable=False),
        sa.Column('success_criteria', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('monitoring_plan', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('scenario_model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scenario_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('decision_date', sa.DateTime(), nullable=False),
        sa.Column('participants', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('exported_at', sa.DateTime(), nullable=True),
        sa.Column('decision_quality_rating', sa.Integer(), nullable=True),
        sa.Column('post_decision_notes', sa.String(2000), nullable=True),
        sa.PrimaryKeyConstraint('brief_id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index('ix_decision_briefs_session_id', 'decision_briefs', ['session_id'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('decision_briefs')
    op.drop_table('concerns')
    op.drop_table('fits')
    op.drop_table('validations')
    op.drop_table('options')
    op.drop_table('profiles')
    op.drop_table('sessions')
