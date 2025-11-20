"""Decision documentation service."""

import logging
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from src.models import DecisionBrief, AssumptionStrength, OutcomeRange

logger = logging.getLogger(__name__)


class DecisionDocumenter:
    """Service for documenting final decisions."""

    def __init__(self):
        """Initialize decision documenter."""
        # In-memory storage for now
        self.briefs: Dict[UUID, DecisionBrief] = {}

    async def create(
        self,
        session_id: UUID,
        chosen_option: Dict,
        decision_rationale: str,
        stakeholder_support: Dict[str, str],
        consensus_strength: float,
        validated_outcomes: Dict[str, OutcomeRange],
        accepted_assumptions: List[AssumptionStrength],
        monitored_risks: List[str],
        minority_concerns_raised: List[Dict],
        minority_concerns_addressed: List[str],
        review_date: datetime,
        success_criteria: List[str],
        monitoring_plan: List[str],
        participants: List[UUID],
        scenario_model_id: Optional[UUID] = None,
        scenario_snapshot: Optional[Dict] = None,
    ) -> DecisionBrief:
        """
        Create decision brief.

        Args:
            session_id: Session identifier
            chosen_option: Chosen option dict
            decision_rationale: Why this option was chosen
            stakeholder_support: Support levels per stakeholder
            consensus_strength: Overall consensus score
            validated_outcomes: Validated outcome predictions
            accepted_assumptions: Assumptions team accepts
            monitored_risks: Risks to monitor
            minority_concerns_raised: List of concerns
            minority_concerns_addressed: How concerns were addressed
            review_date: When to review decision
            success_criteria: Criteria for success
            monitoring_plan: How to monitor
            participants: List of participant user IDs
            scenario_model_id: Optional scenario model ID
            scenario_snapshot: Optional scenario snapshot

        Returns:
            Created decision brief
        """
        brief = DecisionBrief(
            session_id=session_id,
            chosen_option=chosen_option,
            decision_rationale=decision_rationale,
            stakeholder_support=stakeholder_support,
            consensus_strength=consensus_strength,
            validated_outcomes=validated_outcomes,
            accepted_assumptions=accepted_assumptions,
            monitored_risks=monitored_risks,
            minority_concerns_raised=minority_concerns_raised,
            minority_concerns_addressed=minority_concerns_addressed,
            review_date=review_date,
            success_criteria=success_criteria,
            monitoring_plan=monitoring_plan,
            participants=participants,
            scenario_model_id=scenario_model_id,
            scenario_snapshot=scenario_snapshot,
        )

        self.briefs[brief.brief_id] = brief

        logger.info(
            "Decision brief created",
            extra={
                "brief_id": str(brief.brief_id),
                "session_id": str(session_id),
                "consensus_strength": consensus_strength,
                "concerns_raised": len(minority_concerns_raised),
                "concerns_addressed": len(minority_concerns_addressed),
            },
        )

        return brief

    async def get_by_session(self, session_id: UUID) -> Optional[DecisionBrief]:
        """Get decision brief for a session."""
        for brief in self.briefs.values():
            if brief.session_id == session_id:
                return brief
        return None

    async def update(self, brief: DecisionBrief) -> None:
        """Update decision brief."""
        self.briefs[brief.brief_id] = brief

        logger.info(
            "Decision brief updated",
            extra={"brief_id": str(brief.brief_id)},
        )

    async def rate_decision(
        self, brief_id: UUID, rating: int, notes: Optional[str] = None
    ) -> None:
        """
        Rate decision quality post-hoc.

        Args:
            brief_id: Brief identifier
            rating: Quality rating (1-10)
            notes: Optional notes
        """
        brief = self.briefs.get(brief_id)
        if not brief:
            raise ValueError(f"Brief {brief_id} not found")

        brief.decision_quality_rating = rating
        brief.post_decision_notes = notes

        self.briefs[brief_id] = brief

        logger.info(
            "Decision rated",
            extra={"brief_id": str(brief_id), "rating": rating},
        )
