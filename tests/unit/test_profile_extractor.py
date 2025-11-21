"""Unit tests for profile extractor service."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from src.services.profile_extractor import ProfileExtractor
from src.models import RiskLevel, TimeHorizon


@pytest.mark.asyncio
async def test_profile_extractor_heuristic_revenue_focus():
    """Test heuristic extraction identifies revenue focus."""
    extractor = ProfileExtractor()

    profile = await extractor.create(
        session_id=uuid4(),
        user_id=uuid4(),
        role="PM",
        stakeholder_role="stakeholder",
        desired_outcome="Increase revenue by 20% through pricing optimization",
        key_concerns=["Customer churn", "Market competition"],
        preferred_option=None,
        goal_dimensions=["revenue_growth", "customer_retention"],
        decision_context="Pricing decision",
    )

    # Should extract high revenue weight
    assert profile.goal_weights.get("revenue_growth", 0) > 0.6
    assert profile.extraction_source in ["cee", "heuristic"]


@pytest.mark.asyncio
async def test_profile_extractor_conservative_risk():
    """Test heuristic extraction identifies conservative risk tolerance."""
    extractor = ProfileExtractor()

    profile = await extractor.create(
        session_id=uuid4(),
        user_id=uuid4(),
        role="PM",
        stakeholder_role="stakeholder",
        desired_outcome="We need a safe, conservative approach to pricing",
        key_concerns=["Risk of customer loss"],
        preferred_option=None,
        goal_dimensions=["revenue_growth"],
        decision_context="Pricing",
    )

    # Heuristic should detect conservative language
    assert profile.risk_tolerance in [RiskLevel.CONSERVATIVE, RiskLevel.MODERATE]


@pytest.mark.asyncio
async def test_profile_extractor_time_horizon_detection():
    """Test time horizon extraction."""
    extractor = ProfileExtractor()

    profile = await extractor.create(
        session_id=uuid4(),
        user_id=uuid4(),
        role="PM",
        stakeholder_role="stakeholder",
        desired_outcome="Need results within the next month",
        key_concerns=[],
        preferred_option=None,
        goal_dimensions=["time_to_market"],
        decision_context="Feature",
    )

    assert profile.time_horizon == TimeHorizon.MONTHLY


@pytest.mark.asyncio
async def test_profile_extractor_get_by_user():
    """Test retrieving profile by user ID."""
    extractor = ProfileExtractor()
    session_id = uuid4()
    user_id = uuid4()

    profile = await extractor.create(
        session_id=session_id,
        user_id=user_id,
        role="PM",
        stakeholder_role="stakeholder",
        desired_outcome="Test",
        key_concerns=["Test"],
        preferred_option=None,
        goal_dimensions=["revenue_growth"],
        decision_context="Test",
    )

    retrieved = await extractor.get_by_user(session_id, user_id)
    assert retrieved.profile_id == profile.profile_id


@pytest.mark.asyncio
async def test_profile_extractor_count():
    """Test counting profiles for a session."""
    extractor = ProfileExtractor()
    session_id = uuid4()

    # Create 3 profiles
    for i in range(3):
        await extractor.create(
            session_id=session_id,
            user_id=uuid4(),
            role=f"User{i}",
            stakeholder_role="stakeholder",
            desired_outcome="Test",
            key_concerns=["Test"],
            preferred_option=None,
            goal_dimensions=["revenue_growth"],
            decision_context="Test",
        )

    count = await extractor.count(session_id)
    assert count == 3


@pytest.mark.asyncio
async def test_profile_extractor_all_collected():
    """Test checking if all profiles collected."""
    extractor = ProfileExtractor()
    session_id = uuid4()

    # Create 2 profiles
    for i in range(2):
        await extractor.create(
            session_id=session_id,
            user_id=uuid4(),
            role=f"User{i}",
            stakeholder_role="stakeholder",
            desired_outcome="Test",
            key_concerns=["Test"],
            preferred_option=None,
            goal_dimensions=["revenue_growth"],
            decision_context="Test",
        )

    assert await extractor.all_collected(session_id, 2)
    assert not await extractor.all_collected(session_id, 3)
