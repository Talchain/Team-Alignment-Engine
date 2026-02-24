"""Integration tests for Consensus Builder API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_consensus_request_payload():
    """Sample consensus request payload."""
    return {
        "perspectives": [
            {
                "user_id": "pm_001",
                "graph": {
                    "nodes": ["price_increase", "churn", "revenue"],
                    "edges": [
                        {"source": "price_increase", "target": "churn"},
                        {"source": "churn", "target": "revenue"},
                    ],
                },
                "reasoning": "A 30% price increase will boost revenue despite small churn",
                "submitted_at": "2025-01-15T10:30:00Z",
            },
            {
                "user_id": "engineer_002",
                "graph": {
                    "nodes": ["quality", "price", "retention"],
                    "edges": [
                        {"source": "quality", "target": "retention"},
                        {"source": "price", "target": "retention"},
                    ],
                },
                "reasoning": "Fix quality first, then consider pricing",
                "submitted_at": "2025-01-15T10:32:00Z",
            },
        ],
        "decision_context": "Considering 30% price increase for SaaS product",
        "require_creative_synthesis": True,
        "protect_minority_evidence": True,
        "min_causal_quality": "partial",
    }


@pytest.fixture
def mock_consensus_response():
    """Mock consensus response."""
    return {
        "shared_goals": ["Increase revenue", "Maintain customer satisfaction"],
        "shared_beliefs": ["Quality affects retention"],
        "synthesis_options": [
            {
                "description": "Pilot quality improvements with select customers, then phased 15% price increase",
                "causal_mechanism": "Quality improvements reduce churn risk, creating headroom for price increase",
                "satisfies_constraints": ["pm_001", "engineer_002"],
                "pareto_efficiency": 0.85,
                "creative_score": 0.72,
                "causal_graph_changes": {
                    "nodes_added": ["customer_satisfaction"],
                    "edges_added": ["quality → customer_satisfaction"],
                    "mediators_introduced": ["customer_satisfaction"],
                },
            }
        ],
        "conflicts": [],
        "warnings": [
            {
                "warning_type": "minority_has_strong_evidence",
                "severity": "warning",
                "message": "engineer_002's position has superior causal backing",
                "affected_positions": ["pm_001"],
                "recommendation": "Review evidence from engineer_002 before proceeding",
            }
        ],
        "quality_metrics": {
            "causal_validation_passed": True,
            "minority_positions_examined": True,
            "creative_synthesis_attempted": True,
            "forced_compromise_detected": False,
        },
        "trace": {
            "correlation_id": "consensus-test-123",
            "processing_time_ms": 2450.5,
            "isl_calls": 2,
            "llm_calls": 1,
        },
    }


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================


class TestConsensusBuilderAPI:
    """Tests for consensus builder API endpoint."""

    @pytest.mark.asyncio
    async def test_build_consensus_success(
        self,
        client: AsyncClient,
        sample_consensus_request_payload: dict,
    ):
        """Test successful consensus building."""
        with patch(
            "src.services.consensus_builder.ConsensusBuilder.build_consensus"
        ) as mock_build:
            # Mock the response
            from src.models.consensus import (
                ConsensusResponseV1,
                QualityMetricsV1,
                TraceMetadataV1,
            )

            mock_build.return_value = ConsensusResponseV1(
                shared_goals=["Increase revenue"],
                shared_beliefs=["Quality affects retention"],
                synthesis_options=[],
                conflicts=[],
                warnings=[],
                quality_metrics=QualityMetricsV1(
                    causal_validation_passed=True,
                    minority_positions_examined=False,
                    creative_synthesis_attempted=True,
                    forced_compromise_detected=False,
                ),
                trace=TraceMetadataV1(
                    correlation_id="test-123",
                    processing_time_ms=1000.0,
                    isl_calls=2,
                    llm_calls=1,
                ),
            )

            response = await client.post(
                "/api/v1/assist/consensus-builder",
                json=sample_consensus_request_payload,
            )

            assert response.status_code == 200
            data = response.json()

            assert "shared_goals" in data
            assert "synthesis_options" in data
            assert "quality_metrics" in data
            assert "trace" in data
            assert data["trace"]["correlation_id"] is not None

    @pytest.mark.asyncio
    async def test_build_consensus_validation_error_too_few_perspectives(
        self, client: AsyncClient
    ):
        """Test validation error with too few perspectives."""
        payload = {
            "perspectives": [
                {
                    "user_id": "pm_001",
                    "graph": {"nodes": ["price"], "edges": []},
                    "reasoning": "Test",
                }
            ],
            "decision_context": "Test decision",
        }

        response = await client.post(
            "/api/v1/assist/consensus-builder",
            json=payload,
        )

        # Should fail validation (min 2 perspectives)
        assert response.status_code == 400 or response.status_code == 422

    @pytest.mark.asyncio
    async def test_build_consensus_validation_error_too_many_perspectives(
        self, client: AsyncClient
    ):
        """Test validation error with too many perspectives."""
        # Create 11 perspectives (max is 10)
        perspectives = [
            {
                "user_id": f"user_{i}",
                "graph": {"nodes": ["a"], "edges": []},
                "reasoning": f"Perspective {i}",
            }
            for i in range(11)
        ]

        payload = {
            "perspectives": perspectives,
            "decision_context": "Test decision",
        }

        response = await client.post(
            "/api/v1/assist/consensus-builder",
            json=payload,
        )

        # Should fail validation (max 10 perspectives)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_build_consensus_with_trace_id(
        self,
        client: AsyncClient,
        sample_consensus_request_payload: dict,
    ):
        """Test consensus building with custom trace ID."""
        with patch(
            "src.services.consensus_builder.ConsensusBuilder.build_consensus"
        ) as mock_build:
            from src.models.consensus import (
                ConsensusResponseV1,
                QualityMetricsV1,
                TraceMetadataV1,
            )

            trace_id = "custom-trace-xyz"

            mock_build.return_value = ConsensusResponseV1(
                shared_goals=[],
                shared_beliefs=[],
                synthesis_options=[],
                conflicts=[],
                warnings=[],
                quality_metrics=QualityMetricsV1(
                    causal_validation_passed=True,
                    minority_positions_examined=False,
                    creative_synthesis_attempted=False,
                    forced_compromise_detected=False,
                ),
                trace=TraceMetadataV1(
                    correlation_id=trace_id,
                    processing_time_ms=500.0,
                    isl_calls=2,
                    llm_calls=0,
                ),
            )

            response = await client.post(
                "/api/v1/assist/consensus-builder",
                json=sample_consensus_request_payload,
                headers={"X-Request-ID": trace_id},
            )

            assert response.status_code == 200
            # Response should include trace ID in header
            assert response.headers.get("X-Request-ID") == trace_id

    @pytest.mark.asyncio
    async def test_consensus_builder_health_endpoint(self, client: AsyncClient):
        """Test consensus builder health endpoint."""
        response = await client.get("/api/v1/assist/consensus-builder/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "consensus-builder"
        assert "dependencies" in data


# ============================================================================
# SCENARIO TESTS
# ============================================================================


class TestConsensusBuilderScenarios:
    """Scenario-based tests for consensus builder."""

    @pytest.mark.asyncio
    async def test_pm_vs_engineer_scenario(
        self, client: AsyncClient
    ):
        """Test PM vs Engineer scenario from brief."""
        payload = {
            "perspectives": [
                {
                    "user_id": "pm_001",
                    "graph": {
                        "nodes": ["price_increase", "revenue"],
                        "edges": [{"source": "price_increase", "target": "revenue"}],
                    },
                    "reasoning": "30% price increase directly boosts revenue",
                },
                {
                    "user_id": "engineer_003",
                    "graph": {
                        "nodes": ["price_increase", "churn", "quality", "revenue"],
                        "edges": [
                            {"source": "price_increase", "target": "churn"},
                            {"source": "quality", "target": "churn"},
                            {"source": "churn", "target": "revenue"},
                        ],
                    },
                    "reasoning": "Price increase causes churn which reduces revenue. We need to fix quality first.",
                },
            ],
            "decision_context": "Deciding on 30% SaaS price increase",
            "protect_minority_evidence": True,
        }

        with patch(
            "src.services.consensus_builder.ConsensusBuilder.build_consensus"
        ) as mock_build:
            from src.models.consensus import (
                ConsensusResponseV1,
                ConsensusWarningV1,
                QualityMetricsV1,
                TraceMetadataV1,
            )

            mock_build.return_value = ConsensusResponseV1(
                shared_goals=["Increase revenue"],
                shared_beliefs=[],
                synthesis_options=[],
                conflicts=[],
                warnings=[
                    ConsensusWarningV1(
                        warning_type="minority_has_strong_evidence",
                        severity="warning",
                        message="engineer_003's position has superior causal backing (0.9 vs. avg 0.5)",
                        affected_positions=["pm_001"],
                        recommendation="Review evidence from engineer_003 before proceeding",
                    )
                ],
                quality_metrics=QualityMetricsV1(
                    causal_validation_passed=True,
                    minority_positions_examined=True,
                    creative_synthesis_attempted=False,
                    forced_compromise_detected=False,
                ),
                trace=TraceMetadataV1(
                    correlation_id="pm-engineer-test",
                    processing_time_ms=1500.0,
                    isl_calls=2,
                    llm_calls=0,
                ),
            )

            response = await client.post(
                "/api/v1/assist/consensus-builder",
                json=payload,
            )

            assert response.status_code == 200
            data = response.json()

            # Should have warnings about minority evidence
            assert len(data["warnings"]) > 0
            assert any(
                w["warning_type"] == "minority_has_strong_evidence"
                for w in data["warnings"]
            )
