"""Enhanced conflict diagnosis utilities.

Provides decisive tests, Pareto analysis, and reframing for conflict resolution.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from src.models.consensus import (
    ConflictAnalysisV1,
    TeamInputV1,
    GraphV1,
    CausalQualityV1,
)
from src.models.deliberation import (
    DecisiveTestV1,
    SuggestedTestV1,
    ResolutionCriteriaV1,
    ParetoAnalysisV1,
    ParetoOptionV1,
    DimensionV1,
    ReframingAnalysisV1,
    SharedGoalV1,
    AlternativePathV1,
)
from src.clients.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ConflictDiagnosisService:
    """Service for enhanced conflict diagnosis."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize conflict diagnosis service.

        Args:
            llm_client: LLM client for generating tests and reframings

        Note:
            In production, llm_client should always be provided via dependency
            injection to ensure proper resource cleanup. The fallback is for
            testing only and may leak resources.
        """
        self.llm_client = llm_client or LLMClient()  # Fallback for tests only

    async def suggest_decisive_test(
        self,
        conflict: ConflictAnalysisV1,
        decision_context: str,
    ) -> Optional[DecisiveTestV1]:
        """Suggest a decisive test to resolve causal conflict.

        Args:
            conflict: Causal conflict to resolve
            decision_context: Decision background context

        Returns:
            Decisive test suggestion or None if not causal conflict
        """
        if conflict.conflict_type != "causal" or not conflict.causal_conflict:
            return None

        logger.info(f"Generating decisive test for causal conflict")

        # Extract hypotheses from positions
        if len(conflict.positions) < 2:
            return None

        position_a = conflict.positions[0]
        position_b = conflict.positions[1]

        hypothesis_a = position_a.position[:200]
        hypothesis_b = position_b.position[:200]

        # Generate test via LLM
        prompt = f"""
You are a scientific advisor helping resolve a causal disagreement.

Context: {decision_context}

Hypothesis A ({position_a.user_id}): {hypothesis_a}
Causal quality: {position_a.causal_backing.robustness_score:.2f}

Hypothesis B ({position_b.user_id}): {hypothesis_b}
Causal quality: {position_b.causal_backing.robustness_score:.2f}

Design a decisive test that would definitively support Hypothesis A or B.

The test must:
1. Directly measure the differential mechanism
2. Be practically feasible for a product team
3. Provide clear resolution criteria

Return JSON matching this schema:
{{
  "description": "Clear description of the test",
  "test_type": "A/B test" | "observational study" | "historical analysis" | "expert consultation",
  "metrics": ["metric1", "metric2"],
  "intervention": "intervention for A/B test (optional)",
  "resolution_criteria": [
    {{"outcome": "if metric X > Y", "supports_hypothesis": "A"}},
    {{"outcome": "if metric X < Y", "supports_hypothesis": "B"}}
  ],
  "estimated_duration": "e.g., 2 weeks",
  "estimated_cost": "low" | "medium" | "high",
  "confidence_gain": 0.7
}}

