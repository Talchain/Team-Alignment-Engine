"""FACET client for counterfactual robustness analysis.

FACET (SIGMOD 2024): Robust counterfactual generation with confidence intervals.
"""

import logging
from typing import List, Dict, Any, Optional
import httpx
import random

from src.models.consensus import GraphV1
from src.models.deliberation import (
    RobustnessAnalysisV1,
    RobustnessDetailsV1,
    RobustRegionV1,
    ConfidenceIntervalV1,
    SensitivityFactorV1,
)

logger = logging.getLogger(__name__)


class FACETClient:
    """Client for FACET counterfactual robustness analysis.

    Usage:
        async with FACETClient() as client:
            analysis = await client.analyze_robustness(...)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        use_mock: bool = True,  # Use mock by default since FACET may not be deployed
    ):
        """Initialize FACET client.

        Args:
            base_url: FACET service URL
            api_key: API key for authentication
            timeout: Request timeout in seconds
            use_mock: Whether to use mock responses (default: True)
        """
        self.base_url = base_url or "http://facet.example.com"
        self.api_key = api_key
        self.timeout = timeout
        self.use_mock = use_mock
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Enter async context manager - create HTTP client."""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager - close HTTP client."""
        if self.client:
            await self.client.aclose()
        return False

    async def compute_robustness(
        self,
        graph: GraphV1,
        intervention_node: str,
        outcome_node: str,
        claim: str,
        num_scenarios: int = 20,
    ) -> RobustnessAnalysisV1:
        """Compute robustness analysis for a causal claim.

        Args:
            graph: Causal graph
            intervention_node: Node being intervened on
            outcome_node: Node being predicted
            claim: Natural language causal claim
            num_scenarios: Number of counterfactual scenarios to test

        Returns:
            Robustness analysis with counterfactual support
        """
        logger.info(
            f"Computing FACET robustness for {intervention_node} → {outcome_node}",
            extra={
                "num_scenarios": num_scenarios,
                "use_mock": self.use_mock,
            },
        )

        if self.use_mock:
            return await self._mock_robustness_analysis(
                graph, intervention_node, outcome_node, claim, num_scenarios
            )

        try:
            # Call real FACET service
            response = await self.client.post(
                f"{self.base_url}/api/v1/robustness",
                json={
                    "graph": {
                        "nodes": graph.nodes,
                        "edges": [{"source": e["source"], "target": e["target"]} for e in graph.edges],
                    },
                    "intervention": intervention_node,
                    "outcome": outcome_node,
                    "num_scenarios": num_scenarios,
                },
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            result = response.json()

            return self._parse_facet_response(result, claim)

        except httpx.HTTPError as e:
            logger.error(f"FACET request failed: {e}", exc_info=True)
            # Fallback to mock on error
            return await self._mock_robustness_analysis(
                graph, intervention_node, outcome_node, claim, num_scenarios
            )

    async def _mock_robustness_analysis(
        self,
        graph: GraphV1,
        intervention_node: str,
        outcome_node: str,
        claim: str,
        num_scenarios: int,
    ) -> RobustnessAnalysisV1:
        """Generate mock robustness analysis for testing.

        Uses graph structure to generate plausible robustness scores.
        More complex graphs → lower robustness.

        Args:
            graph: Causal graph
            intervention_node: Intervention node
            outcome_node: Outcome node
            claim: Causal claim
            num_scenarios: Number of scenarios to simulate

        Returns:
            Mock robustness analysis
        """
        # Check graph complexity
        num_nodes = len(graph.nodes)
        num_edges = len(graph.edges)

        # Simple graphs are more robust
        if num_nodes <= 3 and num_edges <= 2:
            identification_status = "identified"
            base_robustness = 0.85
        elif num_nodes <= 5 and num_edges <= 4:
            identification_status = "partial"
            base_robustness = 0.65
        else:
            identification_status = "partial"
            base_robustness = 0.45

        # Check for confounders (nodes with multiple outgoing edges)
        has_confounders = any(
            sum(1 for e in graph.edges if e["source"] == node) >= 2
            for node in graph.nodes
        )

        if has_confounders:
            base_robustness *= 0.8
            identification_status = "partial"

        # Add some randomness
        robustness_score = min(max(base_robustness + random.uniform(-0.1, 0.1), 0.0), 1.0)

        # Generate scenarios
        scenarios_supporting = int(num_scenarios * robustness_score)
        scenarios_contradicting = num_scenarios - scenarios_supporting

        # Confidence interval
        std_error = (robustness_score * (1 - robustness_score) / num_scenarios) ** 0.5
        ci_lower = max(robustness_score - 1.96 * std_error, 0.0)
        ci_upper = min(robustness_score + 1.96 * std_error, 1.0)

        # Detect sensitivity factors
        sensitivity_factors = []
        if has_confounders:
            # Find nodes with multiple outgoing edges
            for node in graph.nodes:
                outgoing = [e for e in graph.edges if e["source"] == node]
                if len(outgoing) >= 2:
                    sensitivity_factors.append(
                        SensitivityFactorV1(
                            factor=node,
                            impact_on_estimate="high" if len(outgoing) >= 3 else "medium",
                        )
                    )

        # Robust region (if robustness is high)
        robust_region = None
        if robustness_score >= 0.7:
            robust_region = RobustRegionV1(
                interventions=[
                    f"increase {intervention_node}",
                    f"double {intervention_node}",
                    f"triple {intervention_node}",
                ],
                all_lead_to=f"increase in {outcome_node}",
            )

        return RobustnessAnalysisV1(
            perspective_id="mock",
            causal_claim=claim,
            identification_status=identification_status,
            robustness_score=round(robustness_score, 2),
            robustness_analysis=RobustnessDetailsV1(
                scenarios_tested=num_scenarios,
                scenarios_supporting=scenarios_supporting,
                scenarios_contradicting=scenarios_contradicting,
                robust_region=robust_region,
            ),
            confidence_interval=ConfidenceIntervalV1(
                lower=round(ci_lower, 2),
                upper=round(ci_upper, 2),
                confidence_level=0.95,
            ),
            sensitivity_factors=sensitivity_factors,
        )

    def _parse_facet_response(
        self, facet_result: Dict[str, Any], claim: str
    ) -> RobustnessAnalysisV1:
        """Parse FACET service response into RobustnessAnalysisV1.

        Args:
            facet_result: Raw FACET response
            claim: Original causal claim

        Returns:
            Parsed robustness analysis
        """
        # Extract robustness score
        robustness_score = facet_result.get("robustness_score", 0.5)

        # Extract counterfactual details
        counterfactuals = facet_result.get("counterfactuals", [])
        supporting = sum(1 for cf in counterfactuals if cf.get("supports_claim", False))
        contradicting = len(counterfactuals) - supporting

        # Parse robust region
        robust_region = None
        if "robust_region" in facet_result:
            robust_region = RobustRegionV1(
                interventions=facet_result["robust_region"].get("interventions", []),
                all_lead_to=facet_result["robust_region"].get("consistent_outcome", ""),
            )

        # Parse sensitivity factors
        sensitivity_factors = [
            SensitivityFactorV1(
                factor=factor["name"],
                impact_on_estimate=factor["impact"],
            )
            for factor in facet_result.get("sensitivity_factors", [])
        ]

        return RobustnessAnalysisV1(
            perspective_id=facet_result.get("perspective_id", "unknown"),
            causal_claim=claim,
            identification_status=facet_result.get("identification_status", "partial"),
            robustness_score=robustness_score,
            robustness_analysis=RobustnessDetailsV1(
                scenarios_tested=len(counterfactuals),
                scenarios_supporting=supporting,
                scenarios_contradicting=contradicting,
                robust_region=robust_region,
            ),
            confidence_interval=ConfidenceIntervalV1(
                lower=facet_result.get("ci_lower", robustness_score - 0.1),
                upper=facet_result.get("ci_upper", robustness_score + 0.1),
                confidence_level=facet_result.get("confidence_level", 0.95),
            ),
            sensitivity_factors=sensitivity_factors,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
