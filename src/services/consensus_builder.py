"""Consensus Builder service - Science-backed team decision making.

Inspired by Habermas Machine (Science 2024):
- Weights inputs by causal evidence strength, not social influence
- Prevents mediocre compromise through causal validation
- Protects minority positions with strong evidence backing
- Generates creative synthesis options rather than averaging
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import httpx

from src.models.consensus import (
    TeamInputV1,
    GraphV1,
    ConsensusRequestV1,
    ConsensusResponseV1,
    CausalQualityV1,
    ConflictAnalysisV1,
    ConflictPositionV1,
    CausalConflictV1,
    ValuesConflictV1,
    FramingConflictV1,
    SynthesisOptionV1,
    CausalGraphChangesV1,
    ConsensusWarningV1,
    QualityMetricsV1,
    TraceMetadataV1,
)
from src.models.preferences import ValueModelV1
from src.clients.isl_client import ISLClient
from src.clients.llm_client import LLMClient
from src.config import settings

logger = logging.getLogger(__name__)


class CausalQualityScorer:
    """Scores causal quality of team member inputs using ISL validation."""

    def __init__(self, isl_client: ISLClient):
        """Initialize causal quality scorer.

        Args:
            isl_client: ISL client for causal validation
        """
        self.isl_client = isl_client

    async def score_team_input(self, team_input: TeamInputV1) -> CausalQualityV1:
        """Score the causal quality of a team member's input.

        Steps:
        1. Validate graph structure with ISL
        2. Determine identification status
        3. Detect confounders and mediators
        4. Compute robustness score
        5. Collect validation issues

        Args:
            team_input: Team member's perspective with causal graph

        Returns:
            Causal quality assessment
        """
        logger.info(
            f"Scoring causal quality for user {team_input.user_id}",
            extra={"user_id": team_input.user_id, "graph_nodes": len(team_input.graph.nodes)},
        )

        # Convert GraphV1 to ISL format
        causal_graph = self._graph_to_isl_format(team_input.graph)

        # Call ISL validation
        validation_result = await self._validate_with_isl(
            causal_graph=causal_graph,
            user_id=team_input.user_id,
        )

        # Detect confounders and mediators
        has_confounders = self._detect_confounders(team_input.graph)
        has_mediators = self._detect_mediators(team_input.graph)

        # Determine identification status from ISL response
        identification_status = self._determine_identification_status(
            validation_result, has_confounders, has_mediators
        )

        # Compute robustness score
        robustness_score = self._compute_robustness_score(
            validation_result, has_confounders, has_mediators
        )

        # Collect validation issues
        validation_issues = self._collect_validation_issues(
            validation_result, team_input.graph
        )

        return CausalQualityV1(
            user_id=team_input.user_id,
            identification_status=identification_status,
            has_confounders=has_confounders,
            has_mediators=has_mediators,
            robustness_score=robustness_score,
            validation_issues=validation_issues,
        )

    def _graph_to_isl_format(self, graph: GraphV1) -> Dict[str, Any]:
        """Convert GraphV1 to ISL causal graph format.

        Args:
            graph: Team member's causal graph

        Returns:
            ISL-compatible causal graph dictionary
        """
        return {
            "nodes": graph.nodes,
            "edges": [
                {"source": edge["source"], "target": edge["target"]}
                for edge in graph.edges
            ],
        }

    async def _validate_with_isl(
        self, causal_graph: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """Call ISL to validate causal graph.

        Args:
            causal_graph: Causal graph in ISL format
            user_id: User ID for logging

        Returns:
            ISL validation result
        """
        try:
            # Create minimal option structure for ISL client
            option = {
                "option_id": f"consensus-{user_id}",
                "scenario_link": None,
                "causal_rationale": "",
            }

            # Override causal graph extraction
            original_extract = self.isl_client._extract_causal_graph
            self.isl_client._extract_causal_graph = lambda _: causal_graph

            result = await self.isl_client.validate_option(
                option=option,
                outcome_metrics=["outcome"],  # Generic outcome
                time_horizon="short_term",
            )

            # Restore original method
            self.isl_client._extract_causal_graph = original_extract

            return result

        except httpx.TimeoutException:
            logger.warning(f"ISL validation timed out for user {user_id}")
            return {
                "validation_status": "UNAVAILABLE",
                "is_identifiable": False,
                "warnings": ["ISL validation timed out"],
            }

        except Exception as e:
            logger.error(
                f"ISL validation failed for user {user_id}: {e}",
                exc_info=True,
            )
            return {
                "validation_status": "INVALID",
                "is_identifiable": False,
                "warnings": [f"Validation error: {str(e)}"],
            }

    def _detect_confounders(self, graph: GraphV1) -> bool:
        """Detect if graph has confounding variables.

        A confounder is a variable that has edges to both:
        - A decision variable (intervention)
        - An outcome variable

        For now, we detect any node with multiple outgoing edges as potential confounder.

        Args:
            graph: Causal graph

        Returns:
            True if confounders detected
        """
        # Build adjacency list
        outgoing_edges: Dict[str, List[str]] = {node: [] for node in graph.nodes}
        for edge in graph.edges:
            source = edge["source"]
            target = edge["target"]
            if source in outgoing_edges:
                outgoing_edges[source].append(target)

        # Check for nodes with multiple outgoing edges (common cause pattern)
        for node, targets in outgoing_edges.items():
            if len(targets) >= 2:
                logger.debug(f"Potential confounder detected: {node} -> {targets}")
                return True

        return False

    def _detect_mediators(self, graph: GraphV1) -> bool:
        """Detect if graph has mediating variables.

        A mediator is a variable on the causal path between decision and outcome.
        We detect chains of length >= 3 (source -> mediator -> target).

        Args:
            graph: Causal graph

        Returns:
            True if mediators detected
        """
        # Build adjacency list
        adjacency: Dict[str, List[str]] = {node: [] for node in graph.nodes}
        for edge in graph.edges:
            source = edge["source"]
            target = edge["target"]
            if source in adjacency:
                adjacency[source].append(target)

        # Find paths of length >= 3 using DFS
        def has_path_length_3(start: str, visited: Set[str], depth: int) -> bool:
            if depth >= 2:  # Path of length 3+ found (0 -> 1 -> 2)
                return True

            for neighbor in adjacency.get(start, []):
                if neighbor not in visited:
                    new_visited = visited | {neighbor}
                    if has_path_length_3(neighbor, new_visited, depth + 1):
                        return True

            return False

        for node in graph.nodes:
            if has_path_length_3(node, {node}, 0):
                logger.debug(f"Mediator path detected starting from {node}")
                return True

        return False

    def _determine_identification_status(
        self,
        validation_result: Dict[str, Any],
        has_confounders: bool,
        has_mediators: bool,
    ) -> str:
        """Determine causal identification status.

        Rules:
        - "identified": ISL confirms identifiable + no confounders
        - "partial": ISL confirms identifiable but has confounders/mediators
        - "unidentified": ISL cannot identify or validation failed

        Args:
            validation_result: ISL validation result
            has_confounders: Whether confounders detected
            has_mediators: Whether mediators detected

        Returns:
            Identification status: "identified", "partial", or "unidentified"
        """
        is_identifiable = validation_result.get("is_identifiable", False)

        if not is_identifiable:
            return "unidentified"

        if has_confounders or has_mediators:
            return "partial"

        return "identified"

    def _compute_robustness_score(
        self,
        validation_result: Dict[str, Any],
        has_confounders: bool,
        has_mediators: bool,
    ) -> float:
        """Compute robustness score for causal claim.

        Score based on:
        - Identification status (0.4 weight)
        - Absence of confounders (0.3 weight)
        - Absence of mediators (0.2 weight)
        - ISL confidence if available (0.1 weight)

        Args:
            validation_result: ISL validation result
            has_confounders: Whether confounders detected
            has_mediators: Whether mediators detected

        Returns:
            Robustness score between 0.0 and 1.0
        """
        score = 0.0

        # Identification status (0.4 weight)
        if validation_result.get("is_identifiable", False):
            score += 0.4

        # No confounders (0.3 weight)
        if not has_confounders:
            score += 0.3

        # No mediators (0.2 weight)
        if not has_mediators:
            score += 0.2

        # ISL confidence if available (0.1 weight)
        # Check for FACET score or similar confidence metric
        isl_response = validation_result.get("isl_response", {})
        confidence = isl_response.get("confidence", isl_response.get("facet_score", 0.5))
        score += 0.1 * float(confidence)

        return round(min(max(score, 0.0), 1.0), 2)

    def _collect_validation_issues(
        self, validation_result: Dict[str, Any], graph: GraphV1
    ) -> List[str]:
        """Collect validation issues from ISL response and graph analysis.

        Args:
            validation_result: ISL validation result
            graph: Causal graph

        Returns:
            List of validation issue descriptions
        """
        issues = []

        # Add ISL warnings
        isl_warnings = validation_result.get("warnings", [])
        issues.extend(isl_warnings)

        # Check for isolated nodes (no edges)
        nodes_with_edges = set()
        for edge in graph.edges:
            nodes_with_edges.add(edge["source"])
            nodes_with_edges.add(edge["target"])

        isolated_nodes = set(graph.nodes) - nodes_with_edges
        if isolated_nodes:
            issues.append(f"Isolated nodes with no edges: {', '.join(isolated_nodes)}")

        # Check for cycles (simple check)
        if self._has_cycles(graph):
            issues.append("Graph contains cycles (feedback loops)")

        return issues

    def _has_cycles(self, graph: GraphV1) -> bool:
        """Detect if graph has cycles using DFS.

        Args:
            graph: Causal graph

        Returns:
            True if cycles detected
        """
        # Build adjacency list
        adjacency: Dict[str, List[str]] = {node: [] for node in graph.nodes}
        for edge in graph.edges:
            source = edge["source"]
            target = edge["target"]
            if source in adjacency:
                adjacency[source].append(target)

        visited = set()
        rec_stack = set()

        def has_cycle_dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    if has_cycle_dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in graph.nodes:
            if node not in visited:
                if has_cycle_dfs(node):
                    return True

        return False


class ConsensusBuilder:
    """Main consensus builder service orchestrating all components."""

    def __init__(self, isl_client: ISLClient, llm_client: Optional[LLMClient] = None):
        """Initialize consensus builder.

        Args:
            isl_client: ISL client for causal validation
            llm_client: LLM client for synthesis generation (optional)

        Note:
            In production, llm_client should always be provided via dependency
            injection to ensure proper resource cleanup. The fallback is for
            testing only and may leak resources.
        """
        self.isl_client = isl_client
        self.llm_client = llm_client or LLMClient()  # Fallback for tests only
        self.quality_scorer = CausalQualityScorer(isl_client)

    async def build_consensus(
        self,
        request: ConsensusRequestV1,
        trace_id: Optional[str] = None,
        value_models: Optional[Dict[str, ValueModelV1]] = None,
    ) -> ConsensusResponseV1:
        """Build consensus from team perspectives.

        Main orchestration method that:
        1. Scores causal quality for each perspective
        2. Identifies shared goals and beliefs
        3. Classifies conflicts
        4. Protects minority positions with strong evidence
        5. Generates creative synthesis options (weighted by values if provided)
        6. Computes quality metrics

        Args:
            request: Consensus building request
            trace_id: Optional trace ID for logging
            value_models: Optional value models from preference elicitation (Phase 2A)

        Returns:
            Consensus response with synthesis options and warnings
        """
        import time
        start_time = time.time()

        if not trace_id:
            from uuid import uuid4
            trace_id = f"consensus-{uuid4()}"

        logger.info(
            f"Building consensus for {len(request.perspectives)} perspectives",
            extra={
                "trace_id": trace_id,
                "perspective_count": len(request.perspectives),
                "decision_context": request.decision_context[:100],
            },
        )

        # Step 1: Score causal quality for all perspectives
        logger.info("Step 1: Scoring causal quality for all perspectives")
        causal_qualities = await self._score_all_perspectives(request.perspectives)

        # Step 2: Identify shared goals and beliefs (TODO: implement)
        logger.info("Step 2: Identifying shared goals and beliefs")
        shared_goals, shared_beliefs = await self._identify_shared_elements(
            request.perspectives, causal_qualities
        )

        # Step 3: Classify conflicts (TODO: implement)
        logger.info("Step 3: Classifying conflicts")
        conflicts = await self._classify_conflicts(
            request.perspectives, causal_qualities
        )

        # Step 4: Generate synthesis options (TODO: implement)
        logger.info("Step 4: Generating synthesis options")
        synthesis_options = await self._generate_synthesis_options(
            request, causal_qualities, conflicts, value_models
        )

        # Step 5: Protect minority positions (TODO: implement)
        logger.info("Step 5: Checking for minority position protection")
        warnings = await self._generate_warnings(
            request, causal_qualities, conflicts
        )

        # Step 6: Compute quality metrics
        logger.info("Step 6: Computing quality metrics")
        quality_metrics = self._compute_quality_metrics(
            causal_qualities, conflicts, synthesis_options, warnings
        )

        # Build trace metadata
        processing_time_ms = (time.time() - start_time) * 1000
        trace = TraceMetadataV1(
            correlation_id=trace_id,
            processing_time_ms=round(processing_time_ms, 2),
            isl_calls=len(request.perspectives),  # One ISL call per perspective
            llm_calls=0,  # TODO: Track LLM calls
        )

        logger.info(
            f"Consensus building complete in {processing_time_ms:.2f}ms",
            extra={"trace_id": trace_id, "processing_time_ms": processing_time_ms},
        )

        return ConsensusResponseV1(
            shared_goals=shared_goals,
            shared_beliefs=shared_beliefs,
            synthesis_options=synthesis_options,
            conflicts=conflicts,
            warnings=warnings,
            quality_metrics=quality_metrics,
            trace=trace,
        )

    async def _score_all_perspectives(
        self, perspectives: List[TeamInputV1]
    ) -> Dict[str, CausalQualityV1]:
        """Score causal quality for all team perspectives.

        Args:
            perspectives: List of team member perspectives

        Returns:
            Dictionary mapping user_id to causal quality score
        """
        qualities = {}

        for perspective in perspectives:
            quality = await self.quality_scorer.score_team_input(perspective)
            qualities[perspective.user_id] = quality

        return qualities

    async def _identify_shared_elements(
        self,
        perspectives: List[TeamInputV1],
        causal_qualities: Dict[str, CausalQualityV1],
    ) -> Tuple[List[str], List[str]]:
        """Identify shared goals and causal beliefs across perspectives.

        TODO: Implement goal extraction from reasoning text and graph comparison.

        Args:
            perspectives: List of team perspectives
            causal_qualities: Causal quality scores

        Returns:
            Tuple of (shared_goals, shared_beliefs)
        """
        # Placeholder implementation
        shared_goals = []
        shared_beliefs = []

        # TODO: Extract goals from reasoning text using NLP/LLM
        # TODO: Find common edges across all graphs

        return shared_goals, shared_beliefs

    async def _classify_conflicts(
        self,
        perspectives: List[TeamInputV1],
        causal_qualities: Dict[str, CausalQualityV1],
    ) -> List[ConflictAnalysisV1]:
        """Classify conflicts between perspectives.

        Compares perspectives pairwise to identify:
        - Causal conflicts: Disagreement about causal mechanisms
        - Values conflicts: Different priorities/trade-offs
        - Framing conflicts: Same goal, different paths
        - Mixed conflicts: Combination of above

        Args:
            perspectives: List of team perspectives
            causal_qualities: Causal quality scores

        Returns:
            List of classified conflicts
        """
        conflicts = []

        # Compare perspectives pairwise
        for i in range(len(perspectives)):
            for j in range(i + 1, len(perspectives)):
                perspective_a = perspectives[i]
                perspective_b = perspectives[j]

                conflict = await self._analyze_pairwise_conflict(
                    perspective_a,
                    perspective_b,
                    causal_qualities[perspective_a.user_id],
                    causal_qualities[perspective_b.user_id],
                )

                if conflict:
                    conflicts.append(conflict)

        return conflicts

    async def _analyze_pairwise_conflict(
        self,
        perspective_a: TeamInputV1,
        perspective_b: TeamInputV1,
        quality_a: CausalQualityV1,
        quality_b: CausalQualityV1,
    ) -> Optional[ConflictAnalysisV1]:
        """Analyze conflict between two perspectives.

        Args:
            perspective_a: First perspective
            perspective_b: Second perspective
            quality_a: Causal quality of first perspective
            quality_b: Causal quality of second perspective

        Returns:
            ConflictAnalysisV1 if conflict detected, None otherwise
        """
        # Extract goals from reasoning
        goals_a = self._extract_goals(perspective_a.reasoning)
        goals_b = self._extract_goals(perspective_b.reasoning)

        # Find conflicting edges
        conflicting_edges = self._find_conflicting_edges(
            perspective_a.graph, perspective_b.graph
        )

        # Check if graphs are substantially different
        has_causal_conflict = len(conflicting_edges) > 0

        # Check if goals overlap
        shared_goals = set(goals_a) & set(goals_b)
        has_shared_goals = len(shared_goals) > 0

        # Determine conflict type
        if not has_causal_conflict and not has_shared_goals:
            # No meaningful conflict detected
            return None

        conflict_types = []
        causal_conflict_details = None
        values_conflict_details = None
        framing_conflict_details = None

        # Classify as causal conflict
        if has_causal_conflict:
            conflict_types.append("causal")
            causal_conflict_details = CausalConflictV1(
                evidence_for={
                    perspective_a.user_id: [
                        f"Claims: {edge}"
                        for edge in self._get_edges_as_strings(perspective_a.graph)
                    ],
                    perspective_b.user_id: [
                        f"Claims: {edge}"
                        for edge in self._get_edges_as_strings(perspective_b.graph)
                    ],
                },
                decisive_test=self._suggest_decisive_test(conflicting_edges),
            )

        # Classify as values conflict (same goals, different priorities)
        if has_shared_goals and not has_causal_conflict:
            conflict_types.append("values")
            all_goals = set(goals_a) | set(goals_b)
            unique_goals_a = set(goals_a) - set(goals_b)
            unique_goals_b = set(goals_b) - set(goals_a)

            values_conflict_details = ValuesConflictV1(
                trade_off_dimensions=list(unique_goals_a | unique_goals_b),
                pareto_options=[
                    f"Option favoring {perspective_a.user_id}: {', '.join(goals_a)}",
                    f"Option favoring {perspective_b.user_id}: {', '.join(goals_b)}",
                ],
            )

        # Classify as framing conflict (same goal, different paths)
        if has_shared_goals and has_causal_conflict:
            # This is both framing and causal - will be classified as "mixed"
            conflict_types.append("framing")
            framing_conflict_details = FramingConflictV1(
                shared_goal=list(shared_goals)[0] if shared_goals else "Unknown",
                alternative_paths=[
                    f"{perspective_a.user_id}: {perspective_a.reasoning[:100]}...",
                    f"{perspective_b.user_id}: {perspective_b.reasoning[:100]}...",
                ],
            )

        # Determine final conflict type
        if len(conflict_types) == 0:
            return None
        elif len(conflict_types) == 1:
            conflict_type = conflict_types[0]
        else:
            conflict_type = "mixed"

        # Build conflict positions
        positions = [
            ConflictPositionV1(
                user_id=perspective_a.user_id,
                position=perspective_a.reasoning[:200],
                causal_backing=quality_a,
            ),
            ConflictPositionV1(
                user_id=perspective_b.user_id,
                position=perspective_b.reasoning[:200],
                causal_backing=quality_b,
            ),
        ]

        return ConflictAnalysisV1(
            conflict_type=conflict_type,
            positions=positions,
            causal_conflict=causal_conflict_details,
            values_conflict=values_conflict_details,
            framing_conflict=framing_conflict_details,
        )

    def _extract_goals(self, reasoning: str) -> List[str]:
        """Extract goals from reasoning text.

        Simple keyword-based extraction. In production, use NLP/LLM.

        Args:
            reasoning: Natural language reasoning

        Returns:
            List of extracted goal keywords
        """
        goals = []

        # Common goal keywords
        goal_keywords = [
            "revenue",
            "profit",
            "growth",
            "retention",
            "churn",
            "quality",
            "speed",
            "cost",
            "satisfaction",
            "engagement",
            "efficiency",
            "scale",
        ]

        reasoning_lower = reasoning.lower()
        for keyword in goal_keywords:
            if keyword in reasoning_lower:
                goals.append(keyword)

        return goals

    def _find_conflicting_edges(
        self, graph_a: GraphV1, graph_b: GraphV1
    ) -> List[Tuple[str, str, str]]:
        """Find conflicting edges between two graphs.

        Conflicting edges are:
        1. Different targets for same source
        2. Same edge with opposite direction
        3. One graph has edge, other explicitly contradicts

        Args:
            graph_a: First causal graph
            graph_b: Second causal graph

        Returns:
            List of (source, target, conflict_type) tuples
        """
        conflicts = []

        # Build edge sets
        edges_a = {(edge["source"], edge["target"]) for edge in graph_a.edges}
        edges_b = {(edge["source"], edge["target"]) for edge in graph_b.edges}

        # Check for opposite direction edges
        for source, target in edges_a:
            if (target, source) in edges_b:
                conflicts.append((source, target, "opposite_direction"))

        # Check for different targets with same source
        sources_a = {}
        for edge in graph_a.edges:
            source = edge["source"]
            if source not in sources_a:
                sources_a[source] = []
            sources_a[source].append(edge["target"])

        sources_b = {}
        for edge in graph_b.edges:
            source = edge["source"]
            if source not in sources_b:
                sources_b[source] = []
            sources_b[source].append(edge["target"])

        for source in set(sources_a.keys()) & set(sources_b.keys()):
            targets_a = set(sources_a[source])
            targets_b = set(sources_b[source])

            # If same source points to different targets, it's a conflict
            if targets_a != targets_b:
                for target_a in targets_a - targets_b:
                    conflicts.append((source, target_a, "different_targets"))
                for target_b in targets_b - targets_a:
                    conflicts.append((source, target_b, "different_targets"))

        return conflicts

    def _get_edges_as_strings(self, graph: GraphV1) -> List[str]:
        """Convert graph edges to human-readable strings.

        Args:
            graph: Causal graph

        Returns:
            List of edge descriptions
        """
        return [f"{edge['source']} → {edge['target']}" for edge in graph.edges]

    def _suggest_decisive_test(
        self, conflicting_edges: List[Tuple[str, str, str]]
    ) -> Optional[str]:
        """Suggest a decisive test to resolve causal conflict.

        Args:
            conflicting_edges: List of conflicting edges

        Returns:
            Suggested test description
        """
        if not conflicting_edges:
            return None

        # Take first conflict as example
        source, target, conflict_type = conflicting_edges[0]

        if conflict_type == "opposite_direction":
            return f"Run intervention study: does {source} cause {target}, or vice versa?"
        elif conflict_type == "different_targets":
            return f"Measure effect of {source} on outcomes to determine true causal targets"
        else:
            return f"Collect data to validate causal relationship: {source} → {target}"

    async def _generate_synthesis_options(
        self,
        request: ConsensusRequestV1,
        causal_qualities: Dict[str, CausalQualityV1],
        conflicts: List[ConflictAnalysisV1],
        value_models: Optional[Dict[str, ValueModelV1]] = None,
    ) -> List[SynthesisOptionV1]:
        """Generate creative synthesis options using LLM orchestration.

        Steps:
        1. Format perspectives and conflicts for LLM
        2. Compute value alignment scores if value models provided (Phase 2A integration)
        3. Call LLM to generate creative options (weighted by values)
        4. Compute Pareto efficiency scores
        5. Compute creative scores (novelty vs. averaging)
        6. Build SynthesisOptionV1 objects

        Args:
            request: Original consensus request
            causal_qualities: Causal quality scores
            conflicts: Identified conflicts
            value_models: Optional value models from preference elicitation

        Returns:
            List of synthesis options
        """
        if not request.require_creative_synthesis:
            return []

        logger.info("Generating creative synthesis options via LLM")

        # Format perspectives for LLM (with optional value weighting)
        perspective_dicts = []
        for perspective in request.perspectives:
            quality = causal_qualities.get(perspective.user_id)

            # Compute value alignment weight (Phase 2A integration)
            value_weight = 1.0
            if value_models and perspective.user_id in value_models:
                value_weight = self._compute_value_weight(
                    value_models[perspective.user_id],
                    request.decision_context
                )

            perspective_dicts.append({
                "user_id": perspective.user_id,
                "reasoning": perspective.reasoning,
                "graph_summary": self._summarize_graph(perspective.graph),
                "quality_score": quality.robustness_score if quality else 0.0,
                "value_weight": value_weight,
            })

        # Log value weighting if used
        if value_models:
            logger.info(
                f"Value-weighted synthesis enabled for {len(value_models)} users",
                extra={"value_model_count": len(value_models)}
            )

        # Format conflicts for LLM
        conflict_dicts = []
        for conflict in conflicts:
            conflict_dicts.append({
                "type": conflict.conflict_type,
                "description": self._summarize_conflict(conflict),
            })

        # Call LLM to generate synthesis options
        llm_options = await self.llm_client.generate_synthesis_options(
            decision_context=request.decision_context,
            perspectives=perspective_dicts,
            conflicts=conflict_dicts,
            num_options=3,
        )

        # Convert LLM options to SynthesisOptionV1 objects
        synthesis_options = []
        for llm_option in llm_options:
            synthesis_option = await self._build_synthesis_option(
                llm_option, request, causal_qualities
            )
            if synthesis_option:
                synthesis_options.append(synthesis_option)

        logger.info(f"Generated {len(synthesis_options)} synthesis options")

        return synthesis_options

    def _summarize_graph(self, graph: GraphV1) -> str:
        """Summarize causal graph for LLM.

        Args:
            graph: Causal graph

        Returns:
            Human-readable graph summary
        """
        if not graph.edges:
            return f"{len(graph.nodes)} nodes, no edges"

        edge_strs = [f"{e['source']} → {e['target']}" for e in graph.edges]
        return f"{len(graph.nodes)} nodes, edges: {', '.join(edge_strs[:5])}"

    def _summarize_conflict(self, conflict: ConflictAnalysisV1) -> str:
        """Summarize conflict for LLM.

        Args:
            conflict: Conflict analysis

        Returns:
            Human-readable conflict summary
        """
        if len(conflict.positions) < 2:
            return f"{conflict.conflict_type} conflict"

        pos1 = conflict.positions[0]
        pos2 = conflict.positions[1]

        return (
            f"{conflict.conflict_type} conflict between {pos1.user_id} "
            f"(quality: {pos1.causal_backing.robustness_score:.2f}) and "
            f"{pos2.user_id} (quality: {pos2.causal_backing.robustness_score:.2f})"
        )

    async def _build_synthesis_option(
        self,
        llm_option: Dict[str, Any],
        request: ConsensusRequestV1,
        causal_qualities: Dict[str, CausalQualityV1],
    ) -> Optional[SynthesisOptionV1]:
        """Build SynthesisOptionV1 from LLM output.

        Args:
            llm_option: Raw LLM-generated option
            request: Original request
            causal_qualities: Causal quality scores

        Returns:
            SynthesisOptionV1 or None if invalid
        """
        try:
            # Extract fields from LLM response
            description = llm_option.get("description", "")
            causal_mechanism = llm_option.get("causal_mechanism", "")
            satisfies_constraints = llm_option.get("satisfies_constraints", [])
            nodes_added = llm_option.get("nodes_added", [])
            edges_added = llm_option.get("edges_added", [])
            mediators_introduced = llm_option.get("mediators_introduced", [])

            # Compute Pareto efficiency score
            pareto_efficiency = self._compute_pareto_efficiency(
                satisfies_constraints, len(request.perspectives)
            )

            # Compute creative score (novelty vs. averaging)
            creative_score = self._compute_creative_score(
                nodes_added, edges_added, request.perspectives
            )

            # Build causal graph changes
            causal_graph_changes = CausalGraphChangesV1(
                nodes_added=nodes_added,
                edges_added=edges_added,
                mediators_introduced=mediators_introduced,
            )

            return SynthesisOptionV1(
                description=description,
                causal_mechanism=causal_mechanism,
                satisfies_constraints=satisfies_constraints,
                pareto_efficiency=pareto_efficiency,
                creative_score=creative_score,
                causal_graph_changes=causal_graph_changes,
            )

        except Exception as e:
            logger.error(f"Failed to build synthesis option: {e}", exc_info=True)
            return None

    def _compute_pareto_efficiency(
        self, satisfies_constraints: List[str], total_perspectives: int
    ) -> float:
        """Compute Pareto efficiency score.

        Score based on percentage of stakeholder constraints satisfied.

        Args:
            satisfies_constraints: List of user_ids whose constraints are met
            total_perspectives: Total number of perspectives

        Returns:
            Pareto efficiency score (0.0 - 1.0)
        """
        if total_perspectives == 0:
            return 0.0

        # Base score: percentage of stakeholders satisfied
        base_score = len(satisfies_constraints) / total_perspectives

        # Bonus for satisfying majority (>50%)
        majority_bonus = 0.2 if len(satisfies_constraints) > total_perspectives / 2 else 0.0

        # Bonus for satisfying all stakeholders
        unanimity_bonus = 0.1 if len(satisfies_constraints) == total_perspectives else 0.0

        score = base_score + majority_bonus + unanimity_bonus

        return round(min(score, 1.0), 2)

    def _compute_creative_score(
        self,
        nodes_added: List[str],
        edges_added: List[str],
        perspectives: List[TeamInputV1],
    ) -> float:
        """Compute creative score (novelty vs. simple averaging).

        Score based on:
        - Number of new nodes introduced (0.4 weight)
        - Number of new edges introduced (0.4 weight)
        - Complexity of causal mechanism (0.2 weight)

        Args:
            nodes_added: New nodes introduced
            edges_added: New edges introduced
            perspectives: Original team perspectives

        Returns:
            Creative score (0.0 - 1.0)
        """
        # Count existing nodes/edges across all perspectives
        all_existing_nodes = set()
        all_existing_edges = set()

        for perspective in perspectives:
            all_existing_nodes.update(perspective.graph.nodes)
            for edge in perspective.graph.edges:
                all_existing_edges.add((edge["source"], edge["target"]))

        # Check how many added nodes/edges are truly novel
        novel_nodes = [n for n in nodes_added if n not in all_existing_nodes]
        novel_edges_count = 0
        for edge_str in edges_added:
            # Parse "A → B" format
            if "→" in edge_str:
                parts = edge_str.split("→")
                if len(parts) == 2:
                    source = parts[0].strip()
                    target = parts[1].strip()
                    if (source, target) not in all_existing_edges:
                        novel_edges_count += 1

        # Compute score components
        node_score = min(len(novel_nodes) / 3.0, 1.0) * 0.4  # Cap at 3 new nodes
        edge_score = min(novel_edges_count / 3.0, 1.0) * 0.4  # Cap at 3 new edges
        complexity_score = min(len(edges_added) / 5.0, 1.0) * 0.2  # Cap at 5 total edges

        creative_score = node_score + edge_score + complexity_score

        # If no new nodes/edges, score is very low (simple averaging)
        if len(novel_nodes) == 0 and novel_edges_count == 0:
            creative_score = 0.1

        return round(min(max(creative_score, 0.0), 1.0), 2)

    def _compute_value_weight(
        self,
        value_model: ValueModelV1,
        decision_context: str,
    ) -> float:
        """Compute value alignment weight from user's value model.

        Uses the value model from Phase 2A (ActiVA preference elicitation)
        to weight this user's perspective in synthesis generation.

        Higher weight when:
        - High convergence score (confident value model)
        - Value dimensions are well-defined
        - Model based on sufficient questions

        Args:
            value_model: User's value model from preference elicitation
            decision_context: Decision context for alignment check

        Returns:
            Value weight (0.5 - 1.5) to apply to this user's perspective
        """
        # Base weight starts at 1.0 (neutral)
        weight = 1.0

        # Factor 1: Convergence score (±0.3)
        # High convergence = more confident value model
        convergence_bonus = (value_model.convergence_score - 0.5) * 0.6
        weight += convergence_bonus

        # Factor 2: Questions asked (±0.2)
        # More questions = better calibrated model
        # Penalize if too few questions (<3), bonus if many (>5)
        if value_model.questions_asked < 3:
            weight -= 0.2
        elif value_model.questions_asked >= 5:
            weight += 0.2

        # Factor 3: Value dimension balance (±0.1)
        # Prefer balanced value models over extreme single-dimension focus
        if len(value_model.dimensions) > 0:
            weights_list = [d.weight for d in value_model.dimensions]
            max_weight = max(weights_list)
            # If one dimension dominates (>0.7), slight penalty
            if max_weight > 0.7:
                weight -= 0.1

        # Clamp to reasonable range [0.5, 1.5]
        return round(min(max(weight, 0.5), 1.5), 2)

    async def _generate_warnings(
        self,
        request: ConsensusRequestV1,
        causal_qualities: Dict[str, CausalQualityV1],
        conflicts: List[ConflictAnalysisV1],
    ) -> List[ConsensusWarningV1]:
        """Generate warnings about consensus quality.

        Detects:
        - Minority positions with superior causal backing
        - Forced compromise (no synthesis options found)
        - Weak causal backing across all perspectives

        Args:
            request: Original consensus request
            causal_qualities: Causal quality scores
            conflicts: Identified conflicts

        Returns:
            List of consensus warnings
        """
        warnings = []

        # Check for minority positions with strong evidence
        if request.protect_minority_evidence:
            minority_warnings = self._detect_minority_strong_evidence(
                request.perspectives, causal_qualities
            )
            warnings.extend(minority_warnings)

        # Check for weak causal backing
        weak_backing_warnings = self._detect_weak_causal_backing(
            causal_qualities, request.min_causal_quality
        )
        warnings.extend(weak_backing_warnings)

        # Check for forced compromise (if conflicts exist but no synthesis)
        # This will be checked after synthesis options are generated
        # For now, we can detect unresolved conflicts
        if len(conflicts) > 0:
            forced_compromise_warnings = self._detect_forced_compromise(conflicts)
            warnings.extend(forced_compromise_warnings)

        return warnings

    def _detect_minority_strong_evidence(
        self,
        perspectives: List[TeamInputV1],
        causal_qualities: Dict[str, CausalQualityV1],
    ) -> List[ConsensusWarningV1]:
        """Detect minority positions with superior causal evidence.

        Warns when a single person (or small minority) has significantly
        better causal backing than the majority.

        Args:
            perspectives: Team perspectives
            causal_qualities: Causal quality scores

        Returns:
            List of minority evidence warnings
        """
        warnings = []

        if len(perspectives) < 3:
            # Need at least 3 perspectives to identify minority
            return warnings

        # Calculate average robustness score
        scores = [quality.robustness_score for quality in causal_qualities.values()]
        avg_score = sum(scores) / len(scores)

        # Identify high-quality outliers (score > avg + 0.3)
        threshold = avg_score + 0.3
        high_quality_positions = []

        for user_id, quality in causal_qualities.items():
            if quality.robustness_score >= threshold:
                high_quality_positions.append((user_id, quality))

        # Check if high-quality positions are in minority
        minority_threshold = len(perspectives) / 3  # Less than 1/3 is minority

        for user_id, quality in high_quality_positions:
            # Count how many others share similar position
            # (For now, assume each position is unique - in production, cluster by graph similarity)
            supporters = 1

            if supporters <= minority_threshold:
                # This is a minority position with strong evidence
                other_users = [uid for uid in causal_qualities.keys() if uid != user_id]

                warnings.append(
                    ConsensusWarningV1(
                        warning_type="minority_has_strong_evidence",
                        severity="warning",
                        message=(
                            f"{user_id}'s position has superior causal backing "
                            f"({quality.robustness_score:.2f} vs. avg {avg_score:.2f})"
                        ),
                        affected_positions=other_users,
                        recommendation=f"Review evidence from {user_id} before proceeding",
                    )
                )

        return warnings

    def _detect_weak_causal_backing(
        self,
        causal_qualities: Dict[str, CausalQualityV1],
        min_quality: str,
    ) -> List[ConsensusWarningV1]:
        """Detect perspectives with weak causal backing.

        Args:
            causal_qualities: Causal quality scores
            min_quality: Minimum quality threshold from request

        Returns:
            List of weak backing warnings
        """
        warnings = []

        # Map quality levels to thresholds
        quality_thresholds = {
            "identified": 0.7,
            "partial": 0.4,
            "any": 0.0,
        }

        threshold = quality_thresholds.get(min_quality, 0.4)

        # Find perspectives below threshold
        weak_positions = []
        for user_id, quality in causal_qualities.items():
            if quality.robustness_score < threshold:
                weak_positions.append(user_id)

        if len(weak_positions) > 0:
            warnings.append(
                ConsensusWarningV1(
                    warning_type="weak_causal_backing",
                    severity="info" if len(weak_positions) < len(causal_qualities) / 2 else "warning",
                    message=(
                        f"{len(weak_positions)} perspective(s) have weak causal backing "
                        f"(robustness < {threshold:.2f})"
                    ),
                    affected_positions=weak_positions,
                    recommendation="Consider requesting additional evidence or causal reasoning",
                )
            )

        return warnings

    def _detect_forced_compromise(
        self, conflicts: List[ConflictAnalysisV1]
    ) -> List[ConsensusWarningV1]:
        """Detect forced compromise situations.

        A forced compromise occurs when there are conflicts but no creative
        synthesis options are found (checked after synthesis generation).

        Args:
            conflicts: Identified conflicts

        Returns:
            List of forced compromise warnings
        """
        warnings = []

        # Check for conflicts with low causal backing on both sides
        for conflict in conflicts:
            if len(conflict.positions) < 2:
                continue

            # Check if both positions have weak causal backing
            scores = [pos.causal_backing.robustness_score for pos in conflict.positions]
            avg_conflict_score = sum(scores) / len(scores)

            if avg_conflict_score < 0.5:
                warnings.append(
                    ConsensusWarningV1(
                        warning_type="forced_compromise",
                        severity="warning",
                        message=(
                            f"Conflict between {conflict.positions[0].user_id} and "
                            f"{conflict.positions[1].user_id} has weak causal backing on both sides "
                            f"(avg {avg_conflict_score:.2f})"
                        ),
                        affected_positions=[pos.user_id for pos in conflict.positions],
                        recommendation="Seek additional causal evidence before resolving this conflict",
                    )
                )

        return warnings

    def _compute_quality_metrics(
        self,
        causal_qualities: Dict[str, CausalQualityV1],
        conflicts: List[ConflictAnalysisV1],
        synthesis_options: List[SynthesisOptionV1],
        warnings: List[ConsensusWarningV1],
    ) -> QualityMetricsV1:
        """Compute quality metrics for consensus process.

        Args:
            causal_qualities: Causal quality scores
            conflicts: Identified conflicts
            synthesis_options: Generated synthesis options
            warnings: Generated warnings

        Returns:
            Quality metrics
        """
        # Check if all perspectives passed causal validation
        causal_validation_passed = all(
            quality.identification_status != "unidentified"
            for quality in causal_qualities.values()
        )

        # Check if minority positions were examined
        minority_positions_examined = any(
            warning.warning_type == "minority_has_strong_evidence"
            for warning in warnings
        )

        # Check if creative synthesis was attempted
        creative_synthesis_attempted = len(synthesis_options) > 0

        # Check if forced compromise was detected
        forced_compromise_detected = any(
            warning.warning_type == "forced_compromise"
            for warning in warnings
        )

        return QualityMetricsV1(
            causal_validation_passed=causal_validation_passed,
            minority_positions_examined=minority_positions_examined,
            creative_synthesis_attempted=creative_synthesis_attempted,
            forced_compromise_detected=forced_compromise_detected,
        )