If test is infeasible, also provide:
"alternative_resolution": "Suggest proxy evidence or expert consultation"
"""

        try:
            # Call LLM
            response_text = await self.llm_client._call_llm(prompt)

            # Parse JSON from response
            import json
            response_data = self.llm_client._parse_synthesis_response(response_text)

            if not response_data or len(response_data) == 0:
                # Fallback to manual construction
                return self._create_fallback_test(position_a, position_b, decision_context)

            test_data = response_data[0] if isinstance(response_data, list) else response_data

            # Build DecisiveTestV1
            resolution_criteria = [
                ResolutionCriteriaV1(
                    outcome=criterion.get("outcome", ""),
                    supports_hypothesis=criterion.get("supports_hypothesis", "A"),
                )
                for criterion in test_data.get("resolution_criteria", [])
            ]

            suggested_test = SuggestedTestV1(
                description=test_data.get("description", "Run experiment to test hypotheses"),
                test_type=test_data.get("test_type", "A/B test"),
                metrics=test_data.get("metrics", ["outcome_metric"]),
                intervention=test_data.get("intervention"),
                resolution_criteria=resolution_criteria or [
                    ResolutionCriteriaV1(outcome="Positive result", supports_hypothesis="A"),
                    ResolutionCriteriaV1(outcome="Negative result", supports_hypothesis="B"),
                ],
                estimated_duration=test_data.get("estimated_duration", "2 weeks"),
                estimated_cost=test_data.get("estimated_cost", "medium"),
                confidence_gain=test_data.get("confidence_gain", 0.6),
            )

            return DecisiveTestV1(
                conflict_id=f"conflict-{position_a.user_id}-{position_b.user_id}",
                hypothesis_a=hypothesis_a,
                hypothesis_b=hypothesis_b,
                suggested_test=suggested_test,
                alternative_resolution=test_data.get("alternative_resolution"),
            )

        except Exception as e:
            logger.error(f"Failed to generate decisive test: {e}", exc_info=True)
            return self._create_fallback_test(position_a, position_b, decision_context)

    def _create_fallback_test(
        self,
        position_a: Any,
        position_b: Any,
        decision_context: str,
    ) -> DecisiveTestV1:
        """Create a simple fallback test when LLM fails.

        Args:
            position_a: First position
            position_b: Second position
            decision_context: Decision context

        Returns:
            Basic decisive test
        """
        return DecisiveTestV1(
            conflict_id=f"conflict-{position_a.user_id}-{position_b.user_id}",
            hypothesis_a=position_a.position[:200],
            hypothesis_b=position_b.position[:200],
            suggested_test=SuggestedTestV1(
                description=f"Run A/B test to measure outcomes of both approaches",
                test_type="A/B test",
                metrics=["primary_outcome", "secondary_outcome"],
                intervention=f"Implement approach from {position_a.user_id}",
                resolution_criteria=[
                    ResolutionCriteriaV1(
                        outcome="Positive results favor approach A",
                        supports_hypothesis="A",
                    ),
                    ResolutionCriteriaV1(
                        outcome="Negative results favor approach B",
                        supports_hypothesis="B",
                    ),
                ],
                estimated_duration="2-4 weeks",
                estimated_cost="medium",
                confidence_gain=0.6,
            ),
            alternative_resolution="Consult domain expert or review historical data",
        )

    def analyze_pareto_frontier(
        self,
        conflict: ConflictAnalysisV1,
        synthesis_options: List[Any],
    ) -> Optional[ParetoAnalysisV1]:
        """Analyze Pareto frontier for values conflicts.

        Args:
            conflict: Values conflict
            synthesis_options: Available synthesis options

        Returns:
            Pareto analysis or None if not values conflict
        """
        if conflict.conflict_type != "values" or not conflict.values_conflict:
            return None

        logger.info("Analyzing Pareto frontier for values conflict")

        # Extract dimensions from conflict
        dimensions = []
        for dimension_name in conflict.values_conflict.trade_off_dimensions:
            stakeholders = [
                pos.user_id
                for pos in conflict.positions
                if dimension_name.lower() in pos.position.lower()
            ]

            dimensions.append(
                DimensionV1(
                    dimension=dimension_name,
                    unit="score",
                    stakeholders_prioritizing=stakeholders,
                )
            )

        # Score each option on each dimension
        pareto_options = []
        for option in synthesis_options:
            # Simple scoring based on description keywords
            scores = {}
            for dim in dimensions:
                # Count mentions of dimension in option description
                description_lower = option.description.lower()
                score = min(
                    description_lower.count(dim.dimension.lower()) * 0.3 + 0.5,
                    1.0,
                )
                scores[dim.dimension] = round(score, 2)

            # Check if Pareto optimal (not dominated by any other option)
            dominated_by = []
            for other_option in synthesis_options:
                if other_option == option:
                    continue

                # Check if other_option dominates this option
                # (better on all dimensions)
                other_scores = {
                    dim.dimension: min(
                        other_option.description.lower().count(dim.dimension.lower()) * 0.3 + 0.5,
                        1.0,
                    )
                    for dim in dimensions
                }

                if all(other_scores.get(d, 0) >= scores.get(d, 0) for d in scores):
                    if any(other_scores.get(d, 0) > scores.get(d, 0) for d in scores):
                        dominated_by.append(other_option.description)

            pareto_optimal = len(dominated_by) == 0

            pareto_options.append(
                ParetoOptionV1(
                    option_id=option.description,
                    scores=scores,
                    pareto_optimal=pareto_optimal,
                    dominated_by=dominated_by,
                )
            )

        return ParetoAnalysisV1(
            conflict_id=f"values-conflict-{conflict.positions[0].user_id}",
            dimensions=dimensions,
            pareto_options=pareto_options,
            recommendation="Choose based on organizational values - no option is strictly better than all others",
        )

    async def generate_reframing(
        self,
        conflict: ConflictAnalysisV1,
        decision_context: str,
    ) -> Optional[ReframingAnalysisV1]:
        """Generate reframing analysis for framing conflicts.

        Args:
            conflict: Framing conflict
            decision_context: Decision context

        Returns:
            Reframing analysis or None if not framing conflict
        """
        if conflict.conflict_type != "framing" or not conflict.framing_conflict:
            return None

        logger.info("Generating reframing analysis for framing conflict")

        # Extract original positions
        original_positions = [pos.position[:200] for pos in conflict.positions]

        # Extract shared goal from framing conflict
        shared_goal_text = conflict.framing_conflict.shared_goal

        # Extract alternative paths
        alternative_paths = []
        for pos in conflict.positions:
            alternative_paths.append(
                AlternativePathV1(
                    path_description=pos.position[:150],
                    supporting_stakeholders=[pos.user_id],
                    causal_mechanism=f"Via {pos.user_id}'s approach",
                    potential_synergies=[
                        "Could combine with other approaches",
                        "Addresses same goal from different angle",
                    ],
                )
            )

        # Generate reframed question via LLM
        prompt = f"""
