"""Unit tests for Consensus Builder service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from src.services.consensus_builder import CausalQualityScorer, ConsensusBuilder
from src.models.consensus import (
    TeamInputV1,
    GraphV1,
    ConsensusRequestV1,
    CausalQualityV1,
    ConflictAnalysisV1,
    ConsensusWarningV1,
)
from src.clients.isl_client import ISLClient
from src.clients.llm_client import LLMClient


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_graph_simple() -> GraphV1:
    """Simple causal graph fixture."""
    return GraphV1(
        nodes=["price", "churn", "revenue"],
        edges=[
            {"source": "price", "target": "churn"},
            {"source": "churn", "target": "revenue"},
        ],
    )


@pytest.fixture
def sample_graph_complex() -> GraphV1:
    """Complex causal graph with confounders."""
    return GraphV1(
        nodes=["price", "quality", "churn", "revenue", "satisfaction"],
        edges=[
            {"source": "price", "target": "churn"},
            {"source": "quality", "target": "churn"},
            {"source": "quality", "target": "satisfaction"},
            {"source": "churn", "target": "revenue"},
            {"source": "satisfaction", "target": "revenue"},
        ],
    )


@pytest.fixture
def sample_team_input(sample_graph_simple: GraphV1) -> TeamInputV1:
    """Sample team input fixture."""
    return TeamInputV1(
        user_id="pm_001",
        graph=sample_graph_simple,
        reasoning="Raise price 30% to boost revenue despite potential churn",
    )


@pytest.fixture
def sample_consensus_request(
    sample_graph_simple: GraphV1, sample_graph_complex: GraphV1
) -> ConsensusRequestV1:
    """Sample consensus request with two perspectives."""
    return ConsensusRequestV1(
        perspectives=[
            TeamInputV1(
                user_id="pm_001",
                graph=sample_graph_simple,
                reasoning="Raise price 30% to boost revenue",
            ),
            TeamInputV1(
                user_id="engineer_002",
                graph=sample_graph_complex,
                reasoning="Fix quality first, then consider pricing",
            ),
        ],
        decision_context="Considering 30% price increase for SaaS product",
        require_creative_synthesis=True,
        protect_minority_evidence=True,
        min_causal_quality="partial",
    )


@pytest.fixture
def mock_isl_client() -> AsyncMock:
    """Mock ISL client."""
    client = AsyncMock(spec=ISLClient)
    client.validate_option = AsyncMock(
        return_value={
            "validation_status": "VALIDATED",
            "is_identifiable": True,
            "predicted_outcomes": {},
            "key_assumptions": [],
            "warnings": [],
            "isl_response": {"confidence": 0.8},
            "isl_request_id": "test-isl-123",
        }
    )
    return client


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Mock LLM client."""
    client = AsyncMock(spec=LLMClient)
    client.generate_synthesis_options = AsyncMock(
        return_value=[
            {
                "description": "Pilot quality improvements, then phased 15% price increase",
                "causal_mechanism": "Quality improvements reduce churn risk",
                "satisfies_constraints": ["pm_001", "engineer_002"],
                "nodes_added": ["customer_satisfaction"],
                "edges_added": ["quality → customer_satisfaction"],
                "mediators_introduced": ["customer_satisfaction"],
            }
        ]
    )
    return client


# ============================================================================
# CAUSAL QUALITY SCORER TESTS
# ============================================================================


class TestCausalQualityScorer:
    """Tests for CausalQualityScorer."""

    @pytest.mark.asyncio
    async def test_score_team_input_identified(
        self, mock_isl_client: AsyncMock, sample_team_input: TeamInputV1
    ):
        """Test scoring a team input with identified causal graph."""
        scorer = CausalQualityScorer(isl_client=mock_isl_client)

        quality = await scorer.score_team_input(sample_team_input)

        assert quality.user_id == "pm_001"
        assert quality.identification_status == "identified"
        assert quality.robustness_score > 0.0

    @pytest.mark.asyncio
    async def test_detect_confounders(
        self, mock_isl_client: AsyncMock, sample_graph_complex: GraphV1
    ):
        """Test confounder detection."""
        scorer = CausalQualityScorer(isl_client=mock_isl_client)

        has_confounders = scorer._detect_confounders(sample_graph_complex)

        # quality → churn, quality → satisfaction (common cause)
        assert has_confounders is True

    @pytest.mark.asyncio
    async def test_detect_mediators(
        self, mock_isl_client: AsyncMock, sample_graph_simple: GraphV1
    ):
        """Test mediator detection."""
        scorer = CausalQualityScorer(isl_client=mock_isl_client)

        has_mediators = scorer._detect_mediators(sample_graph_simple)

        # price → churn → revenue (churn is mediator)
        assert has_mediators is True

    @pytest.mark.asyncio
    async def test_compute_robustness_score(self, mock_isl_client: AsyncMock):
        """Test robustness score computation."""
        scorer = CausalQualityScorer(isl_client=mock_isl_client)

        # Perfect case: identifiable, no confounders, no mediators
        score = scorer._compute_robustness_score(
            validation_result={"is_identifiable": True, "isl_response": {"confidence": 0.9}},
            has_confounders=False,
            has_mediators=False,
        )

        # Should be high: 0.4 (identifiable) + 0.3 (no confounders) + 0.2 (no mediators) + 0.09 (confidence)
        assert score >= 0.9

    @pytest.mark.asyncio
    async def test_collect_validation_issues(
        self, mock_isl_client: AsyncMock
    ):
        """Test validation issue collection."""
        scorer = CausalQualityScorer(isl_client=mock_isl_client)

        graph = GraphV1(
            nodes=["a", "b", "c", "isolated"],
            edges=[{"source": "a", "target": "b"}],
        )

        validation_result = {"warnings": ["Test warning"]}

        issues = scorer._collect_validation_issues(validation_result, graph)

        assert "Test warning" in issues
        assert any("isolated" in issue.lower() for issue in issues)


