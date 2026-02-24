"""Outcome tracking service for Phase 5 autonomous learning.

Tracks decision outcomes, predicted vs actual measurements, and provides
data for pattern learning and graph refinement.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4

from src.storage.outcome_repository import OutcomeRepository
from src.models.outcomes import (
    DecisionOutcomeV1,
    OutcomeMeasurementV1,
    PredictedOutcomeV1,
    ActualOutcomeV1,
    TrackDecisionOutcomeRequestV1,
    TrackDecisionOutcomeResponseV1,
    RecordActualOutcomeRequestV1,
    RecordActualOutcomeResponseV1,
    OutcomeAnalysisResponseV1,
    AccuracyAnalysisV1,
    AssumptionValidationV1,
)
from src.models.consensus import SynthesisOptionV1

logger = logging.getLogger(__name__)


class OutcomeTrackingService:
    """Service for tracking decision outcomes and learning from them."""

    def __init__(self, repository: OutcomeRepository):
        """Initialize service.

        Args:
            repository: Outcome repository for persistence
        """
        self.repository = repository

    async def track_decision_outcome(
        self,
        request: TrackDecisionOutcomeRequestV1,
    ) -> TrackDecisionOutcomeResponseV1:
        """Track a new decision outcome with predictions.

        Args:
            request: Decision outcome tracking request

        Returns:
            Outcome tracking response with outcome ID
        """
        logger.info(f"Tracking decision outcome for session {request.session_id}")

        # Extract key assumptions from selected option
        key_assumptions = []
        if hasattr(request.selected_option, "causal_rationale"):
            # Parse assumptions from causal rationale
            # This is a placeholder - in production, would use LLM to extract
            key_assumptions = [
                {
                    "assumption_id": f"assumption_{i}",
                    "description": request.selected_option.causal_rationale,
                }
                for i in range(1)
            ]

        # Create decision record
        decision_data = {
            "selected_option": request.selected_option.model_dump(),
            "decided_at": datetime.utcnow().isoformat() + "Z",
            "decision_graph": getattr(request.selected_option, "graph", {}).model_dump() if hasattr(request.selected_option, "graph") else {},
            "key_assumptions": key_assumptions,
        }

        # Create outcome record
        outcome = DecisionOutcomeV1(
            outcome_id=uuid4(),
            session_id=request.session_id,
            decision=decision_data,
            predicted_outcomes=request.predicted_outcomes,
            actual_outcomes=None,
            status="predicted",
            created_at=datetime.utcnow(),
            measured_at=None,
        )

        # Persist to database
        await self.repository.create_outcome(outcome)

        # Determine next measurement date from schedule
        next_measurement_date = None
        if request.measurement_schedule:
            # Find earliest measurement date
            earliest = min(
                request.measurement_schedule,
                key=lambda x: x.get("measure_at", "9999-12-31"),
            )
            next_measurement_date = earliest.get("measure_at")

        logger.info(f"Decision outcome tracked with ID {outcome.outcome_id}")

        return TrackDecisionOutcomeResponseV1(
            outcome_id=outcome.outcome_id,
            status="predicted",
            next_measurement_date=next_measurement_date,
        )

    async def record_actual_outcome(
        self,
        request: RecordActualOutcomeRequestV1,
    ) -> RecordActualOutcomeResponseV1:
        """Record actual measured outcomes for a decision.

        Args:
            request: Request with actual outcome measurements

        Returns:
            Response confirming measurements recorded
        """
        logger.info(f"Recording actual outcomes for outcome {request.outcome_id}")

        # Get existing outcome
        outcome = await self.repository.get_outcome(request.outcome_id)
        if not outcome:
            raise ValueError(f"Outcome {request.outcome_id} not found")

        # Create granular measurements
        measurements_created = 0
        for actual in request.actual_outcomes:
            # Find matching prediction
            predicted = next(
                (p for p in outcome.predicted_outcomes if p.metric == actual.metric),
                None,
            )

            if not predicted:
                logger.warning(
                    f"No prediction found for metric {actual.metric}, skipping measurement"
                )
                continue

            # Create measurement record
            measurement = OutcomeMeasurementV1(
                measurement_id=uuid4(),
                outcome_id=request.outcome_id,
                metric=actual.metric,
                actual_value=actual.actual_value,
                predicted_value=predicted.predicted_value,
                variance=actual.variance_from_prediction,
                notes=request.notes,
                measured_at=actual.measured_at,
            )

            await self.repository.create_measurement(measurement)
            measurements_created += 1

        # Update outcome with actual outcomes
        await self.repository.update_outcome_status(
            outcome_id=request.outcome_id,
            status="measured",
            actual_outcomes=request.actual_outcomes,
        )

        logger.info(
            f"Recorded {measurements_created} measurements for outcome {request.outcome_id}"
        )

        return RecordActualOutcomeResponseV1(
            outcome_id=request.outcome_id,
            measurements_recorded=measurements_created,
            status="measured",
        )

    async def analyze_outcome(
        self,
        outcome_id: UUID,
    ) -> OutcomeAnalysisResponseV1:
        """Analyze outcome accuracy and assumption validation.

        Args:
            outcome_id: Outcome ID to analyze

        Returns:
            Detailed outcome analysis
        """
        logger.info(f"Analyzing outcome {outcome_id}")

        # Get outcome
        outcome = await self.repository.get_outcome(outcome_id)
        if not outcome:
            raise ValueError(f"Outcome {outcome_id} not found")

        if outcome.status not in ["measured", "analyzed"]:
            raise ValueError(
                f"Outcome {outcome_id} has not been measured yet (status: {outcome.status})"
            )

        # Analyze accuracy for each metric
        accuracy_analysis = []
        for predicted in outcome.predicted_outcomes:
            # Find matching actual
            actual = next(
                (a for a in outcome.actual_outcomes if a.metric == predicted.metric),
                None,
            )

            if not actual:
                logger.warning(f"No actual outcome for metric {predicted.metric}")
                continue

            # Calculate accuracy metrics
            prediction_error = abs(actual.variance_from_prediction)

            # Check if within confidence interval
            within_ci = (
                predicted.confidence_interval["lower"]
                <= actual.actual_value
                <= predicted.confidence_interval["upper"]
            )

            # Assign accuracy grade
            if prediction_error < 0.1:
                grade = "excellent"
            elif prediction_error < 0.2:
                grade = "good"
            else:
                grade = "poor"

            accuracy_analysis.append(
                AccuracyAnalysisV1(
                    metric=predicted.metric,
                    prediction_error=prediction_error,
                    within_confidence_interval=within_ci,
                    accuracy_grade=grade,
                )
            )

        # Validate assumptions
        # This is a placeholder - in production, would use sophisticated validation
        assumption_validation = []
        key_assumptions = outcome.decision.get("key_assumptions", [])
        for assumption in key_assumptions:
            # Heuristic: if accuracy is good, assumptions likely held
            avg_accuracy = sum(a.prediction_error for a in accuracy_analysis) / len(
                accuracy_analysis
            ) if accuracy_analysis else 1.0

            validated = avg_accuracy < 0.2  # Good accuracy threshold

            assumption_validation.append(
                AssumptionValidationV1(
                    assumption_id=assumption.get("assumption_id", "unknown"),
                    validated=validated,
                    evidence=[
                        f"Average prediction error: {avg_accuracy:.2%}",
                        f"Metrics analyzed: {len(accuracy_analysis)}",
                    ],
                )
            )

        # Update outcome status to analyzed
        await self.repository.update_outcome_status(
            outcome_id=outcome_id,
            status="analyzed",
        )

        logger.info(
            f"Outcome analysis complete: {len(accuracy_analysis)} metrics, "
            f"{len(assumption_validation)} assumptions"
        )

        return OutcomeAnalysisResponseV1(
            outcome=outcome,
            accuracy_analysis=accuracy_analysis,
            assumption_validation=assumption_validation,
        )

    async def get_outcomes_for_session(
        self,
        session_id: str,
    ) -> List[DecisionOutcomeV1]:
        """Get all outcomes for a session.

        Args:
            session_id: Session ID

        Returns:
            List of outcomes
        """
        return await self.repository.get_outcomes_for_session(session_id)

    async def get_outcomes_by_status(
        self,
        status: str,
        limit: Optional[int] = None,
    ) -> List[DecisionOutcomeV1]:
        """Get outcomes by status.

        Args:
            status: Status to filter by
            limit: Optional limit on results

        Returns:
            List of outcomes
        """
        return await self.repository.get_outcomes_by_status(status, limit)

    async def get_all_measured_outcomes(
        self,
        min_sample_size: int = 1,
    ) -> List[DecisionOutcomeV1]:
        """Get all measured outcomes for learning.

        Args:
            min_sample_size: Minimum number of outcomes to return

        Returns:
            List of measured outcomes
        """
        return await self.repository.get_all_measured_outcomes(min_sample_size)
