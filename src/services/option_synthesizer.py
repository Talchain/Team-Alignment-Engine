"""Option Synthesizer service (Phase C: C2).

Combines elements from multiple options into hybrid options.
"""

import logging
from typing import List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from src.clients.cee_client import CEEClient
from src.models.option import ProposedOption
from src.models.phase_c_models import SynthesisMetadata

logger = logging.getLogger(__name__)


class OptionSynthesizer:
    """Service for synthesizing hybrid options from multiple sources."""

    def __init__(self, cee_client: CEEClient):
        """Initialize with CEE client."""
        self.cee = cee_client

    async def synthesize_options(
        self,
        session_id: UUID,
        source_options: List[ProposedOption],
        profiles: List[Dict[str, Any]],
        decision_context: str,
        synthesis_goal: str,
    ) -> ProposedOption:
        """
        Synthesize a hybrid option from multiple source options.

        Args:
            session_id: Session UUID
            source_options: List of source options to combine
            profiles: List of stakeholder profiles
            decision_context: Context of the decision
            synthesis_goal: What to optimize for in synthesis
                (e.g., "maximize consensus", "balance trade-offs")

        Returns:
            Synthesized ProposedOption with SynthesisMetadata

        Raises:
            ValueError: If fewer than 2 source options provided
            httpx.HTTPError: If CEE request fails
        """
        if len(source_options) < 2:
            raise ValueError(
                f"Need at least 2 source options for synthesis, got {len(source_options)}"
            )

        logger.info(
            "Synthesizing hybrid option",
            extra={
                "session_id": str(session_id),
                "num_sources": len(source_options),
                "synthesis_goal": synthesis_goal,
            },
        )

        # Convert source options to dicts for CEE
        source_options_data = [
            {
                "option_id": str(opt.option_id),
                "title": opt.title,
                "description": opt.description,
                "expected_outcome": opt.expected_outcome,
                "causal_rationale": opt.causal_rationale,
                "addresses_goals": opt.addresses_goals,
                "trade_offs": opt.trade_offs,
                "key_assumptions": opt.key_assumptions,
            }
            for opt in source_options
        ]

        # Call CEE to synthesize
        cee_response = await self.cee.synthesize_options(
            source_options=source_options_data,
            decision_context=decision_context,
            profiles=profiles,
            synthesis_goal=synthesis_goal,
        )

        # Extract synthesized option from CEE response
        synthesized_data = cee_response.get("synthesized_option", {})
        source_option_ids = [opt.option_id for opt in source_options]

        # Extract synthesis metadata
        elements_preserved = synthesized_data.get("elements_preserved", [])
        elements_sacrificed = synthesized_data.get("elements_sacrificed", [])
        compatibility_score = synthesized_data.get("compatibility_score", 0.0)

        # Create synthesis metadata
        synthesis_metadata = SynthesisMetadata(
            source_option_ids=source_option_ids,
            elements_preserved=elements_preserved,
            elements_sacrificed=elements_sacrificed,
            compatibility_score=compatibility_score,
            synthesis_timestamp=datetime.utcnow(),
        )

        # Create synthesized ProposedOption
        synthesized_option = ProposedOption(
            option_id=uuid4(),
            session_id=session_id,
            proposed_by="ai_synthesizer",
            round_number=source_options[0].round_number,  # Inherit from sources
            title=synthesized_data.get("title"),
            description=synthesized_data.get("description"),
            expected_outcome=synthesized_data.get("expected_outcome"),
            causal_rationale=synthesized_data.get("causal_rationale"),
            addresses_goals=synthesized_data.get("addresses_goals", []),
            trade_offs=synthesized_data.get("trade_offs", []),
            key_assumptions=synthesized_data.get("key_assumptions", []),
            scenario_link=synthesized_data.get("scenario_link"),
            is_baseline=False,
            status="synthesized",
            synthesis_metadata=synthesis_metadata.dict(),
        )

        logger.info(
            "Option synthesis complete",
            extra={
                "synthesized_option_id": str(synthesized_option.option_id),
                "title": synthesized_option.title,
                "compatibility_score": compatibility_score,
                "num_preserved": len(elements_preserved),
                "num_sacrificed": len(elements_sacrificed),
            },
        )

        return synthesized_option

    async def calculate_compatibility_score(
        self, option_a: ProposedOption, option_b: ProposedOption
    ) -> float:
        """
        Calculate compatibility score between two options.

        Compatibility is based on:
        - Overlap in goals addressed
        - Compatibility of trade-offs
        - Consistency of assumptions

        Args:
            option_a: First option
            option_b: Second option

        Returns:
            Compatibility score between 0.0 and 1.0
        """
        # Calculate goal overlap
        goals_a = set(option_a.addresses_goals)
        goals_b = set(option_b.addresses_goals)
        if len(goals_a) == 0 or len(goals_b) == 0:
            goal_overlap = 0.0
        else:
            goal_overlap = len(goals_a & goals_b) / len(goals_a | goals_b)

        # Calculate trade-off compatibility (simple heuristic)
        tradeoffs_a = {t.get("dimension") for t in option_a.trade_offs if "dimension" in t}
        tradeoffs_b = {t.get("dimension") for t in option_b.trade_offs if "dimension" in t}
        if len(tradeoffs_a) == 0 or len(tradeoffs_b) == 0:
            tradeoff_compatibility = 1.0  # No conflicting trade-offs
        else:
            # Fewer overlapping trade-off dimensions = more compatible
            overlap = len(tradeoffs_a & tradeoffs_b)
            tradeoff_compatibility = 1.0 - (overlap / max(len(tradeoffs_a), len(tradeoffs_b)))

        # Weight the components
        compatibility = (0.6 * goal_overlap) + (0.4 * tradeoff_compatibility)

        logger.debug(
            "Calculated compatibility",
            extra={
                "option_a": str(option_a.option_id),
                "option_b": str(option_b.option_id),
                "compatibility": compatibility,
            },
        )

        return compatibility

    async def find_best_synthesis_pairs(
        self, options: List[ProposedOption], min_compatibility: float = 0.5
    ) -> List[tuple[ProposedOption, ProposedOption, float]]:
        """
        Find the best pairs of options to synthesize.

        Args:
            options: List of options to analyze
            min_compatibility: Minimum compatibility score (default 0.5)

        Returns:
            List of (option_a, option_b, compatibility_score) tuples,
            sorted by compatibility descending
        """
        if len(options) < 2:
            return []

        pairs = []
        for i in range(len(options)):
            for j in range(i + 1, len(options)):
                score = await self.calculate_compatibility_score(options[i], options[j])
                if score >= min_compatibility:
                    pairs.append((options[i], options[j], score))

        # Sort by compatibility descending
        pairs.sort(key=lambda x: x[2], reverse=True)

        logger.info(
            "Found synthesis pairs",
            extra={
                "total_options": len(options),
                "compatible_pairs": len(pairs),
                "min_compatibility": min_compatibility,
            },
        )

        return pairs
