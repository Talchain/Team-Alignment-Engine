"""Decision pattern learner for Phase 5 autonomous learning.

Analyzes historical decision outcomes to identify:
- Reliable causal paths that predict well
- Unreliable assumptions frequently violated
- Missing confounders that improve accuracy
"""

import logging
from typing import List, Optional, Dict, Any
from collections import defaultdict
from statistics import mean, stdev

from src.storage.outcome_repository import OutcomeRepository
from src.models.outcomes import (
    DecisionOutcomeV1,
    LearningInsightV1,
    LearningInsightsV1,
    ReliablePathV1,
    UnreliableAssumptionV1,
    MissingConfounderV1,
    GetLearningInsightsRequestV1,
    GetLearningInsightsResponseV1,
)

logger = logging.getLogger(__name__)


class DecisionPatternLearner:
    """Service for learning patterns from historical decision outcomes."""

    def __init__(self, repository: OutcomeRepository):
        """Initialize learner.

        Args:
            repository: Outcome repository for data access
        """
        self.repository = repository

    async def get_learning_insights(
        self,
        request: GetLearningInsightsRequestV1,
    ) -> GetLearningInsightsResponseV1:
        """Get learning insights from historical outcomes.

        Args:
            request: Request with filtering criteria

        Returns:
            Learning insights per archetype
        """
        logger.info(
            f"Generating learning insights (archetype: {request.archetype}, "
            f"min_sample_size: {request.min_sample_size})"
        )

        # Get all measured outcomes
        all_outcomes = await self.repository.get_all_measured_outcomes(
            min_sample_size=request.min_sample_size
        )

        if len(all_outcomes) < request.min_sample_size:
            logger.warning(
                f"Insufficient outcomes for learning: {len(all_outcomes)} < {request.min_sample_size}"
            )
            return GetLearningInsightsResponseV1(
                insights=LearningInsightsV1(insights=[]),
                total_outcomes_analyzed=len(all_outcomes),
            )

        # Group outcomes by archetype
        archetype_groups = self._group_by_archetype(all_outcomes)

        # Filter by archetype if specified
        if request.archetype:
            archetype_groups = {
                k: v for k, v in archetype_groups.items() if k == request.archetype
            }

        # Generate insights for each archetype
        insights = []
        for archetype, outcomes in archetype_groups.items():
            if len(outcomes) < request.min_sample_size:
                logger.debug(
                    f"Skipping archetype {archetype}: only {len(outcomes)} outcomes"
                )
                continue

            insight = await self._analyze_archetype(archetype, outcomes)
            insights.append(insight)

        logger.info(
            f"Generated {len(insights)} learning insights from {len(all_outcomes)} outcomes"
        )

        return GetLearningInsightsResponseV1(
            insights=LearningInsightsV1(insights=insights),
            total_outcomes_analyzed=len(all_outcomes),
        )

    def _group_by_archetype(
        self,
        outcomes: List[DecisionOutcomeV1],
    ) -> Dict[str, List[DecisionOutcomeV1]]:
        """Group outcomes by decision archetype.

        Args:
            outcomes: List of outcomes

        Returns:
            Dict mapping archetype to outcomes
        """
        groups = defaultdict(list)

        for outcome in outcomes:
            # Extract archetype from decision
            # Placeholder: in production, would use more sophisticated classification
            archetype = outcome.decision.get("archetype", "general")

            # If no archetype, try to infer from context
            if archetype == "general":
                decision_context = outcome.session_id.split("-")[0] if "-" in outcome.session_id else "general"
                archetype = decision_context

            groups[archetype].append(outcome)

        return dict(groups)

    async def _analyze_archetype(
        self,
        archetype: str,
        outcomes: List[DecisionOutcomeV1],
    ) -> LearningInsightV1:
        """Analyze outcomes for a specific archetype.

        Args:
            archetype: Decision archetype
            outcomes: Outcomes for this archetype

        Returns:
            Learning insights
        """
        logger.debug(f"Analyzing {len(outcomes)} outcomes for archetype {archetype}")

        # Identify reliable causal paths
        reliable_paths = self._identify_reliable_paths(outcomes)

        # Identify unreliable assumptions
        unreliable_assumptions = self._identify_unreliable_assumptions(outcomes)

        # Identify missing confounders
        missing_confounders = self._identify_missing_confounders(outcomes)

        return LearningInsightV1(
            archetype=archetype,
            reliable_paths=reliable_paths,
            unreliable_assumptions=unreliable_assumptions,
            missing_confounders=missing_confounders,
        )

    def _identify_reliable_paths(
        self,
        outcomes: List[DecisionOutcomeV1],
    ) -> List[ReliablePathV1]:
        """Identify causal paths that historically predict well.

        Args:
            outcomes: List of outcomes

        Returns:
            List of reliable paths
        """
        # Group outcomes by causal path structure
        path_groups = defaultdict(list)

        for outcome in outcomes:
            # Extract graph structure
            graph = outcome.decision.get("decision_graph", {})
            if not graph:
                continue

            # Create path signature (simplified - would be more sophisticated in production)
            edges = graph.get("edges", [])
            path_signature = tuple(sorted(
                (e.get("source", ""), e.get("target", ""))
                for e in edges
            ))

            path_groups[path_signature].append(outcome)

        # Calculate accuracy for each path
        reliable_paths = []
        for path_sig, path_outcomes in path_groups.items():
            if len(path_outcomes) < 3:  # Need minimum sample size
                continue

            # Calculate average prediction accuracy
            accuracies = []
            for outcome in path_outcomes:
                if not outcome.actual_outcomes:
                    continue

                # Calculate accuracy across all metrics
                for predicted in outcome.predicted_outcomes:
                    actual = next(
                        (a for a in outcome.actual_outcomes if a.metric == predicted.metric),
                        None,
                    )
                    if actual:
                        # Accuracy = 1 - |error|
                        accuracy = 1.0 - min(abs(actual.variance_from_prediction), 1.0)
                        accuracies.append(accuracy)

            if not accuracies:
                continue

            avg_accuracy = mean(accuracies)

            # Only include if accuracy is good (>70%)
            if avg_accuracy >= 0.7:
                # Reconstruct path structure
                path_structure = {
                    "edges": [
                        {"source": source, "target": target}
                        for source, target in path_sig
                    ]
                }

                reliable_paths.append(
                    ReliablePathV1(
                        path=path_structure,
                        historical_accuracy=avg_accuracy,
                        sample_size=len(path_outcomes),
                    )
                )

        # Sort by accuracy
        reliable_paths.sort(key=lambda x: x.historical_accuracy, reverse=True)

        return reliable_paths[:10]  # Return top 10

    def _identify_unreliable_assumptions(
        self,
        outcomes: List[DecisionOutcomeV1],
    ) -> List[UnreliableAssumptionV1]:
        """Identify assumptions frequently violated in practice.

        Args:
            outcomes: List of outcomes

        Returns:
            List of unreliable assumptions
        """
        # Track assumption violations
        assumption_stats = defaultdict(lambda: {"violations": 0, "total": 0, "errors": []})

        for outcome in outcomes:
            if not outcome.actual_outcomes:
                continue

            # Extract key assumptions
            key_assumptions = outcome.decision.get("key_assumptions", [])

            for assumption in key_assumptions:
                assumption_desc = assumption.get("description", "")
                if not assumption_desc:
                    continue

                assumption_stats[assumption_desc]["total"] += 1

                # Check if assumption was violated (heuristic: poor prediction accuracy)
                for predicted in outcome.predicted_outcomes:
                    actual = next(
                        (a for a in outcome.actual_outcomes if a.metric == predicted.metric),
                        None,
                    )
                    if actual:
                        error = abs(actual.variance_from_prediction)
                        assumption_stats[assumption_desc]["errors"].append(error)

                        # Violation if error > 20%
                        if error > 0.2:
                            assumption_stats[assumption_desc]["violations"] += 1

        # Identify unreliable assumptions
        unreliable = []
        for assumption_desc, stats in assumption_stats.items():
            if stats["total"] < 3:  # Need minimum sample size
                continue

            violation_rate = stats["violations"] / stats["total"]

            # Only include if violation rate is significant (>30%)
            if violation_rate >= 0.3:
                typical_variance = mean(stats["errors"]) if stats["errors"] else 0.0

                unreliable.append(
                    UnreliableAssumptionV1(
                        assumption=assumption_desc,
                        violation_rate=violation_rate,
                        typical_variance=typical_variance,
                    )
                )

        # Sort by violation rate
        unreliable.sort(key=lambda x: x.violation_rate, reverse=True)

        return unreliable[:10]  # Return top 10

    def _identify_missing_confounders(
        self,
        outcomes: List[DecisionOutcomeV1],
    ) -> List[MissingConfounderV1]:
        """Identify confounders discovered through outcome analysis.

        Args:
            outcomes: List of outcomes

        Returns:
            List of missing confounders
        """
        # This is a placeholder for more sophisticated confounder detection
        # In production, would use causal discovery algorithms

        # Track variables that correlate with prediction errors
        variable_impact = defaultdict(lambda: {"outcome_ids": [], "improvements": []})

        for outcome in outcomes:
            if not outcome.actual_outcomes:
                continue

            # Calculate overall prediction accuracy
            errors = []
            for predicted in outcome.predicted_outcomes:
                actual = next(
                    (a for a in outcome.actual_outcomes if a.metric == predicted.metric),
                    None,
                )
                if actual:
                    errors.append(abs(actual.variance_from_prediction))

            if not errors:
                continue

            avg_error = mean(errors)

            # Check for missing variables in graph
            graph = outcome.decision.get("decision_graph", {})
            nodes = graph.get("nodes", [])
            node_ids = {n.get("id", "") for n in nodes}

            # Common confounders to check (simplified)
            potential_confounders = [
                "market_conditions",
                "competitor_actions",
                "external_factors",
                "seasonal_effects",
            ]

            for confounder in potential_confounders:
                if confounder not in node_ids:
                    # This confounder is missing
                    # Heuristic: if error is high, missing this might be the cause
                    if avg_error > 0.2:
                        variable_impact[confounder]["outcome_ids"].append(str(outcome.outcome_id))
                        variable_impact[confounder]["improvements"].append(avg_error)

        # Identify significant confounders
        missing_confounders = []
        for confounder, impact in variable_impact.items():
            if len(impact["outcome_ids"]) < 3:  # Need minimum sample size
                continue

            avg_improvement = mean(impact["improvements"])

            # Only include if potential improvement is significant
            if avg_improvement >= 0.2:
                missing_confounders.append(
                    MissingConfounderV1(
                        confounder=confounder,
                        discovered_in=impact["outcome_ids"][:5],  # Limit to 5 examples
                        impact_on_accuracy=avg_improvement,
                    )
                )

        # Sort by impact
        missing_confounders.sort(key=lambda x: x.impact_on_accuracy, reverse=True)

        return missing_confounders[:5]  # Return top 5