You are facilitating a team discussion where people agree on the goal but disagree on the path.

Context: {decision_context}

Shared Goal: {shared_goal_text}

Different Approaches:
{chr(10).join(f"- {pos}" for pos in original_positions)}

Generate a reframed question that:
1. Emphasizes the shared goal
2. Opens space for combining approaches
3. Focuses on "how" rather than "which"

Return a single reframed question (1-2 sentences).
"""

        try:
            response = await self.llm_client._call_llm(prompt)
            reframed_question = response.strip().strip('"\'')

            if not reframed_question:
                reframed_question = f"How can we best achieve {shared_goal_text}?"

        except Exception as e:
            logger.error(f"Failed to generate reframing: {e}", exc_info=True)
            reframed_question = f"How can we best achieve {shared_goal_text}?"

        return ReframingAnalysisV1(
            conflict_id=f"framing-{conflict.positions[0].user_id}",
            original_positions=original_positions,
            shared_goal=SharedGoalV1(
                description=shared_goal_text,
                confidence=0.8,
                evidence=[pos.position[:100] for pos in conflict.positions[:2]],
            ),
            alternative_paths=alternative_paths,
            reframed_question=reframed_question,
        )


# Singleton instance
_conflict_diagnosis_service: Optional[ConflictDiagnosisService] = None


def get_conflict_diagnosis_service(llm_client: Optional[LLMClient] = None) -> ConflictDiagnosisService:
    """Get or create conflict diagnosis service singleton.

    Args:
        llm_client: Optional LLM client

    Returns:
        ConflictDiagnosisService instance
    """
    global _conflict_diagnosis_service
    if _conflict_diagnosis_service is None:
        _conflict_diagnosis_service = ConflictDiagnosisService(llm_client=llm_client)
    return _conflict_diagnosis_service
