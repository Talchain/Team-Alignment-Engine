"""Unit tests for services."""

import pytest
from uuid import uuid4

from src.models import DecisionType, AlignmentMode, SessionStatus
from src.services import SessionManager, FitCalculator


@pytest.mark.asyncio
async def test_session_manager_create():
    """Test session manager can create sessions."""
    manager = SessionManager()

    team_id = uuid4()
    created_by = uuid4()

    session = await manager.create(
        team_id=team_id,
        decision_topic="Test Topic",
        decision_context="Test Context",
        decision_type=DecisionType.PRICING,
        alignment_mode=AlignmentMode.QUICK,
        stakeholders=[{"user_id": str(uuid4()), "role": "owner", "name": "Test"}],
        created_by=created_by,
    )

    assert session.team_id == team_id
    assert session.status == SessionStatus.COLLECTING

    # Can retrieve session
    retrieved = await manager.get(session.session_id)
    assert retrieved.session_id == session.session_id


@pytest.mark.asyncio
async def test_session_manager_update_status():
    """Test updating session status."""
    manager = SessionManager()

    session = await manager.create(
        team_id=uuid4(),
        decision_topic="Test",
        decision_context="Test",
        decision_type=DecisionType.CUSTOM,
        alignment_mode=AlignmentMode.QUICK,
        stakeholders=[],
        created_by=uuid4(),
    )

    await manager.update_status(session.session_id, SessionStatus.ANALYZING)

    updated = await manager.get(session.session_id)
    assert updated.status == SessionStatus.ANALYZING


@pytest.mark.asyncio
async def test_fit_calculator_consensus_level():
    """Test consensus level determination."""
    calculator = FitCalculator()

    # Strong consensus
    support = {
        "user1": "strong",
        "user2": "strong",
        "user3": "strong",
    }
    strength = await calculator.calculate_consensus_strength(support)
    assert strength > 0.8

    # Weak consensus
    support = {
        "user1": "strong",
        "user2": "weak",
        "user3": "none",
    }
    strength = await calculator.calculate_consensus_strength(support)
    assert strength < 0.6
