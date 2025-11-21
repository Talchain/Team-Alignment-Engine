"""Unit tests for disagreement analyzer service."""

import pytest
from uuid import uuid4

from src.services.disagreement_analyzer import DisagreementAnalyzer
from src.models import StakeholderProfile, RiskLevel, TimeHorizon


@pytest.mark.asyncio
async def test_find_common_ground_high_agreement():
    """Test identifying common ground when goals align."""
    analyzer = DisagreementAnalyzer()

    profiles = [
        StakeholderProfile(
            session_id=uuid4(),
            user_id=uuid4(),
            role="PM",
            desired_outcome="Revenue growth",
            key_concerns=["Churn"],
            goal_weights={"revenue_growth": 0.9, "customer_retention": 0.8},
            risk_tolerance=RiskLevel.MODERATE,
            time_horizon=TimeHorizon.QUARTERLY,
        ),
        StakeholderProfile(
            session_id=uuid4(),
            user_id=uuid4(),
            role="Designer",
            desired_outcome="Revenue and retention",
            key_concerns=["Churn"],
            goal_weights={"revenue_growth": 0.85, "customer_retention": 0.9},
            risk_tolerance=RiskLevel.MODERATE,
            time_horizon=TimeHorizon.QUARTERLY,
        ),
    ]

    shared_ground = await analyzer.find_common_ground(profiles, "Test context")

    # Should find common goals
    assert len(shared_ground.common_goals) > 0
    assert any(g["goal"] == "revenue_growth" for g in shared_ground.common_goals)


@pytest.mark.asyncio
async def test_map_tensions_conflicting_priorities():
    """Test identifying tensions when priorities conflict."""
    analyzer = DisagreementAnalyzer()

    profiles = [
        StakeholderProfile(
            session_id=uuid4(),
            user_id=uuid4(),
            role="PM",
            desired_outcome="Fast delivery",
            key_concerns=[],
            goal_weights={"time_to_market": 0.9, "product_quality": 0.3},
            risk_tolerance=RiskLevel.AGGRESSIVE,
            time_horizon=TimeHorizon.WEEKLY,
        ),
        StakeholderProfile(
            session_id=uuid4(),
            user_id=uuid4(),
            role="QA",
            desired_outcome="High quality",
            key_concerns=[],
            goal_weights={"time_to_market": 0.2, "product_quality": 0.95},
            risk_tolerance=RiskLevel.CONSERVATIVE,
            time_horizon=TimeHorizon.QUARTERLY,
        ),
    ]

    disagreement_map = await analyzer.map_tensions(profiles, "Test context")

    # Should find tension between speed and quality
    assert len(disagreement_map.primary_tensions) > 0


@pytest.mark.asyncio
async def test_identify_common_concerns():
    """Test identifying concerns mentioned by multiple stakeholders."""
    analyzer = DisagreementAnalyzer()

    profiles = [
        StakeholderProfile(
            session_id=uuid4(),
            user_id=uuid4(),
            role="PM",
            desired_outcome="Test",
            key_concerns=["customer churn", "timeline risk"],
            goal_weights={"revenue_growth": 0.8},
            risk_tolerance=RiskLevel.MODERATE,
            time_horizon=TimeHorizon.QUARTERLY,
        ),
        StakeholderProfile(
            session_id=uuid4(),
            user_id=uuid4(),
            role="Designer",
            desired_outcome="Test",
            key_concerns=["churn rate", "customer satisfaction"],
            goal_weights={"revenue_growth": 0.7},
            risk_tolerance=RiskLevel.MODERATE,
            time_horizon=TimeHorizon.QUARTERLY,
        ),
    ]

    common_concerns = analyzer._identify_common_concerns(profiles)

    # Should find "churn" mentioned by both
    assert any("churn" in concern for concern in common_concerns)


@pytest.mark.asyncio
async def test_empty_profiles_handling():
    """Test handling empty profile list."""
    analyzer = DisagreementAnalyzer()

    shared_ground = await analyzer.find_common_ground([], "Test context")
    disagreement_map = await analyzer.map_tensions([], "Test context")

    assert len(shared_ground.common_goals) == 0
    assert len(disagreement_map.primary_tensions) == 0
