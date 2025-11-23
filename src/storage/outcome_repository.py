"""Repository for outcome tracking and learning persistence.

Handles all database operations for Phase 5 autonomous learning.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.storage.db_models import DecisionOutcomeDB, OutcomeMeasurementDB
from src.models.outcomes import (
    DecisionOutcomeV1,
    OutcomeMeasurementV1,
    PredictedOutcomeV1,
    ActualOutcomeV1,
)

logger = logging.getLogger(__name__)


class OutcomeRepository:
    """Repository for outcome tracking persistence."""

    def __init__(self, db: AsyncSession):
        """Initialize repository.

        Args:
            db: Database session
        """
        self.db = db

    # ========================================================================
    # DECISION OUTCOME OPERATIONS
    # ========================================================================

    async def create_outcome(
        self,
        outcome: DecisionOutcomeV1,
    ) -> DecisionOutcomeV1:
        """Create new decision outcome record.

        Args:
            outcome: Outcome to create

        Returns:
            Created outcome
        """
        logger.info(f"Creating decision outcome {outcome.outcome_id} for session {outcome.session_id}")

        db_outcome = DecisionOutcomeDB(
            outcome_id=outcome.outcome_id,
            session_id=outcome.session_id,
            decision=outcome.decision,
            predicted_outcomes=[p.model_dump() for p in outcome.predicted_outcomes],
            actual_outcomes=[a.model_dump() for a in outcome.actual_outcomes] if outcome.actual_outcomes else None,
            status=outcome.status,
            created_at=outcome.created_at,
            measured_at=outcome.measured_at,
        )

        self.db.add(db_outcome)
        await self.db.flush()

        return outcome

    async def get_outcome(
        self,
        outcome_id: UUID,
    ) -> Optional[DecisionOutcomeV1]:
        """Get decision outcome by ID.

        Args:
            outcome_id: Outcome ID

        Returns:
            Outcome or None
        """
        result = await self.db.execute(
            select(DecisionOutcomeDB).where(DecisionOutcomeDB.outcome_id == outcome_id)
        )
        db_outcome = result.scalar_one_or_none()

        if not db_outcome:
            return None

        return DecisionOutcomeV1(
            outcome_id=db_outcome.outcome_id,
            session_id=db_outcome.session_id,
            decision=db_outcome.decision,
            predicted_outcomes=[PredictedOutcomeV1(**p) for p in db_outcome.predicted_outcomes],
            actual_outcomes=[ActualOutcomeV1(**a) for a in db_outcome.actual_outcomes] if db_outcome.actual_outcomes else None,
            status=db_outcome.status,
            created_at=db_outcome.created_at,
            measured_at=db_outcome.measured_at,
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
        result = await self.db.execute(
            select(DecisionOutcomeDB)
            .where(DecisionOutcomeDB.session_id == session_id)
            .order_by(DecisionOutcomeDB.created_at.desc())
        )
        db_outcomes = result.scalars().all()

        outcomes = []
        for db_outcome in db_outcomes:
            outcomes.append(
                DecisionOutcomeV1(
                    outcome_id=db_outcome.outcome_id,
                    session_id=db_outcome.session_id,
                    decision=db_outcome.decision,
                    predicted_outcomes=[PredictedOutcomeV1(**p) for p in db_outcome.predicted_outcomes],
                    actual_outcomes=[ActualOutcomeV1(**a) for a in db_outcome.actual_outcomes] if db_outcome.actual_outcomes else None,
                    status=db_outcome.status,
                    created_at=db_outcome.created_at,
                    measured_at=db_outcome.measured_at,
                )
            )

        return outcomes

    async def update_outcome_status(
        self,
        outcome_id: UUID,
        status: str,
        actual_outcomes: Optional[List[ActualOutcomeV1]] = None,
    ) -> None:
        """Update outcome status and actual outcomes.

        Args:
            outcome_id: Outcome ID
            status: New status
            actual_outcomes: Actual outcomes if available
        """
        update_values = {
            "status": status,
        }

        if actual_outcomes:
            update_values["actual_outcomes"] = [a.model_dump() for a in actual_outcomes]
            update_values["measured_at"] = datetime.utcnow()

        await self.db.execute(
            update(DecisionOutcomeDB)
            .where(DecisionOutcomeDB.outcome_id == outcome_id)
            .values(**update_values)
        )
        await self.db.flush()

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
        query = (
            select(DecisionOutcomeDB)
            .where(DecisionOutcomeDB.status == status)
            .order_by(DecisionOutcomeDB.created_at.desc())
        )

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        db_outcomes = result.scalars().all()

        outcomes = []
        for db_outcome in db_outcomes:
            outcomes.append(
                DecisionOutcomeV1(
                    outcome_id=db_outcome.outcome_id,
                    session_id=db_outcome.session_id,
                    decision=db_outcome.decision,
                    predicted_outcomes=[PredictedOutcomeV1(**p) for p in db_outcome.predicted_outcomes],
                    actual_outcomes=[ActualOutcomeV1(**a) for a in db_outcome.actual_outcomes] if db_outcome.actual_outcomes else None,
                    status=db_outcome.status,
                    created_at=db_outcome.created_at,
                    measured_at=db_outcome.measured_at,
                )
            )

        return outcomes

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
        result = await self.db.execute(
            select(DecisionOutcomeDB)
            .where(DecisionOutcomeDB.status.in_(["measured", "analyzed"]))
            .order_by(DecisionOutcomeDB.measured_at.desc())
        )
        db_outcomes = result.scalars().all()

        if len(db_outcomes) < min_sample_size:
            logger.warning(
                f"Only {len(db_outcomes)} measured outcomes available, "
                f"but {min_sample_size} requested"
            )

        outcomes = []
        for db_outcome in db_outcomes:
            outcomes.append(
                DecisionOutcomeV1(
                    outcome_id=db_outcome.outcome_id,
                    session_id=db_outcome.session_id,
                    decision=db_outcome.decision,
                    predicted_outcomes=[PredictedOutcomeV1(**p) for p in db_outcome.predicted_outcomes],
                    actual_outcomes=[ActualOutcomeV1(**a) for a in db_outcome.actual_outcomes] if db_outcome.actual_outcomes else None,
                    status=db_outcome.status,
                    created_at=db_outcome.created_at,
                    measured_at=db_outcome.measured_at,
                )
            )

        return outcomes

    # ========================================================================
    # MEASUREMENT OPERATIONS
    # ========================================================================

    async def create_measurement(
        self,
        measurement: OutcomeMeasurementV1,
    ) -> OutcomeMeasurementV1:
        """Create new outcome measurement.

        Args:
            measurement: Measurement to create

        Returns:
            Created measurement
        """
        logger.info(
            f"Creating measurement {measurement.measurement_id} for outcome {measurement.outcome_id}"
        )

        db_measurement = OutcomeMeasurementDB(
            measurement_id=measurement.measurement_id,
            outcome_id=measurement.outcome_id,
            metric=measurement.metric,
            actual_value=measurement.actual_value,
            predicted_value=measurement.predicted_value,
            variance=measurement.variance,
            notes=measurement.notes,
            measured_at=measurement.measured_at,
        )

        self.db.add(db_measurement)
        await self.db.flush()

        return measurement

    async def get_measurements_for_outcome(
        self,
        outcome_id: UUID,
    ) -> List[OutcomeMeasurementV1]:
        """Get all measurements for an outcome.

        Args:
            outcome_id: Outcome ID

        Returns:
            List of measurements
        """
        result = await self.db.execute(
            select(OutcomeMeasurementDB)
            .where(OutcomeMeasurementDB.outcome_id == outcome_id)
            .order_by(OutcomeMeasurementDB.measured_at)
        )
        db_measurements = result.scalars().all()

        measurements = []
        for db_m in db_measurements:
            measurements.append(
                OutcomeMeasurementV1(
                    measurement_id=db_m.measurement_id,
                    outcome_id=db_m.outcome_id,
                    metric=db_m.metric,
                    actual_value=db_m.actual_value,
                    predicted_value=db_m.predicted_value,
                    variance=db_m.variance,
                    notes=db_m.notes,
                    measured_at=db_m.measured_at,
                )
            )

        return measurements

    async def get_measurements_by_metric(
        self,
        metric: str,
        limit: Optional[int] = None,
    ) -> List[OutcomeMeasurementV1]:
        """Get all measurements for a specific metric.

        Args:
            metric: Metric name
            limit: Optional limit on results

        Returns:
            List of measurements
        """
        query = (
            select(OutcomeMeasurementDB)
            .where(OutcomeMeasurementDB.metric == metric)
            .order_by(OutcomeMeasurementDB.measured_at.desc())
        )

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        db_measurements = result.scalars().all()

        measurements = []
        for db_m in db_measurements:
            measurements.append(
                OutcomeMeasurementV1(
                    measurement_id=db_m.measurement_id,
                    outcome_id=db_m.outcome_id,
                    metric=db_m.metric,
                    actual_value=db_m.actual_value,
                    predicted_value=db_m.predicted_value,
                    variance=db_m.variance,
                    notes=db_m.notes,
                    measured_at=db_m.measured_at,
                )
            )

        return measurements
