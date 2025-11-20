"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "team-alignment-engine"
    assert "dependencies" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint."""
    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "team-alignment-engine"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient, sample_session_data):
    """Test creating a session."""
    response = await client.post("/api/v1/alignment/sessions", json=sample_session_data)

    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "collecting"
    assert "invite_links" in data
