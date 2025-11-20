"""Validation orchestration service for ISL integration."""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from src.models import (
    ProposedOption,
    CausalValidation,
    AssumptionStrength,
    OutcomeRange,
    ValidationStatus,
    EvidenceLevel,
    ImpactLevel,
)
from src.clients import ISLClient

logger = logging.getLogger(__name__)


class ValidationOrchestrator:
    """Service for orchestrating causal validation with ISL."""

    def __init__(self, isl_client: Optional[ISLClient] = None):
        """Initialize validation orchestrator."""
        self.isl_client = isl_client or ISLClient()
        # In-memory storage for now
        self.validations: Dict[UUID, CausalValidation] = {}

    async def validate_option(
        self,
        option: ProposedOption,
        outcome_metrics: List[str],
        time_horizon: str,
    ) -> CausalValidation:
        """
        Validate option with ISL.

        Args:
            option: Proposed option
            outcome_metrics: Metrics to predict
            time_horizon: Time horizon for predictions

        Returns:
            Causal validation result
        """
        logger.info(
            "Validating option with ISL",
            extra={
                "option_id": str(option.option_id),
                "metrics": outcome_metrics,
                "horizon": time_horizon,
            },
        )

        try:
            # Call ISL for validation
            isl_result = await self.isl_client.validate_option(
                option=option.dict(),
                outcome_metrics=outcome_metrics,
                time_horizon=time_horizon,
            )

            # Parse ISL response
            validation = self._parse_isl_response(option.option_id, isl_result)

            self.validations[validation.validation_id] = validation

            logger.info(
                "Validation complete",
                extra={
                    "option_id": str(option.option_id),
                    "validation_id": str(validation.validation_id),
                    "status": validation.validation_status,
                    "is_identifiable": validation.is_identifiable,
                },
            )

            return validation

        except Exception as e:
            logger.error(
                f"Validation failed: {e}",
                extra={"option_id": str(option.option_id)},
                exc_info=True,
            )

            # Return graceful degradation
            return self._create_unavailable_validation(option.option_id, str(e))

    async def validate_all_options(
        self,
        options: List[ProposedOption],
        outcome_metrics: List[str],
        time_horizon: str,
    ) -> List[CausalValidation]:
        """
        Validate all options in parallel.

        Args:
            options: List of options to validate
            outcome_metrics: Metrics to predict
            time_horizon: Time horizon

        Returns:
            List of validation results
        """
        logger.info(
            f"Validating {len(options)} options in parallel",
            extra={"option_count": len(options)},
        )

        # In production, run in parallel with asyncio.gather
        validations = []
        for option in options:
            validation = await self.validate_option(
                option, outcome_metrics, time_horizon
            )
            validations.append(validation)

        return validations

    async def get_by_option(self, option_id: UUID) -> Optional[CausalValidation]:
        """Get validation for an option."""
        for validation in self.validations.values():
            if validation.option_id == option_id:
                return validation
        return None

    async def count_validated(self, session_id: UUID) -> int:
        """Count validated options for a session."""
        # Would query database in production
        return len([
            v for v in self.validations.values()
            if v.validation_status == ValidationStatus.VALIDATED
        ])

    async def count_calls(self, session_id: UUID) -> int:
        """Count ISL calls made for a session."""
        # Would track in database
        return len(self.validations)

    def _parse_isl_response(
        self, option_id: UUID, isl_result: Dict
    ) -> CausalValidation:
        """Parse ISL response into CausalValidation."""
        # Extract validation status
        validation_status = isl_result.get(
            "validation_status", ValidationStatus.INVALID
        )
        is_identifiable = isl_result.get("is_identifiable", False)

        # Parse predicted outcomes
        predicted_outcomes = {}
        for metric, outcome_data in isl_result.get("predicted_outcomes", {}).items():
            predicted_outcomes[metric] = OutcomeRange(
                metric=metric,
                p10=outcome_data.get("p10", 0),
                p50=outcome_data.get("p50", 0),
                p90=outcome_data.get("p90", 0),
                unit=outcome_data.get("unit", ""),
                confidence=EvidenceLevel(outcome_data.get("confidence", "medium")),
            )

        # Parse assumptions
        key_assumptions = []
        for assumption_data in isl_result.get("key_assumptions", []):
            key_assumptions.append(
                AssumptionStrength(
                    assumption_id=assumption_data.get("assumption_id", ""),
                    assumption_text=assumption_data.get("assumption_text", ""),
                    evidence_strength=EvidenceLevel(
                        assumption_data.get("evidence_strength", "medium")
                    ),
                    impact_if_wrong=ImpactLevel(
                        assumption_data.get("impact_if_wrong", "medium")
                    ),
                    source=assumption_data.get("source"),
                )
            )

        # Determine data sufficiency
        data_sufficiency = "sufficient"
        if validation_status == ValidationStatus.INSUFFICIENT_DATA:
            data_sufficiency = "insufficient"
        elif validation_status == ValidationStatus.UNCERTAIN:
            data_sufficiency = "limited"

        return CausalValidation(
            option_id=option_id,
            is_identifiable=is_identifiable,
            validation_status=validation_status,
            data_sufficiency=data_sufficiency,
            predicted_outcomes=predicted_outcomes,
            key_assumptions=key_assumptions,
            warnings=isl_result.get("warnings", []),
            quality_concerns=[],
            sensitivity_factors=[],
            isl_response=isl_result.get("isl_response", {}),
            isl_request_id=isl_result.get("isl_request_id"),
        )

    def _create_unavailable_validation(
        self, option_id: UUID, error_msg: str
    ) -> CausalValidation:
        """Create validation result for unavailable ISL."""
        return CausalValidation(
            option_id=option_id,
            is_identifiable=False,
            validation_status=ValidationStatus.UNAVAILABLE,
            data_sufficiency="insufficient",
            predicted_outcomes={},
            key_assumptions=[],
            warnings=[f"ISL unavailable: {error_msg}"],
            quality_concerns=["Could not validate option causally"],
            sensitivity_factors=[],
            isl_response={},
            isl_request_id=None,
        )
