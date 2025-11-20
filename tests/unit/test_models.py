"""Unit tests for data models."""

import pytest
from uuid import uuid4
from datetime import datetime

from src.models import (
    AlignmentSession,
    StakeholderProfile,
    ProposedOption,
    SessionStatus,
    AlignmentMode,
    DecisionType,
    RiskLevel,
    TimeHorizon,
)


def test_alignment_session_creation():
    """Test creating an alignment session."""
    team_id = uuid4()
    created_by = uuid4()

    session = AlignmentSession(
        team_id=team_id,
        decision_topic="Test Topic",
        decision_context="Test Context",
        decision_type=DecisionType.PRICING,
        alignment_mode=AlignmentMode.EVIDENCE_BACKED,
        stakeholders=[{"user_id": str(uuid4()), "role": "owner", "name": "Test"}],
        created_by=created_by,
    )

    assert session.team_id == team_id
    assert session.status == SessionStatus.COLLECTING
    assert session.decision_type == DecisionType.PRICING
    assert session.alignment_mode == AlignmentMode.EVIDENCE_BACKED
    assert isinstance(session.created_at, datetime)


def test_stakeholder_profile_goal_weights_validation():
    """Test that goal weights are validated to be between 0-1."""
    with pytest.raises(AssertionError, match="Goal weights must be 0-1"):
        StakeholderProfile(
            session_id=uuid4(),
            user_id=uuid4(),
            role="PM",
            desired_outcome="Test outcome",
            key_concerns=["Test concern"],
            goal_weights={"revenue": 1.5},  # Invalid: >1
            risk_tolerance=RiskLevel.MODERATE,
            time_horizon=TimeHorizon.QUARTERLY,
        )


def test_proposed_option_assumptions_validation():
    """Test that option assumptions have required fields."""
    with pytest.raises(AssertionError, match="Must have assumption_id"):
        ProposedOption(
            session_id=uuid4(),
            proposed_by=str(uuid4()),
            title="Test Option",
            description="Test description",
            expected_outcome="Test outcome",
            causal_rationale="Test rationale",
            addresses_goals=["revenue"],
            trade_offs=["timeline"],
            key_assumptions=[
                {"assumption_text": "Test"}  # Missing assumption_id
            ],
        )


def test_decision_template_pricing():
    """Test decision template for pricing."""
    from src.models import DecisionTemplate

    template = DecisionTemplate.get_template(DecisionType.PRICING)

    assert template.decision_type == DecisionType.PRICING
    assert "revenue_growth" in template.goal_dimensions
    assert "customer_retention" in template.goal_dimensions
    assert len(template.default_outcome_metrics) > 0
