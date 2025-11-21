"""Unit tests for fit calculator service."""

import pytest
from uuid import uuid4

from src.services.fit_calculator import FitCalculator
from src.models import (
    StakeholderProfile,
    ProposedOption,
    RiskLevel,
    TimeHorizon,
    FitLevel,
    ConsensusLevel,
)


@pytest.mark.asyncio
async def test_fit_calculator_strong_alignment():
    """Test strong fit when option addresses stakeholder goals."""
    calculator = FitCalculator()

    profile = StakeholderProfile(
        session_id=uuid4(),
        user_id=uuid4(),
        role="PM",
        desired_outcome="Revenue growth",
        key_concerns=[],
        goal_weights={"revenue_growth": 0.9, "customer_retention": 0.8},
        risk_tolerance=RiskLevel.MODERATE,
        time_horizon=TimeHorizon.QUARTERLY,
        must_have_constraints=[],
        red_lines=[],
    )

    option = ProposedOption(
        session_id=uuid4(),
        proposed_by="user",
        title="Revenue Option",
        description="Increase revenue",
        expected_outcome="15% revenue growth",
        causal_rationale="Pricing optimization",
        addresses_goals=["revenue_growth", "customer_retention"],
        trade_offs=[],
        key_assumptions=[{"assumption_id": "a1", "assumption_text": "Test"}],
    )

    fit_score = await calculator.calculate_fit(profile, option)

    assert fit_score.fit_score > 0.7
    assert fit_score.fit_level == FitLevel.STRONG
    assert "revenue_growth" in fit_score.satisfies_goals


@pytest.mark.asyncio
async def test_fit_calculator_constraint_violation():
    """Test that constraint violations lower fit score."""
    calculator = FitCalculator()

    profile = StakeholderProfile(
        session_id=uuid4(),
        user_id=uuid4(),
        role="PM",
        desired_outcome="Fast launch",
        key_concerns=["Must launch in 8 weeks"],
        goal_weights={"time_to_market": 0.9},
        risk_tolerance=RiskLevel.MODERATE,
        time_horizon=TimeHorizon.QUARTERLY,
        must_have_constraints=["Launch in 8 weeks"],
        red_lines=[],
    )

    option = ProposedOption(
        session_id=uuid4(),
        proposed_by="user",
        title="Slow Option",
        description="Takes 16 weeks timeline to complete",
        expected_outcome="High quality but slow",
        causal_rationale="Quality focus",
        addresses_goals=["time_to_market"],
        trade_offs=["timeline"],
        key_assumptions=[{"assumption_id": "a1", "assumption_text": "Test"}],
    )

    fit_score = await calculator.calculate_fit(profile, option)

    # Constraint violation should reduce score
    assert fit_score.fit_score < 0.7


@pytest.mark.asyncio
async def test_fit_calculator_overall_alignment():
    """Test overall alignment calculation across multiple stakeholders."""
    calculator = FitCalculator()

    profiles = [
        StakeholderProfile(
            session_id=uuid4(),
            user_id=uuid4(),
            role="PM",
            desired_outcome="Growth",
            key_concerns=[],
            goal_weights={"revenue_growth": 0.9},
            risk_tolerance=RiskLevel.MODERATE,
            time_horizon=TimeHorizon.QUARTERLY,
            must_have_constraints=[],
            red_lines=[],
        ),
        StakeholderProfile(
            session_id=uuid4(),
            user_id=uuid4(),
            role="Designer",
            desired_outcome="Quality",
            key_concerns=[],
            goal_weights={"product_quality": 0.9},
            risk_tolerance=RiskLevel.CONSERVATIVE,
            time_horizon=TimeHorizon.QUARTERLY,
            must_have_constraints=[],
            red_lines=[],
        ),
    ]

    option = ProposedOption(
        session_id=uuid4(),
        proposed_by="user",
        title="Balanced Option",
        description="Balance growth and quality",
        expected_outcome="Good outcome",
        causal_rationale="Balanced approach",
        addresses_goals=["revenue_growth", "product_quality"],
        trade_offs=[],
        key_assumptions=[{"assumption_id": "a1", "assumption_text": "Test"}],
    )

    fit = await calculator.calculate_all_fits(option, profiles)

    assert 0.0 <= fit.overall_alignment <= 1.0
    assert fit.consensus_level in [
        ConsensusLevel.STRONG,
        ConsensusLevel.MODERATE,
        ConsensusLevel.WEAK,
        ConsensusLevel.NONE,
    ]


@pytest.mark.asyncio
async def test_consensus_strength_calculation():
    """Test consensus strength from support levels."""
    calculator = FitCalculator()

    # Strong consensus
    support = {"user1": "strong", "user2": "strong", "user3": "strong"}
    strength = await calculator.calculate_consensus_strength(support)
    assert strength > 0.9

    # Mixed consensus
    support = {"user1": "strong", "user2": "moderate", "user3": "weak"}
    strength = await calculator.calculate_consensus_strength(support)
    assert 0.4 <= strength <= 0.8

    # No consensus
    support = {"user1": "weak", "user2": "weak", "user3": "none"}
    strength = await calculator.calculate_consensus_strength(support)
    assert strength < 0.5
