"""Concern validation service for minority protection."""

import logging
from typing import Dict, Optional
from uuid import UUID

from src.models import MinorityConcern, ConcernStatus, SensitivityResult
from src.clients import ISLClient

logger = logging.getLogger(__name__)


class ConcernValidator:
    """Service for validating minority concerns."""

    def __init__(self, isl_client: Optional[ISLClient] = None):
        """Initialize concern validator."""
        self.isl_client = isl_client or ISLClient()
        # In-memory storage for now
        self.concerns: Dict[UUID, MinorityConcern] = {}

    async def create_concern(
        self,
        option_id: UUID,
        raised_by: UUID,
        concern_text: str,
        concern_type: str,
        assumption_id_tested: Optional[str] = None,
    ) -> MinorityConcern:
        """
        Create a new minority concern.

        Args:
            option_id: Option being questioned
            raised_by: User raising the concern
            concern_text: Text of the concern
            concern_type: Type (assumption, constraint, outcome)
            assumption_id_tested: Optional assumption ID to test

        Returns:
            Created concern
        """
        concern = MinorityConcern(
            option_id=option_id,
            raised_by=raised_by,
            concern_text=concern_text,
            concern_type=concern_type,
            assumption_id_tested=assumption_id_tested,
            status=ConcernStatus.RAISED,
        )

        self.concerns[concern.concern_id] = concern

        logger.info(
            "Concern raised",
            extra={
                "concern_id": str(concern.concern_id),
                "option_id": str(option_id),
                "raised_by": str(raised_by),
                "concern_type": concern_type,
            },
        )

        return concern

    async def validate_concern(
        self,
        concern_id: UUID,
        validation_id: str,
        factor: str,
        baseline_value: float,
        alternative_value: float,
        materiality_threshold: float = 0.1,
    ) -> MinorityConcern:
        """
        Validate concern with ISL sensitivity analysis.

        Args:
            concern_id: Concern to validate
            validation_id: ISL validation ID
            factor: Factor to test
            baseline_value: Baseline value
            alternative_value: Alternative value to test
            materiality_threshold: Threshold for materiality (default 10%)

        Returns:
            Updated concern with validation result
        """
        concern = self.concerns.get(concern_id)
        if not concern:
            raise ValueError(f"Concern {concern_id} not found")

        concern.status = ConcernStatus.VALIDATING

        logger.info(
            "Validating concern with ISL",
            extra={
                "concern_id": str(concern_id),
                "factor": factor,
                "baseline": baseline_value,
                "alternative": alternative_value,
            },
        )

        try:
            # Call ISL for sensitivity analysis
            sensitivity = await self.isl_client.sensitivity_analysis(
                validation_id=validation_id,
                factor=factor,
                baseline_value=baseline_value,
                alternative_value=alternative_value,
            )

            # Determine if concern is material
            outcome_delta_percent = abs(
                sensitivity.get("outcome_delta_percent", 0)
            )
            is_material = outcome_delta_percent > materiality_threshold

            # Create sensitivity result
            concern.causal_validation = SensitivityResult(
                factor_tested=factor,
                baseline_outcome=sensitivity.get("baseline_outcome", 0),
                alternative_outcome=sensitivity.get("alternative_outcome", 0),
                outcome_delta=sensitivity.get("outcome_delta", 0),
                is_material=is_material,
                explanation=sensitivity.get("explanation", ""),
            )

            concern.sensitivity_tested = True
            concern.status = (
                ConcernStatus.VALIDATED if is_material else ConcernStatus.DISMISSED
            )

            logger.info(
                "Concern validation complete",
                extra={
                    "concern_id": str(concern_id),
                    "is_material": is_material,
                    "delta_percent": outcome_delta_percent,
                },
            )

        except Exception as e:
            logger.error(
                f"Concern validation failed: {e}",
                extra={"concern_id": str(concern_id)},
                exc_info=True,
            )

            concern.status = ConcernStatus.RAISED
            concern.resolution = f"Validation failed: {str(e)}"

        self.concerns[concern_id] = concern
        return concern

    async def address_concern(
        self, concern_id: UUID, resolution: str
    ) -> MinorityConcern:
        """
        Mark concern as addressed.

        Args:
            concern_id: Concern to address
            resolution: Resolution explanation

        Returns:
            Updated concern
        """
        concern = self.concerns.get(concern_id)
        if not concern:
            raise ValueError(f"Concern {concern_id} not found")

        concern.status = ConcernStatus.ADDRESSED
        concern.resolution = resolution

        logger.info(
            "Concern addressed",
            extra={"concern_id": str(concern_id)},
        )

        self.concerns[concern_id] = concern
        return concern

    async def get(self, concern_id: UUID) -> Optional[MinorityConcern]:
        """Get concern by ID."""
        return self.concerns.get(concern_id)

    async def get_all_by_option(self, option_id: UUID) -> list:
        """Get all concerns for an option."""
        return [
            concern
            for concern in self.concerns.values()
            if concern.option_id == option_id
        ]
