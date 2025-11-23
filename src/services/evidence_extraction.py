"""Evidence extraction and linking service.

Extracts causal claims from reasoning text and links to graph paths.
"""

import logging
import re
from typing import List, Dict, Optional, Tuple

from src.models.consensus import TeamInputV1, GraphV1
from src.models.deliberation import (
    EvidenceItemV1,
    UnsupportedClaimWarningV1,
    CausalPathV1,
)
from src.clients.isl_client import ISLClient

logger = logging.getLogger(__name__)


class EvidenceExtractionService:
    """Service for extracting and validating evidence from reasoning."""

    def __init__(self, isl_client: Optional[ISLClient] = None):
        """Initialize evidence extraction service.

        Args:
            isl_client: ISL client for validation
        """
        self.isl_client = isl_client or ISLClient()

        # Common causal language patterns
        self.causal_patterns = [
            r"(\w+)\s+(?:causes?|leads? to|results? in|increases?|decreases?)\s+(\w+)",
            r"if\s+(\w+)\s+then\s+(\w+)",
            r"(\w+)\s+→\s+(\w+)",
            r"(\w+)\s+affects?\s+(\w+)",
            r"due to\s+(\w+),\s+(\w+)",
        ]

    async def extract_evidence_items(
        self,
        team_input: TeamInputV1,
        round_id: str,
    ) -> Tuple[List[EvidenceItemV1], List[UnsupportedClaimWarningV1]]:
        """Extract evidence items from team input.

        Args:
            team_input: Team member's input
            round_id: Round ID

        Returns:
            Tuple of (evidence_items, warnings)
        """
        logger.info(f"Extracting evidence from {team_input.user_id}'s reasoning")

        evidence_items = []
        warnings = []

        # Extract causal claims from reasoning
        claims = self._extract_causal_claims(team_input.reasoning)

        for claim_text, source_node, target_node in claims:
            # Find causal path in graph
            path = self._find_causal_path(team_input.graph, source_node, target_node)

            if not path:
                # No path found - unsupported claim
                warnings.append(
                    UnsupportedClaimWarningV1(
                        claim=claim_text,
                        user_id=team_input.user_id,
                        issue="no_causal_path",
                        suggestion=f"Add causal edge: {source_node} → {target_node}",
                    )
                )
                continue

            # Validate path with ISL (simplified)
            try:
                validation = await self.isl_client.validate_option(
                    option={
                        "option_id": "evidence-check",
                        "causal_rationale": claim_text,
                    },
                    outcome_metrics=[target_node],
                    time_horizon="short_term",
                )

                supported_by_isl = validation.get("is_identifiable", False)
                robustness_score = 0.7 if supported_by_isl else 0.4

            except Exception as e:
                logger.warning(f"ISL validation failed: {e}")
                supported_by_isl = False
                robustness_score = 0.5

            # Determine evidence strength
            evidence_strength = self._assess_evidence_strength(
                claim_text, supported_by_isl, team_input.graph
            )

            # Create evidence item
            evidence_item = EvidenceItemV1(
                user_id=team_input.user_id,
                round_id=round_id,
                claim=claim_text,
                causal_path=path,
                evidence_type="domain_expertise",  # Could be inferred from reasoning
                evidence_strength=evidence_strength,
                supported_by_isl=supported_by_isl,
                robustness_score=robustness_score,
                conflicts_with=[],  # TODO: Detect conflicts with other evidence
            )

            evidence_items.append(evidence_item)

        logger.info(
            f"Extracted {len(evidence_items)} evidence items, {len(warnings)} warnings"
        )

        return evidence_items, warnings

    def _extract_causal_claims(self, reasoning: str) -> List[Tuple[str, str, str]]:
        """Extract causal claims from reasoning text.

        Args:
            reasoning: Natural language reasoning

        Returns:
            List of (claim_text, source_node, target_node) tuples
        """
        claims = []

        # Extract using regex patterns
        for pattern in self.causal_patterns:
            matches = re.finditer(pattern, reasoning, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    source = match.group(1).strip().lower()
                    target = match.group(2).strip().lower()

                    # Clean up
                    source = re.sub(r"[^\w\s-]", "", source).replace(" ", "_")
                    target = re.sub(r"[^\w\s-]", "", target).replace(" ", "_")

                    # Get full sentence as claim
                    sentence_start = max(0, match.start() - 50)
                    sentence_end = min(len(reasoning), match.end() + 50)
                    claim_text = reasoning[sentence_start:sentence_end].strip()

                    claims.append((claim_text, source, target))

        return claims[:10]  # Limit to 10 claims

    def _find_causal_path(
        self, graph: GraphV1, source: str, target: str
    ) -> Optional[CausalPathV1]:
        """Find causal path between source and target nodes.

        Args:
            graph: Causal graph
            source: Source node
            target: Target node

        Returns:
            Causal path or None
        """
        # Normalize node names for matching
        def normalize(name: str) -> str:
            return name.lower().replace(" ", "_").replace("-", "_")

        source_norm = normalize(source)
        target_norm = normalize(target)

        # Build adjacency list
        adjacency: Dict[str, List[str]] = {normalize(node): [] for node in graph.nodes}
        edge_map: Dict[Tuple[str, str], str] = {}

        for edge in graph.edges:
            src_norm = normalize(edge["source"])
            tgt_norm = normalize(edge["target"])

            if src_norm in adjacency:
                adjacency[src_norm].append(tgt_norm)
                edge_map[(src_norm, tgt_norm)] = "causal"

        # BFS to find shortest path
        from collections import deque

        queue = deque([(source_norm, [source_norm])])
        visited = {source_norm}

        while queue:
            current, path = queue.popleft()

            if current == target_norm:
                # Found path
                mechanism = path[1:-1] if len(path) > 2 else []
                edge_types = ["causal"] * (len(path) - 1)

                return CausalPathV1(
                    source_node=source,
                    target_node=target,
                    mechanism=mechanism,
                    edge_types=edge_types,
                )

            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def _assess_evidence_strength(
        self, claim: str, supported_by_isl: bool, graph: GraphV1
    ) -> str:
        """Assess evidence strength for a claim.

        Args:
            claim: Causal claim text
            supported_by_isl: Whether ISL validation passed
            graph: Causal graph

        Returns:
            Evidence strength: strong, moderate, weak, unsupported
        """
        # Strong: ISL supported + complex graph
        if supported_by_isl and len(graph.edges) >= 3:
            return "strong"

        # Moderate: ISL supported OR reasonable graph
        if supported_by_isl or len(graph.edges) >= 2:
            return "moderate"

        # Weak: Simple graph, no ISL support
        if len(graph.edges) >= 1:
            return "weak"

        return "unsupported"
