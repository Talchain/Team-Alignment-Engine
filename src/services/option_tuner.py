"""Option Tuner service (Phase C: C3).

Adjusts options to address minority concerns while preserving core elements.
"""

import logging
from typing import List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from src.clients.cee_client import CEEClient
from src.models.option import ProposedOption
from src.models.concern import MinorityConcern
from src.models.phase_c_models import TuningMetadata

logger = logging.getLogger(__name__)


class OptionTuner:
    """Service for tuning options to address minority concerns."""

    def __init__(self, cee_client: CEEClient):
        """Initialize with CEE client."""
        self.cee = cee_client

    async def tune_option(
        self,
        session_id: UUID,
        option: ProposedOption,
        concern: MinorityConcern,
        profiles: List[Dict[str, Any]],
        decision_context: str,
        preserve_elements: List[str],
    ) -> ProposedOption:
        """
        Tune an option to address a minority concern.

        Args:
            session_id: Session UUID
            option: Original option to tune
            concern: Minority concern to address
            profiles: All stakeholder profiles
            decision_context: Context of the decision
            preserve_elements: Elements that must be preserved
                (e.g., ["core_timeline", "budget_constraints"])

        Returns:
            Tuned ProposedOption with TuningMetadata

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        logger.info(
            "Tuning option for minority concern",
            extra={
                "session_id": str(session_id),
                "option_id": str(option.option_id),
                "concern_id": str(concern.concern_id),
                "preserve_elements": preserve_elements,
            },
        )

        # Convert option and concern to dicts for CEE
        option_data = {
            "option_id": str(option.option_id),
            "title": option.title,
            "description": option.description,
            "expected_outcome": option.expected_outcome,
            "causal_rationale": option.causal_rationale,
            "addresses_goals": option.addresses_goals,
            "trade_offs": option.trade_offs,
            "key_assumptions": option.key_assumptions,
        }

        concern_data = {
            "concern_id": str(concern.concern_id),
            "concern_text": concern.concern_text,
            "concern_type": concern.concern_type,
            "raised_by": str(concern.raised_by),
        }

        # Call CEE to tune option
        cee_response = await self.cee.tune_option(
            option=option_data,
            concern=concern_data,
            profiles=profiles,
            decision_context=decision_context,
            preserve_elements=preserve_elements,
        )

        # Extract tuned option from CEE response
        tuned_data = cee_response.get("tuned_option", {})

        # Extract tuning metadata
        parameters_adjusted = tuned_data.get("parameters_adjusted", [])
        preserved_elements_actual = tuned_data.get("preserved_elements", preserve_elements)

        # Create tuning metadata
        tuning_metadata = TuningMetadata(
            source_option_id=option.option_id,
            concern_addressed=concern.concern_id,
            parameters_adjusted=parameters_adjusted,
            preserved_elements=preserved_elements_actual,
            tuning_timestamp=datetime.utcnow(),
        )

        # Create tuned ProposedOption
        tuned_option = ProposedOption(
            option_id=uuid4(),
            session_id=session_id,
            proposed_by=f"ai_tuner_for_{concern.raised_by}",
            round_number=option.round_number,
            title=tuned_data.get("title"),
            description=tuned_data.get("description"),
            expected_outcome=tuned_data.get("expected_outcome"),
            causal_rationale=tuned_data.get("causal_rationale"),
            addresses_goals=tuned_data.get("addresses_goals", []),
            trade_offs=tuned_data.get("trade_offs", []),
            key_assumptions=tuned_data.get("key_assumptions", []),
            scenario_link=tuned_data.get("scenario_link"),
            is_baseline=False,
            status="tuned",
            tuning_metadata=tuning_metadata,
        )

        logger.info(
            "Option tuning complete",
            extra={
                "tuned_option_id": str(tuned_option.option_id),
                "title": tuned_option.title,
                "num_adjustments": len(parameters_adjusted),
                "preserved": len(preserved_elements_actual),
            },
        )

        return tuned_option

    async def identify_tunable_parameters(
        self, option: ProposedOption, concern: MinorityConcern
    ) -> List[str]:
        """
        Identify which parameters in an option could be tuned to address a concern.

        This is a heuristic analysis based on the concern type and option structure.

        Args:
            option: Option to analyze
            concern: Concern to address

        Returns:
            List of tunable parameter names
        """
        tunable_params = []

        # Analyze concern type
        if concern.concern_type == "timeline":
            tunable_params.extend(["timeline", "phasing", "rollout_schedule"])
        elif concern.concern_type == "budget":
            tunable_params.extend(["budget", "resource_allocation", "cost_structure"])
        elif concern.concern_type == "risk":
            tunable_params.extend(["risk_mitigation", "fallback_plan", "validation_requirements"])
        elif concern.concern_type == "scope":
            tunable_params.extend(["scope", "features", "deliverables"])
        elif concern.concern_type == "stakeholder":
            tunable_params.extend(["stakeholder_involvement", "communication_plan", "approval_process"])

        # Check which parameters are actually present in the option
        # (look in description, trade_offs, assumptions)
        option_text = (
            f"{option.description} {option.causal_rationale} "
            f"{' '.join(str(t) for t in option.trade_offs)}"
        ).lower()

        present_params = [
            param for param in tunable_params if param.replace("_", " ") in option_text
        ]

        logger.debug(
            "Identified tunable parameters",
            extra={
                "option_id": str(option.option_id),
                "concern_type": concern.concern_type,
                "tunable_params": present_params,
            },
        )

        return present_params

    async def assess_tuning_feasibility(
        self,
        option: ProposedOption,
        concern: MinorityConcern,
        preserve_elements: List[str],
    ) -> Dict[str, Any]:
        """
        Assess whether tuning is feasible given constraints.

        Args:
            option: Option to tune
            concern: Concern to address
            preserve_elements: Elements that must be preserved

        Returns:
            Feasibility assessment with:
            - is_feasible (bool)
            - tunable_params (List[str])
            - conflicts (List[str])
            - recommendation (str)
        """
        tunable_params = await self.identify_tunable_parameters(option, concern)

        # Check for conflicts between tunable params and preserve elements
        conflicts = []
        for param in tunable_params:
            for preserved in preserve_elements:
                # Simple keyword check
                if param.replace("_", " ") in preserved.lower() or preserved.lower() in param:
                    conflicts.append(f"{param} conflicts with preserved element: {preserved}")

        is_feasible = len(tunable_params) > 0 and len(conflicts) == 0

        if is_feasible:
            recommendation = (
                f"Tuning is feasible. Can adjust {len(tunable_params)} parameters "
                f"while preserving {len(preserve_elements)} core elements."
            )
        elif len(tunable_params) == 0:
            recommendation = (
                f"Tuning may not be feasible. No tunable parameters identified "
                f"for concern type '{concern.concern_type}'."
            )
        else:
            recommendation = (
                f"Tuning has conflicts. {len(conflicts)} conflicts detected "
                f"between tunable parameters and preserved elements."
            )

        logger.info(
            "Assessed tuning feasibility",
            extra={
                "option_id": str(option.option_id),
                "is_feasible": is_feasible,
                "num_tunable": len(tunable_params),
                "num_conflicts": len(conflicts),
            },
        )

        return {
            "is_feasible": is_feasible,
            "tunable_params": tunable_params,
            "conflicts": conflicts,
            "recommendation": recommendation,
        }
