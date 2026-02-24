"""Causal modelling agent for Phase 5 autonomous learning.

Generates graph refinement suggestions based on:
- Historical learning insights
- Similar decision patterns
- Causal theory
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import uuid4

from src.storage.outcome_repository import OutcomeRepository
from src.services.decision_pattern_learner import DecisionPatternLearner
from src.clients.isl_client import ISLClient
from src.models.outcomes import (
    RefinementSuggestionV1,
    RefinementSuggestionsV1,
    RefinementEvidenceV1,
    ProposedChangeV1,
    GraphDeltaV1,
    ExpectedImpactV1,
    AnalyzeGraphRequestV1,
    AnalyzeGraphResponseV1,
    ApplySuggestionsRequestV1,
    ApplySuggestionsResponseV1,
    LearningInsightsV1,
    GetLearningInsightsRequestV1,
)
from src.models.consensus import GraphV1, NodeV1, EdgeV1

logger = logging.getLogger(__name__)


class CausalModellingAgent:
    """Agent for analyzing graphs and suggesting refinements."""

    def __init__(
        self,
        repository: OutcomeRepository,
        pattern_learner: DecisionPatternLearner,
        isl_client: ISLClient,
    ):
        """Initialize agent.

        Args:
            repository: Outcome repository for data access
            pattern_learner: Pattern learner for historical insights
            isl_client: ISL client for causal validation
        """
        self.repository = repository
        self.pattern_learner = pattern_learner
        self.isl_client = isl_client

    async def analyze_graph(
        self,
        request: AnalyzeGraphRequestV1,
    ) -> AnalyzeGraphResponseV1:
        """Analyze graph and suggest refinements.

        Args:
            request: Graph analysis request

        Returns:
            Analysis with refinement suggestions
        """
        logger.info(f"Analyzing graph for session {request.session_id}")

        suggestions = []
        learning_insights = LearningInsightsV1(insights=[])

        # Get learning insights if requested
        if request.include_learning:
            learning_response = await self.pattern_learner.get_learning_insights(
                GetLearningInsightsRequestV1(
                    archetype=None,  # All archetypes
                    min_sample_size=3,
                )
            )
            learning_insights = learning_response.insights

        # Generate suggestions from learning insights
        for insight in learning_insights.insights:
            # Add missing reliable paths
            for reliable_path in insight.reliable_paths:
                suggestion = self._suggest_add_reliable_path(
                    request.graph,
                    reliable_path.path,
                    reliable_path.historical_accuracy,
                    reliable_path.sample_size,
                )
                if suggestion and suggestion.evidence.confidence >= request.confidence_threshold:
                    suggestions.append(suggestion)

            # Suggest removing edges for unreliable assumptions
            for unreliable in insight.unreliable_assumptions:
                suggestion = self._suggest_remove_unreliable_assumption(
                    request.graph,
                    unreliable.assumption,
                    unreliable.violation_rate,
                )
                if suggestion and suggestion.evidence.confidence >= request.confidence_threshold:
                    suggestions.append(suggestion)

            # Add missing confounders
            for confounder in insight.missing_confounders:
                suggestion = self._suggest_add_confounder(
                    request.graph,
                    confounder.confounder,
                    confounder.impact_on_accuracy,
                    len(confounder.discovered_in),
                )
                if suggestion and suggestion.evidence.confidence >= request.confidence_threshold:
                    suggestions.append(suggestion)

        # Find similar historical decisions
        similar_decisions = await self._find_similar_decisions(request.graph)

        # Create refinement suggestions summary
        refinement_suggestions = RefinementSuggestionsV1(
            session_id=request.session_id,
            current_graph=request.graph,
            suggestions=suggestions,
            summary={
                "high_confidence": sum(1 for s in suggestions if s.evidence.confidence >= 0.8),
                "medium_confidence": sum(1 for s in suggestions if 0.6 <= s.evidence.confidence < 0.8),
                "auto_applicable": sum(1 for s in suggestions if s.auto_apply),
            },
        )

        logger.info(
            f"Generated {len(suggestions)} refinement suggestions for session {request.session_id}"
        )

        return AnalyzeGraphResponseV1(
            refinement_suggestions=refinement_suggestions,
            learning_insights=learning_insights,
            similar_decisions=similar_decisions,
        )

    async def apply_suggestions(
        self,
        request: ApplySuggestionsRequestV1,
    ) -> ApplySuggestionsResponseV1:
        """Apply refinement suggestions to a graph.

        Args:
            request: Request to apply suggestions

        Returns:
            Refined graph and validation results
        """
        logger.info(
            f"Applying {len(request.suggestion_ids)} suggestions to session {request.session_id}"
        )

        if not request.user_approved:
            raise ValueError("User approval required to apply suggestions")

        # This is a placeholder - in production, would:
        # 1. Load current graph from session
        # 2. Load suggestions by ID
        # 3. Apply graph deltas
        # 4. Validate with ISL
        # 5. Return refined graph

        # For now, return a placeholder response
        from src.models.consensus import GraphV1

        refined_graph = GraphV1(
            nodes=[],
            edges=[],
        )

        applied_suggestions = []

        validation_result = {
            "valid": True,
            "warnings": [],
        }

        logger.info(f"Applied {len(applied_suggestions)} suggestions successfully")

        return ApplySuggestionsResponseV1(
            refined_graph=refined_graph,
            applied_suggestions=applied_suggestions,
            validation_result=validation_result,
        )

    def _suggest_add_reliable_path(
        self,
        current_graph: GraphV1,
        reliable_path: Dict[str, Any],
        accuracy: float,
        sample_size: int,
    ) -> Optional[RefinementSuggestionV1]:
        """Suggest adding a reliable causal path.

        Args:
            current_graph: Current graph structure
            reliable_path: Reliable path structure
            accuracy: Historical accuracy
            sample_size: Number of historical observations

        Returns:
            Refinement suggestion or None
        """
        # Extract edges from reliable path
        path_edges = reliable_path.get("edges", [])
        if not path_edges:
            return None

        # Check if edges already exist in graph
        current_edge_pairs = {
            (e.source, e.target) for e in current_graph.edges
        }

        missing_edges = [
            e for e in path_edges
            if (e.get("source"), e.get("target")) not in current_edge_pairs
        ]

        if not missing_edges:
            return None

        # Create suggestion to add missing edges
        edges_to_add = [
            {
                "source": e.get("source", ""),
                "target": e.get("target", ""),
                "mechanism": "historical_pattern",
            }
            for e in missing_edges
        ]

        graph_delta = GraphDeltaV1(
            nodes_added=None,
            edges_added=edges_to_add,
            edges_removed=None,
        )

        proposed_change = ProposedChangeV1(
            action=f"Add {len(edges_to_add)} causal edges from historically reliable path",
            graph_delta=graph_delta,
        )

        evidence = RefinementEvidenceV1(
            source="historical_learning",
            details=f"This causal path has {accuracy:.1%} accuracy across {sample_size} historical decisions",
            confidence=min(accuracy, 0.95),  # Cap at 0.95
        )

        expected_impact = ExpectedImpactV1(
            prediction_accuracy_improvement=(accuracy - 0.5) * 20,  # Rough heuristic
            causal_validity_improvement=10.0,
        )

        return RefinementSuggestionV1(
            suggestion_id=str(uuid4()),
            suggestion_type="add_edge",
            rationale=f"Historical data shows this causal path predicts outcomes well ({accuracy:.1%} accuracy)",
            evidence=evidence,
            proposed_change=proposed_change,
            expected_impact=expected_impact,
            auto_apply=accuracy >= 0.85 and sample_size >= 10,
            requires_user_approval=True,
        )

    def _suggest_remove_unreliable_assumption(
        self,
        current_graph: GraphV1,
        assumption: str,
        violation_rate: float,
    ) -> Optional[RefinementSuggestionV1]:
        """Suggest removing edges based on unreliable assumptions.

        Args:
            current_graph: Current graph structure
            assumption: Assumption description
            violation_rate: How often violated

        Returns:
            Refinement suggestion or None
        """
        # This is simplified - would need more sophisticated matching in production
        # For now, just flag high violation rate without specific edge removal

        if violation_rate < 0.4:  # Only suggest if violation rate is high
            return None

        evidence = RefinementEvidenceV1(
            source="historical_learning",
            details=f"This assumption was violated in {violation_rate:.1%} of historical cases",
            confidence=min(violation_rate, 0.9),
        )

        # Don't provide specific edges to remove - require user review
        graph_delta = GraphDeltaV1(
            nodes_added=None,
            edges_added=None,
            edges_removed=None,
        )

        proposed_change = ProposedChangeV1(
            action=f"Review edges relying on assumption: {assumption[:100]}...",
            graph_delta=graph_delta,
        )

        expected_impact = ExpectedImpactV1(
            prediction_accuracy_improvement=violation_rate * 15,
            causal_validity_improvement=violation_rate * 20,
        )

        return RefinementSuggestionV1(
            suggestion_id=str(uuid4()),
            suggestion_type="remove_edge",
            rationale=f"This assumption frequently doesn't hold ({violation_rate:.1%} violation rate)",
            evidence=evidence,
            proposed_change=proposed_change,
            expected_impact=expected_impact,
            auto_apply=False,  # Never auto-remove
            requires_user_approval=True,
        )

    def _suggest_add_confounder(
        self,
        current_graph: GraphV1,
        confounder: str,
        impact: float,
        sample_size: int,
    ) -> Optional[RefinementSuggestionV1]:
        """Suggest adding a missing confounder.

        Args:
            current_graph: Current graph structure
            confounder: Confounder variable name
            impact: Impact on accuracy
            sample_size: Number of cases where discovered

        Returns:
            Refinement suggestion or None
        """
        # Check if confounder already exists
        existing_nodes = {n.id for n in current_graph.nodes}
        if confounder in existing_nodes:
            return None

        # Create suggestion to add confounder node
        nodes_to_add = [
            {
                "id": confounder,
                "label": confounder.replace("_", " ").title(),
                "type": "confounder",
            }
        ]

        graph_delta = GraphDeltaV1(
            nodes_added=nodes_to_add,
            edges_added=None,
            edges_removed=None,
        )

        proposed_change = ProposedChangeV1(
            action=f"Add confounder node: {confounder.replace('_', ' ').title()}",
            graph_delta=graph_delta,
        )

        evidence = RefinementEvidenceV1(
            source="historical_learning",
            details=f"Missing this variable correlated with {impact:.1%} prediction errors in {sample_size} cases",
            confidence=min(impact / 0.3, 0.85),  # Scale confidence
        )

        expected_impact = ExpectedImpactV1(
            prediction_accuracy_improvement=impact * 100,  # Convert to percentage points
            causal_validity_improvement=impact * 50,
        )

        return RefinementSuggestionV1(
            suggestion_id=str(uuid4()),
            suggestion_type="add_confounder",
            rationale=f"Historical analysis suggests {confounder} is a missing confounder",
            evidence=evidence,
            proposed_change=proposed_change,
            expected_impact=expected_impact,
            auto_apply=False,  # Require user review for confounders
            requires_user_approval=True,
        )

    async def _find_similar_decisions(
        self,
        graph: GraphV1,
    ) -> List[Any]:
        """Find similar historical decisions.

        Args:
            graph: Current graph

        Returns:
            List of similar decision outcomes
        """
        # Placeholder - would implement graph similarity matching in production
        # For now, return empty list
        return []