# ============================================================================
# CONFLICT CLASSIFICATION TESTS
# ============================================================================


class TestConflictClassification:
    """Tests for conflict classification."""

    @pytest.mark.asyncio
    async def test_classify_causal_conflict(
        self, mock_isl_client: AsyncMock, mock_llm_client: AsyncMock
    ):
        """Test classifying causal conflicts."""
        builder = ConsensusBuilder(
            isl_client=mock_isl_client, llm_client=mock_llm_client
        )

        # Two perspectives with conflicting edges
        perspective_a = TeamInputV1(
            user_id="user_a",
            graph=GraphV1(
                nodes=["price", "revenue"],
                edges=[{"source": "price", "target": "revenue"}],
            ),
            reasoning="Higher price increases revenue",
        )

        perspective_b = TeamInputV1(
            user_id="user_b",
            graph=GraphV1(
                nodes=["price", "revenue"],
                edges=[{"source": "revenue", "target": "price"}],  # Opposite direction
            ),
            reasoning="Higher revenue allows higher price",
        )

        quality_a = CausalQualityV1(
            user_id="user_a",
            identification_status="partial",
            has_confounders=False,
            has_mediators=False,
            robustness_score=0.6,
            validation_issues=[],
        )

        quality_b = CausalQualityV1(
            user_id="user_b",
            identification_status="partial",
            has_confounders=False,
            has_mediators=False,
            robustness_score=0.6,
            validation_issues=[],
        )

        conflict = await builder._analyze_pairwise_conflict(
            perspective_a, perspective_b, quality_a, quality_b
        )

        assert conflict is not None
        assert conflict.conflict_type == "causal"
        assert conflict.causal_conflict is not None

    @pytest.mark.asyncio
    async def test_extract_goals_from_reasoning(
        self, mock_isl_client: AsyncMock, mock_llm_client: AsyncMock
    ):
        """Test goal extraction from reasoning text."""
        builder = ConsensusBuilder(
            isl_client=mock_isl_client, llm_client=mock_llm_client
        )

        reasoning = "We need to increase revenue while maintaining quality and reducing churn"

        goals = builder._extract_goals(reasoning)

        assert "revenue" in goals
        assert "quality" in goals
        assert "churn" in goals


# ============================================================================
# MINORITY PROTECTION TESTS
# ============================================================================


class TestMinorityProtection:
    """Tests for minority position protection."""

    @pytest.mark.asyncio
    async def test_detect_minority_strong_evidence(
        self, mock_isl_client: AsyncMock, mock_llm_client: AsyncMock
    ):
        """Test detection of minority with superior evidence."""
        builder = ConsensusBuilder(
            isl_client=mock_isl_client, llm_client=mock_llm_client
        )

        # 3 perspectives: 2 weak, 1 strong
        perspectives = [
            TeamInputV1(
                user_id="user_weak_1",
                graph=GraphV1(nodes=["a"], edges=[]),
                reasoning="Simple view",
            ),
            TeamInputV1(
                user_id="user_weak_2",
                graph=GraphV1(nodes=["b"], edges=[]),
                reasoning="Another simple view",
            ),
            TeamInputV1(
                user_id="user_strong",
                graph=GraphV1(nodes=["c", "d", "e"], edges=[]),
                reasoning="Complex detailed analysis",
            ),
        ]

        causal_qualities = {
            "user_weak_1": CausalQualityV1(
                user_id="user_weak_1",
                identification_status="partial",
                has_confounders=False,
                has_mediators=False,
                robustness_score=0.3,
                validation_issues=[],
            ),
            "user_weak_2": CausalQualityV1(
                user_id="user_weak_2",
                identification_status="partial",
                has_confounders=False,
                has_mediators=False,
                robustness_score=0.3,
                validation_issues=[],
            ),
            "user_strong": CausalQualityV1(
                user_id="user_strong",
                identification_status="identified",
                has_confounders=False,
                has_mediators=False,
                robustness_score=0.9,
                validation_issues=[],
            ),
        }

        warnings = builder._detect_minority_strong_evidence(
            perspectives, causal_qualities
        )

        assert len(warnings) > 0
        assert any(w.warning_type == "minority_has_strong_evidence" for w in warnings)
        assert any("user_strong" in w.message for w in warnings)


