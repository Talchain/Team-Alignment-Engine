"""Decision Retrospective service (Phase C: C5).

Captures actual outcomes and generates lessons learned.
"""

import logging
from typing import List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from src.clients.cee_client import CEEClient
from src.models.decision import DecisionBrief
from src.models.phase_c_models import (
    DecisionRetrospective,
    OutcomeComparison,
    AssumptionValidationRecord,
)

logger = logging.getLogger(__name__)


class DecisionRetrospectiveService:
    """Service for creating decision retrospectives and learning from outcomes."""

    def __init__(self, cee_client: CEEClient):
        """Initialize with CEE client."""
        self.cee = cee_client

    async def create_retrospective(
        self,
        session_id: UUID,
        brief: DecisionBrief,
        actual_outcomes: Dict[str, float],
        assumption_validations: List[AssumptionValidationRecord],
        decision_context: str,
        recorded_by: UUID,
    ) -> DecisionRetrospective:
        """
        Create a comprehensive decision retrospective.

        Args:
            session_id: Session UUID
            brief: Original decision brief
            actual_outcomes: Actual measured outcomes
                (e.g., {"revenue_growth": 0.15, "churn_rate": 0.05})
            assumption_validations: List of assumption validation records
            decision_context: Context of the decision
            recorded_by: User who recorded the retrospective

        Returns:
            DecisionRetrospective with lessons learned

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        logger.info(
            "Creating decision retrospective",
            extra={
                "session_id": str(session_id),
                "brief_id": str(brief.brief_id),
                "num_outcomes": len(actual_outcomes),
                "num_validations": len(assumption_validations),
            },
        )

        # Compare actual vs predicted outcomes
        outcome_comparison = await self._compare_outcomes(brief, actual_outcomes)

        # Analyze assumption results
        assumption_analysis = await self._analyze_assumptions(
            brief, assumption_validations
        )

        # Convert to dicts for CEE
        brief_data = {
            "brief_id": str(brief.brief_id),
            "chosen_option": brief.chosen_option,
            "decision_rationale": brief.decision_rationale,
            "validated_outcomes": brief.validated_outcomes,
            "accepted_assumptions": brief.accepted_assumptions,
        }

        validation_data = [
            {
                "assumption_id": v.assumption_id,
                "validation_result": v.validation_result,
                "validation_notes": v.validation_notes,
            }
            for v in assumption_validations
        ]

        # Call CEE to generate lessons learned
        cee_response = await self.cee.generate_lessons_learned(
            decision_brief=brief_data,
            actual_outcomes=actual_outcomes,
            assumption_validations=validation_data,
            decision_context=decision_context,
        )

        # Extract narrative and lessons from CEE
        narrative = cee_response.get("narrative", "")
        lessons_learned = cee_response.get("lessons_learned", [])

        # Create retrospective
        retrospective = DecisionRetrospective(
            retrospective_id=uuid4(),
            session_id=session_id,
            brief_id=brief.brief_id,
            actual_outcomes=actual_outcomes,
            outcome_comparison=outcome_comparison.dict(),
            assumption_results=[v.dict() for v in assumption_validations],
            assumption_analysis=assumption_analysis,
            narrative=narrative,
            lessons_learned=lessons_learned,
            recorded_at=datetime.utcnow(),
        )

        logger.info(
            "Decision retrospective created",
            extra={
                "retrospective_id": str(retrospective.retrospective_id),
                "num_lessons": len(lessons_learned),
                "outcome_accuracy": outcome_comparison.overall_accuracy,
            },
        )

        return retrospective

    async def _compare_outcomes(
        self, brief: DecisionBrief, actual_outcomes: Dict[str, float]
    ) -> OutcomeComparison:
        """
        Compare actual outcomes to predictions.

        Args:
            brief: Decision brief with predictions
            actual_outcomes: Actual measured outcomes

        Returns:
            OutcomeComparison analysis
        """
        predicted_outcomes = brief.validated_outcomes
        comparisons = []
        total_accuracy = 0.0
        num_compared = 0

        for metric, actual_value in actual_outcomes.items():
            if metric in predicted_outcomes:
                prediction = predicted_outcomes[metric]

                # Extract p50 prediction (expected value)
                if isinstance(prediction, dict):
                    predicted_value = prediction.get("p50", 0.0)
                    p10 = prediction.get("p10", 0.0)
                    p90 = prediction.get("p90", 0.0)

                    # Check if actual fell within range
                    within_range = p10 <= actual_value <= p90
                else:
                    predicted_value = prediction
                    within_range = False

                # Calculate accuracy (1 - relative error)
                if predicted_value != 0:
                    relative_error = abs(actual_value - predicted_value) / abs(predicted_value)
                    accuracy = max(0.0, 1.0 - relative_error)
                else:
                    accuracy = 1.0 if actual_value == 0 else 0.0

                total_accuracy += accuracy
                num_compared += 1

                comparisons.append({
                    "metric": metric,
                    "predicted": predicted_value,
                    "actual": actual_value,
                    "accuracy": accuracy,
                    "within_range": within_range,
                })

        overall_accuracy = total_accuracy / num_compared if num_compared > 0 else 0.0

        logger.debug(
            "Compared outcomes",
            extra={
                "num_metrics": num_compared,
                "overall_accuracy": overall_accuracy,
            },
        )

        return OutcomeComparison(
            comparisons=comparisons,
            overall_accuracy=overall_accuracy,
            num_metrics_compared=num_compared,
        )

    async def _analyze_assumptions(
        self, brief: DecisionBrief, validations: List[AssumptionValidationRecord]
    ) -> Dict[str, Any]:
        """
        Analyze which assumptions held vs failed.

        Args:
            brief: Decision brief with accepted assumptions
            validations: Assumption validation records

        Returns:
            Analysis dict with breakdown of assumption results
        """
        accepted_assumptions = brief.accepted_assumptions

        num_confirmed = sum(1 for v in validations if v.validation_result == "confirmed")
        num_rejected = sum(1 for v in validations if v.validation_result == "rejected")
        num_modified = sum(1 for v in validations if v.validation_result == "modified")

        # Identify which assumptions were never validated
        validated_ids = {v.assumption_id for v in validations}
        accepted_ids = {a.get("assumption_id") for a in accepted_assumptions if "assumption_id" in a}
        never_validated = list(accepted_ids - validated_ids)

        analysis = {
            "total_assumptions": len(accepted_assumptions),
            "num_validated": len(validations),
            "num_confirmed": num_confirmed,
            "num_rejected": num_rejected,
            "num_modified": num_modified,
            "never_validated_ids": never_validated,
            "assumption_accuracy": num_confirmed / len(validations) if validations else 0.0,
        }

        logger.debug(
            "Analyzed assumptions",
            extra={
                "confirmed": num_confirmed,
                "rejected": num_rejected,
                "modified": num_modified,
                "accuracy": analysis["assumption_accuracy"],
            },
        )

        return analysis

    async def generate_organizational_recommendations(
        self, team_id: UUID, retrospectives: List[DecisionRetrospective]
    ) -> Dict[str, Any]:
        """
        Generate organizational recommendations from multiple retrospectives.

        Args:
            team_id: Team UUID
            retrospectives: List of decision retrospectives for this team

        Returns:
            Organizational recommendations including:
            - patterns (List[str]): Recurring patterns identified
            - strengths (List[str]): Team strengths
            - areas_for_improvement (List[str]): Areas to improve
            - recommended_changes (List[str]): Process changes to consider

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        if not retrospectives:
            logger.warning(
                "No retrospectives available for org recommendations",
                extra={"team_id": str(team_id)},
            )
            return {
                "patterns": [],
                "strengths": [],
                "areas_for_improvement": [],
                "recommended_changes": [],
            }

        logger.info(
            "Generating organizational recommendations",
            extra={
                "team_id": str(team_id),
                "num_retrospectives": len(retrospectives),
            },
        )

        # Convert retrospectives to dicts for CEE
        retrospective_data = [
            {
                "retrospective_id": str(r.retrospective_id),
                "session_id": str(r.session_id),
                "outcome_comparison": r.outcome_comparison,
                "assumption_analysis": r.assumption_analysis,
                "lessons_learned": r.lessons_learned,
            }
            for r in retrospectives
        ]

        # Call CEE to generate org recommendations
        cee_response = await self.cee.generate_org_recommendations(
            retrospectives=retrospective_data,
            team_id=str(team_id),
        )

        recommendations = {
            "patterns": cee_response.get("patterns", []),
            "strengths": cee_response.get("strengths", []),
            "areas_for_improvement": cee_response.get("areas_for_improvement", []),
            "recommended_changes": cee_response.get("recommended_changes", []),
        }

        logger.info(
            "Organizational recommendations generated",
            extra={
                "team_id": str(team_id),
                "num_patterns": len(recommendations["patterns"]),
                "num_recommendations": len(recommendations["recommended_changes"]),
            },
        )

        return recommendations
