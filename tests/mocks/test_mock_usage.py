"""
Example tests demonstrating mock usage.

Shows how to use MockISLServer and MockPLoTClient for testing TAE
without requiring external services.
"""

import pytest
from fastapi.testclient import TestClient
from tests.mocks import create_mock_isl_server, create_mock_plot_client


class TestMockISLServer:
    """Test MockISLServer functionality."""

    def test_mock_isl_validation_endpoint(self):
        """Test that MockISLServer returns valid causal validation responses."""
        # Create mock ISL server
        mock_isl = create_mock_isl_server(latency_ms=0, identifiable_rate=1.0)

        # Create test client
        client = TestClient(mock_isl.app)

        # Prepare validation request
        payload = {
            "causal_graph": {
                "nodes": ["pricing", "churn", "revenue"],
                "edges": [
                    {"source": "pricing", "target": "churn"},
                    {"source": "churn", "target": "revenue"},
                ],
            },
            "interventions": [
                {"node": "pricing", "value": "increase_10_percent"}
            ],
            "outcome_metrics": ["revenue", "churn"],
            "time_horizon": "quarterly",
        }

        # Make request
        response = client.post(
            "/api/v1/causal/validate",
            json=payload,
            headers={"X-API-Key": "test-api-key-1234567890abcdef"},
        )

        # Verify response
        assert response.status_code == 200
        result = response.json()

        assert "request_id" in result
        assert result["is_identifiable"] is True  # Due to identifiable_rate=1.0
        assert "predicted_outcomes" in result
        assert "assumptions" in result
        assert len(result["assumptions"]) > 0

        # Verify predicted outcomes for requested metrics
        for metric in payload["outcome_metrics"]:
            assert metric in result["predicted_outcomes"]
            assert "point_estimate" in result["predicted_outcomes"][metric]
            assert "confidence_interval" in result["predicted_outcomes"][metric]

    def test_mock_isl_sensitivity_analysis(self):
        """Test sensitivity analysis endpoint."""
        mock_isl = create_mock_isl_server()
        client = TestClient(mock_isl.app)

        payload = {
            "validation_id": "val-123",
            "factor": "price_sensitivity",
            "baseline_value": 1.0,
            "alternative_value": 1.5,
        }

        response = client.post(
            "/api/v1/analysis/sensitivity",
            json=payload,
            headers={"X-API-Key": "test-key-1234567890abcdef"},
        )

        assert response.status_code == 200
        result = response.json()

        assert result["factor"] == "price_sensitivity"
        assert result["baseline_value"] == 1.0
        assert result["alternative_value"] == 1.5
        assert "sensitivity_score" in result
        assert "outcome_delta" in result
        assert "recommendation" in result

    def test_mock_isl_error_injection(self):
        """Test error injection capability."""
        # Create mock with 100% error rate
        mock_isl = create_mock_isl_server(error_rate=1.0)
        client = TestClient(mock_isl.app)

        payload = {
            "causal_graph": {"nodes": [], "edges": []},
            "interventions": [],
            "outcome_metrics": ["revenue"],
            "time_horizon": "quarterly",
        }

        response = client.post(
            "/api/v1/causal/validate",
            json=payload,
            headers={"X-API-Key": "test-key-1234567890abcdef"},
        )

        # Should get error due to error_rate=1.0
        assert response.status_code == 500

    def test_mock_isl_history_tracking(self):
        """Test that mock tracks validation history."""
        mock_isl = create_mock_isl_server()
        client = TestClient(mock_isl.app)

        # Make multiple requests
        for i in range(3):
            client.post(
                "/api/v1/causal/validate",
                json={
                    "causal_graph": {"nodes": [], "edges": []},
                    "interventions": [],
                    "outcome_metrics": [f"metric_{i}"],
                    "time_horizon": "quarterly",
                },
                headers={"X-API-Key": "test-key-1234567890abcdef"},
            )

        # Check history
        response = client.get("/mock/history")
        assert response.status_code == 200

        history = response.json()
        assert history["total_validations"] == 3
        assert len(history["history"]) == 3

    def test_mock_isl_configuration(self):
        """Test runtime configuration of mock behavior."""
        mock_isl = create_mock_isl_server()
        client = TestClient(mock_isl.app)

        # Configure mock
        config_response = client.post(
            "/mock/configure",
            json={
                "latency_ms": 500,
                "error_rate": 0.5,
                "identifiable_rate": 0.2,
            },
        )

        assert config_response.status_code == 200
        config = config_response.json()["current_config"]

        assert config["latency_ms"] == 500
        assert config["error_rate"] == 0.5
        assert config["identifiable_rate"] == 0.2


@pytest.mark.asyncio
class TestMockPLoTClient:
    """Test MockPLoTClient functionality."""

    async def test_mock_plot_request_structure(self):
        """
        Test that MockPLoTClient creates correct request structure.

        Note: This test would require a running TAE server.
        For unit testing, we just verify the client can be instantiated.
        """
        async with create_mock_plot_client() as plot_client:
            assert plot_client.base_url == "http://localhost:8000"
            assert len(plot_client.api_key) >= 16  # Valid API key length

            # History should be empty
            assert len(plot_client.get_request_history()) == 0

    async def test_mock_plot_history_tracking(self):
        """Test that client tracks request history."""
        async with create_mock_plot_client() as plot_client:
            # Initially empty
            assert len(plot_client.get_request_history()) == 0

            # Clear should not fail
            plot_client.clear_history()
            assert len(plot_client.get_request_history()) == 0


# Integration test example (requires running TAE + mock ISL)
@pytest.mark.integration
@pytest.mark.asyncio
class TestMockIntegration:
    """
    Integration tests using mocks.

    These tests require TAE server running with MockISLServer configured.
    """

    async def test_tae_with_mock_isl(self):
        """
        Test TAE calling MockISLServer for validation.

        Setup:
        1. Start MockISLServer on port 9000
        2. Configure TAE to use http://localhost:9000 as ISL_BASE_URL
        3. Make TAE request that triggers ISL validation
        4. Verify MockISLServer received and responded correctly
        """
        # This would be implemented in actual integration test suite
        # Demonstrates the testing pattern
        pass

    async def test_plot_calling_tae_with_mocks(self):
        """
        Test full workflow: PLoT → TAE → MockISL

        Setup:
        1. Start TAE with MockISLServer
        2. Use MockPLoTClient to request alignment data
        3. Verify response includes validated data from MockISL
        """
        # This would be implemented in actual integration test suite
        pass