# ============================================================================
# SYNTHESIS GENERATION TESTS
# ============================================================================


class TestSynthesisGeneration:
    """Tests for creative synthesis generation."""

    @pytest.mark.asyncio
    async def test_compute_pareto_efficiency(
        self, mock_isl_client: AsyncMock, mock_llm_client: AsyncMock
    ):
        """Test Pareto efficiency computation."""
        builder = ConsensusBuilder(
            isl_client=mock_isl_client, llm_client=mock_llm_client
        )

        # Satisfies 2 out of 3 stakeholders
        efficiency = builder._compute_pareto_efficiency(
            satisfies_constraints=["user_a", "user_b"],
            total_perspectives=3,
        )

        # Base: 2/3 = 0.67, Majority bonus: 0.2 = 0.87
        assert efficiency >= 0.8

    @pytest.mark.asyncio
    async def test_compute_creative_score(
        self, mock_isl_client: AsyncMock, mock_llm_client: AsyncMock, sample_graph_simple: GraphV1
    ):
        """Test creative score computation."""
        builder = ConsensusBuilder(
            isl_client=mock_isl_client, llm_client=mock_llm_client
        )

        perspectives = [
            TeamInputV1(
                user_id="user_a",
                graph=sample_graph_simple,
                reasoning="Test",
            )
        ]

        # Adding completely new nodes/edges
        score = builder._compute_creative_score(
            nodes_added=["new_node_1", "new_node_2"],
            edges_added=["new_node_1 → new_node_2", "new_node_2 → revenue"],
            perspectives=perspectives,
        )

        # Should have high creative score (novel nodes and edges)
        assert score > 0.5


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestConsensusBuilderIntegration:
    """Integration tests for full consensus building flow."""

    @pytest.mark.asyncio
    async def test_build_consensus_full_flow(
        self,
        mock_isl_client: AsyncMock,
        mock_llm_client: AsyncMock,
        sample_consensus_request: ConsensusRequestV1,
    ):
        """Test full consensus building flow."""
        builder = ConsensusBuilder(
            isl_client=mock_isl_client, llm_client=mock_llm_client
        )

        response = await builder.build_consensus(
            request=sample_consensus_request,
            trace_id="test-trace-123",
        )

        # Verify response structure
        assert response.trace.correlation_id == "test-trace-123"
        assert len(response.synthesis_options) >= 0
        assert response.quality_metrics is not None
        assert response.quality_metrics.causal_validation_passed is not None

        # Verify ISL was called for each perspective
        assert mock_isl_client.validate_option.call_count == len(
            sample_consensus_request.perspectives
        )

    @pytest.mark.asyncio
    async def test_build_consensus_with_conflicts(
        self, mock_isl_client: AsyncMock, mock_llm_client: AsyncMock
    ):
        """Test consensus building with conflicting perspectives."""
        request = ConsensusRequestV1(
            perspectives=[
                TeamInputV1(
                    user_id="pm_001",
                    graph=GraphV1(
                        nodes=["price", "revenue"],
                        edges=[{"source": "price", "target": "revenue"}],
                    ),
                    reasoning="Higher price increases revenue",
                ),
                TeamInputV1(
                    user_id="analyst_002",
                    graph=GraphV1(
                        nodes=["price", "churn", "revenue"],
                        edges=[
                            {"source": "price", "target": "churn"},
                            {"source": "churn", "target": "revenue"},
                        ],
                    ),
                    reasoning="Higher price increases churn which decreases revenue",
                ),
            ],
            decision_context="Price increase decision",
        )

        builder = ConsensusBuilder(
            isl_client=mock_isl_client, llm_client=mock_llm_client
        )

        response = await builder.build_consensus(request)

        # Should detect causal conflict
        assert len(response.conflicts) > 0
        # Should generate warnings or synthesis options
        assert len(response.warnings) > 0 or len(response.synthesis_options) > 0
