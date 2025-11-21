"""Assumption Testing Advisor service (Phase C: C4).

Recommends which assumptions to validate before making a decision.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.clients.cee_client import CEEClient
from src.models.option import ProposedOption
from src.models.validation import AssumptionStrength
from src.models.phase_c_models import TestStrategy

logger = logging.getLogger(__name__)


class AssumptionTestingAdvisor:
    """Service for recommending assumption validation strategies."""

    def __init__(self, cee_client: CEEClient):
        """Initialize with CEE client."""
        self.cee = cee_client

    async def recommend_test_strategies(
        self,
        option: ProposedOption,
        assumptions: List[AssumptionStrength],
        decision_context: str,
        time_to_decision: int,
        available_resources: Optional[Dict[str, Any]] = None,
    ) -> List[TestStrategy]:
        """
        Recommend testing strategies for critical assumptions.

        Args:
            option: Option being validated
            assumptions: List of assumptions with strength assessments
            decision_context: Context of the decision
            time_to_decision: Days until decision needed
            available_resources: Optional resource constraints
                (e.g., {"budget": 10000, "team_size": 3})

        Returns:
            List of TestStrategy recommendations, prioritized by importance

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        logger.info(
            "Recommending test strategies",
            extra={
                "option_id": str(option.option_id),
                "num_assumptions": len(assumptions),
                "days_to_decision": time_to_decision,
            },
        )

        # Convert option and assumptions to dicts for CEE
        option_data = {
            "option_id": str(option.option_id),
            "title": option.title,
            "description": option.description,
            "expected_outcome": option.expected_outcome,
            "causal_rationale": option.causal_rationale,
        }

        assumptions_data = [
            {
                "assumption_id": a.assumption_id,
                "assumption_text": a.assumption_text,
                "evidence_level": a.evidence_strength.value,
                "impact_level": a.impact_if_wrong.value,
                "source": a.source,
            }
            for a in assumptions
        ]

        # Call CEE to get recommendations
        cee_response = await self.cee.recommend_test_strategy(
            assumptions=assumptions_data,
            option=option_data,
            decision_context=decision_context,
            time_to_decision=time_to_decision,
            available_resources=available_resources,
        )

        # Extract recommendations from CEE response
        recommendations_data = cee_response.get("recommendations", [])

        # Convert to TestStrategy objects
        strategies: List[TestStrategy] = []
        for rec in recommendations_data:
            strategy = TestStrategy(
                assumption_id=rec.get("assumption_id"),
                priority=rec.get("priority", 1),
                recommended_method=rec.get("recommended_method"),
                estimated_effort_days=rec.get("estimated_effort_days", 0),
                estimated_cost=rec.get("estimated_cost", 0.0),
                rationale=rec.get("rationale", ""),
                alternative_methods=rec.get("alternative_methods", []),
                expected_confidence_gain=rec.get("expected_confidence_gain", 0.0),
            )
            strategies.append(strategy)

        logger.info(
            "Test strategy recommendations complete",
            extra={
                "option_id": str(option.option_id),
                "num_recommendations": len(strategies),
                "top_priority_method": strategies[0].recommended_method if strategies else None,
            },
        )

        return strategies

    async def prioritize_assumptions(
        self, assumptions: List[AssumptionStrength]
    ) -> List[AssumptionStrength]:
        """
        Prioritize assumptions by criticality for testing.

        Prioritization based on:
        1. High impact + low evidence = highest priority
        2. High impact + medium evidence = medium priority
        3. Low impact or high evidence = lower priority

        Args:
            assumptions: List of assumptions with strength assessments

        Returns:
            Sorted list of assumptions (highest priority first)
        """
        # Define priority scoring function
        def priority_score(assumption: AssumptionStrength) -> float:
            # Impact: critical=3, high=2, medium=1, low=0
            impact_scores = {
                "critical": 3.0,
                "high": 2.0,
                "medium": 1.0,
                "low": 0.0,
            }

            # Evidence: none=3, weak=2, medium=1, strong=0 (inverse - less evidence = higher priority)
            evidence_scores = {
                "none": 3.0,
                "weak": 2.0,
                "medium": 1.0,
                "strong": 0.0,
            }

            impact = impact_scores.get(assumption.impact_if_wrong.value, 1.0)
            evidence_inverse = evidence_scores.get(assumption.evidence_strength.value, 1.0)

            # Priority = impact * (4 - evidence)
            # This gives highest score to high impact + low evidence
            return impact * (1.0 + evidence_inverse)

        # Sort by priority score descending
        prioritized = sorted(assumptions, key=priority_score, reverse=True)

        logger.info(
            "Prioritized assumptions",
            extra={
                "total_assumptions": len(assumptions),
                "top_priority": (
                    {
                        "id": prioritized[0].assumption_id,
                        "impact": prioritized[0].impact_if_wrong.value,
                        "evidence": prioritized[0].evidence_strength.value,
                    }
                    if prioritized
                    else None
                ),
            },
        )

        return prioritized

    async def estimate_validation_timeline(
        self, strategies: List[TestStrategy]
    ) -> Dict[str, Any]:
        """
        Estimate timeline for validating assumptions.

        Args:
            strategies: List of test strategies

        Returns:
            Timeline estimation with:
            - total_days (int): Total days for all strategies
            - critical_path_days (int): Days for highest priority only
            - parallel_possible (bool): Whether tests can run in parallel
            - breakdown (List[Dict]): Per-strategy timeline
        """
        if not strategies:
            return {
                "total_days": 0,
                "critical_path_days": 0,
                "parallel_possible": False,
                "breakdown": [],
            }

        # Calculate total if run sequentially
        total_days = sum(s.estimated_effort_days for s in strategies)

        # Critical path (highest priority items)
        critical_strategies = [s for s in strategies if s.priority <= 2]
        critical_path_days = sum(s.estimated_effort_days for s in critical_strategies)

        # Check if any strategies can run in parallel
        # (simple heuristic: different methods can often run in parallel)
        methods = set(s.recommended_method for s in strategies)
        parallel_possible = len(methods) > 1

        # Build breakdown
        breakdown = [
            {
                "assumption_id": s.assumption_id,
                "priority": s.priority,
                "method": s.recommended_method,
                "days": s.estimated_effort_days,
                "cost": s.estimated_cost,
            }
            for s in strategies
        ]

        logger.info(
            "Estimated validation timeline",
            extra={
                "total_days": total_days,
                "critical_path_days": critical_path_days,
                "parallel_possible": parallel_possible,
            },
        )

        return {
            "total_days": total_days,
            "critical_path_days": critical_path_days,
            "parallel_possible": parallel_possible,
            "breakdown": breakdown,
        }

    async def recommend_validation_budget(
        self,
        strategies: List[TestStrategy],
        time_constraint: Optional[int] = None,
        budget_constraint: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Recommend validation approach given time/budget constraints.

        Args:
            strategies: List of test strategies
            time_constraint: Optional max days available
            budget_constraint: Optional max budget available

        Returns:
            Recommended approach with:
            - recommended_strategies (List[TestStrategy]): Subset to pursue
            - total_cost (float): Total cost of recommended strategies
            - total_days (int): Total days for recommended strategies
            - excluded_strategies (List[str]): Strategy IDs not recommended
            - rationale (str): Why this approach is recommended
        """
        if not strategies:
            return {
                "recommended_strategies": [],
                "total_cost": 0.0,
                "total_days": 0,
                "excluded_strategies": [],
                "rationale": "No strategies to evaluate",
            }

        # Start with all strategies, filter by constraints
        recommended = strategies.copy()
        excluded = []

        # Filter by budget
        if budget_constraint is not None:
            # Prioritize highest priority strategies within budget
            sorted_by_priority = sorted(recommended, key=lambda s: s.priority)
            recommended = []
            cumulative_cost = 0.0

            for strategy in sorted_by_priority:
                if cumulative_cost + strategy.estimated_cost <= budget_constraint:
                    recommended.append(strategy)
                    cumulative_cost += strategy.estimated_cost
                else:
                    excluded.append(strategy.assumption_id)

        # Filter by time
        if time_constraint is not None:
            # Assume parallel execution possible for different methods
            methods_used = {}
            final_recommended = []

            for strategy in sorted(recommended, key=lambda s: s.priority):
                method = strategy.recommended_method
                if method not in methods_used:
                    methods_used[method] = strategy.estimated_effort_days
                else:
                    methods_used[method] += strategy.estimated_effort_days

                # Check if adding this strategy exceeds time constraint
                max_days = max(methods_used.values())
                if max_days <= time_constraint:
                    final_recommended.append(strategy)
                else:
                    if strategy.assumption_id not in excluded:
                        excluded.append(strategy.assumption_id)

            recommended = final_recommended

        # Calculate totals
        total_cost = sum(s.estimated_cost for s in recommended)
        total_days = max(
            (s.estimated_effort_days for s in recommended), default=0
        )  # Assume parallel

        # Build rationale
        if not recommended:
            rationale = "No strategies fit within time/budget constraints"
        elif len(excluded) == 0:
            rationale = "All strategies recommended - no constraints binding"
        else:
            rationale = (
                f"Recommended {len(recommended)} highest-priority strategies "
                f"within constraints. Excluded {len(excluded)} lower-priority strategies."
            )

        logger.info(
            "Recommended validation budget",
            extra={
                "num_recommended": len(recommended),
                "num_excluded": len(excluded),
                "total_cost": total_cost,
                "total_days": total_days,
            },
        )

        return {
            "recommended_strategies": recommended,
            "total_cost": total_cost,
            "total_days": total_days,
            "excluded_strategies": excluded,
            "rationale": rationale,
        }
