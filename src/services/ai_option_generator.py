"""AI Option Generator service (Phase C: C1).

Generates creative options using AI to bridge disagreements.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from src.clients.cee_client import CEEClient
from src.models.option import ProposedOption
from src.models.phase_c_models import AIGenerationMetadata

logger = logging.getLogger(__name__)


class AIOptionGenerator:
    """Service for AI-powered option generation."""

    def __init__(self, cee_client: CEEClient):
        """Initialize with CEE client."""
        self.cee = cee_client

    async def generate_options(
        self,
        session_id: UUID,
        profiles: List[Dict[str, Any]],
        decision_context: str,
        disagreement_map: Dict[str, Any],
        generation_mode: str = "creative_synthesis",
        num_options: int = 3,
        seed: Optional[str] = None,
    ) -> List[ProposedOption]:
        """
        Generate creative options using AI.

        Args:
            session_id: Session UUID
            profiles: List of stakeholder profiles
            decision_context: Context of the decision
            disagreement_map: Map of disagreements to address
            generation_mode: "creative_synthesis" or "constraint_satisfaction"
            num_options: Number of options to generate (default 3)
            seed: Optional seed for deterministic generation

        Returns:
            List of AI-generated ProposedOption objects

        Raises:
            ValueError: If generation mode is invalid
            httpx.HTTPError: If CEE request fails
        """
        # Validate generation mode
        if generation_mode not in ["creative_synthesis", "constraint_satisfaction"]:
            raise ValueError(
                f"Invalid generation_mode: {generation_mode}. "
                "Must be 'creative_synthesis' or 'constraint_satisfaction'"
            )

        logger.info(
            "Generating AI options",
            extra={
                "session_id": str(session_id),
                "mode": generation_mode,
                "num_profiles": len(profiles),
                "num_options": num_options,
            },
        )

        # Call CEE to generate options
        cee_response = await self.cee.generate_options(
            profiles=profiles,
            decision_context=decision_context,
            disagreement_map=disagreement_map,
            generation_mode=generation_mode,
            num_options=num_options,
            seed=seed,
        )

        # Extract generated options from CEE response
        generated_options_data = cee_response.get("options", [])
        cee_request_id = cee_response.get("request_id")

        # Convert to ProposedOption objects
        options: List[ProposedOption] = []
        for idx, option_data in enumerate(generated_options_data):
            # Determine which tension was primarily addressed
            tension_addressed = option_data.get("tension_addressed")
            perspective_weights = option_data.get("perspective_weights", {})

            # Create AI generation metadata
            ai_metadata = AIGenerationMetadata(
                generation_mode=generation_mode,
                tension_addressed=tension_addressed,
                perspective_weights=perspective_weights,
                generation_timestamp=datetime.utcnow(),
                cee_request_id=cee_request_id,
            )

            # Create ProposedOption
            option = ProposedOption(
                option_id=uuid4(),
                session_id=session_id,
                proposed_by="ai_assistant",
                round_number=1,
                title=option_data.get("title"),
                description=option_data.get("description"),
                expected_outcome=option_data.get("expected_outcome"),
                causal_rationale=option_data.get("causal_rationale"),
                addresses_goals=option_data.get("addresses_goals", []),
                trade_offs=option_data.get("trade_offs", []),
                key_assumptions=option_data.get("key_assumptions", []),
                scenario_link=option_data.get("scenario_link"),
                is_baseline=False,
                status="ai_generated",
                ai_generation_metadata=ai_metadata,
            )

            options.append(option)

            logger.info(
                "Generated AI option",
                extra={
                    "option_id": str(option.option_id),
                    "title": option.title,
                    "tension_addressed": tension_addressed,
                },
            )

        logger.info(
            "AI option generation complete",
            extra={
                "session_id": str(session_id),
                "num_generated": len(options),
                "mode": generation_mode,
            },
        )

        return options

    async def generate_creative_synthesis(
        self,
        session_id: UUID,
        profiles: List[Dict[str, Any]],
        decision_context: str,
        disagreement_map: Dict[str, Any],
        num_options: int = 3,
    ) -> List[ProposedOption]:
        """
        Generate options using creative synthesis mode.

        This mode focuses on bridging disagreements with novel approaches.

        Args:
            session_id: Session UUID
            profiles: List of stakeholder profiles
            decision_context: Context of the decision
            disagreement_map: Map of disagreements to address
            num_options: Number of options to generate (default 3)

        Returns:
            List of AI-generated ProposedOption objects
        """
        return await self.generate_options(
            session_id=session_id,
            profiles=profiles,
            decision_context=decision_context,
            disagreement_map=disagreement_map,
            generation_mode="creative_synthesis",
            num_options=num_options,
        )

    async def generate_constraint_satisfaction(
        self,
        session_id: UUID,
        profiles: List[Dict[str, Any]],
        decision_context: str,
        disagreement_map: Dict[str, Any],
        num_options: int = 3,
    ) -> List[ProposedOption]:
        """
        Generate options using constraint satisfaction mode.

        This mode focuses on respecting all stakeholder red lines and must-haves.

        Args:
            session_id: Session UUID
            profiles: List of stakeholder profiles
            decision_context: Context of the decision
            disagreement_map: Map of disagreements to address
            num_options: Number of options to generate (default 3)

        Returns:
            List of AI-generated ProposedOption objects
        """
        return await self.generate_options(
            session_id=session_id,
            profiles=profiles,
            decision_context=decision_context,
            disagreement_map=disagreement_map,
            generation_mode="constraint_satisfaction",
            num_options=num_options,
        )
