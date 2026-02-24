"""Add Phase 5 autonomous learning tables

Revision ID: 006
Revises: 005
Create Date: 2025-11-23

Phase 5: Causal Modelling Agents & Learning
- decision_outcomes: Track predicted vs actual outcomes
- outcome_measurements: Granular outcome measurements

These tables enable:
- Historical learning from decision outcomes
- Pattern detection across decisions
- Graph refinement suggestions
- Autonomous improvement cycle
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Phase 5 autonomous learning schema."""

    # decision_outcomes table
    op.create_table(
        'decision_outcomes',
        sa.Column('outcome_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('decision', postgresql.JSON, nullable=False, comment='Selected option with decision graph and assumptions'),
        sa.Column('predicted_outcomes', postgresql.JSON, nullable=False, comment='Array of predicted metrics with confidence intervals'),
        sa.Column('actual_outcomes', postgresql.JSON, nullable=True, comment='Array of measured actual outcomes'),
        sa.Column('status', sa.String(20), nullable=False, server_default='predicted', comment='predicted | monitoring | measured | analyzed'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('measured_at', sa.DateTime, nullable=True),
    )

    # Indexes for decision_outcomes
    op.create_index('ix_decision_outcomes_session_id', 'decision_outcomes', ['session_id'])
    op.create_index('ix_decision_outcomes_status', 'decision_outcomes', ['status'])
    op.create_index('ix_decision_outcomes_created_at', 'decision_outcomes', ['created_at'])

    # outcome_measurements table
    op.create_table(
        'outcome_measurements',
        sa.Column('measurement_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('outcome_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric', sa.String(255), nullable=False, comment='Metric name being measured'),
        sa.Column('actual_value', sa.Float, nullable=False, comment='Measured actual value'),
        sa.Column('predicted_value', sa.Float, nullable=False, comment='Originally predicted value'),
        sa.Column('variance', sa.Float, nullable=False, comment='(actual - predicted) / predicted'),
        sa.Column('measured_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('notes', sa.Text, nullable=True, comment='Context or explanation for measurement'),
    )

    # Foreign key
    op.create_foreign_key(
        'fk_outcome_measurements_outcome',
        'outcome_measurements', 'decision_outcomes',
        ['outcome_id'], ['outcome_id'],
        ondelete='CASCADE'
    )

    # Indexes for outcome_measurements
    op.create_index('ix_outcome_measurements_outcome_id', 'outcome_measurements', ['outcome_id'])
    op.create_index('ix_outcome_measurements_metric', 'outcome_measurements', ['metric'])
    op.create_index('ix_outcome_measurements_measured_at', 'outcome_measurements', ['measured_at'])

    # Composite index for learning queries
    op.create_index(
        'ix_outcome_measurements_metric_variance',
        'outcome_measurements',
        ['metric', 'variance']
    )


def downgrade() -> None:
    """Remove Phase 5 autonomous learning schema."""

    # Drop indexes first
    op.drop_index('ix_outcome_measurements_metric_variance', table_name='outcome_measurements')
    op.drop_index('ix_outcome_measurements_measured_at', table_name='outcome_measurements')
    op.drop_index('ix_outcome_measurements_metric', table_name='outcome_measurements')
    op.drop_index('ix_outcome_measurements_outcome_id', table_name='outcome_measurements')

    op.drop_index('ix_decision_outcomes_created_at', table_name='decision_outcomes')
    op.drop_index('ix_decision_outcomes_status', table_name='decision_outcomes')
    op.drop_index('ix_decision_outcomes_session_id', table_name='decision_outcomes')

    # Drop foreign key
    op.drop_constraint('fk_outcome_measurements_outcome', 'outcome_measurements', type_='foreignkey')

    # Drop tables
    op.drop_table('outcome_measurements')
    op.drop_table('decision_outcomes')
