"""Pytest configuration and fixtures."""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient

from src.api.main import app


@pytest.fixture
async def client() -> AsyncGenerator:
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    from uuid import uuid4

    return {
        "team_id": str(uuid4()),
        "decision_topic": "Test Decision",
        "decision_context": "This is a test decision",
        "decision_type": "custom",
        "alignment_mode": "evidence_backed",
        "stakeholders": [
            {
                "user_id": str(uuid4()),
                "role": "owner",
                "name": "Test Owner",
                "email": "owner@test.com",
            }
        ],
        "created_by": str(uuid4()),
    }


@pytest.fixture
def sample_profile_data():
    """Sample profile data for testing."""
    return {
        "desired_outcome": "Increase revenue by 15%",
        "key_concerns": ["Customer churn", "Timeline risk"],
        "preferred_option": None,
    }
