"""API routes for Phase 5 outcome tracking and learning.

Endpoints:
- POST /v1/outcomes/track - Track a decision outcome
- POST /v1/outcomes/record - Record actual outcomes
- GET /v1/outcomes/{outcome_id}/analyze - Analyze outcome accuracy
- GET /v1/outcomes/session/{session_id} - Get outcomes for session
- GET /v1/learning/insights - Get learning insights
"""

import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.storage.database import get_db
from src.storage.outcome_repository import OutcomeRepository
from src.services.outcome_tracking import OutcomeTrackingService
from src.services.decision_pattern_learner import DecisionPatternLearner
from src.models.outcomes import (
    TrackDecisionOutcomeRequestV1,
    TrackDecisionOutcomeResponseV1,
    RecordActualOutcomeRequestV1,
    RecordActualOutcomeResponseV1,
    OutcomeAnalysisResponseV1,
    DecisionOutcomeV1,
    GetLearningInsightsRequestV1,
    GetLearningInsightsResponseV1,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/outcomes", tags=["outcomes"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_outcome_service(
    db: AsyncSession = Depends(get_db),
) -> OutcomeTrackingService:
    """Get outcome tracking service instance.

    Args:
        db: Database session

    Returns:
        Outcome tracking service
    """
    repository = OutcomeRepository(db)
    return OutcomeTrackingService(repository)


async def get_pattern_learner(
    db: AsyncSession = Depends(get_db),
) -> DecisionPatternLearner:
    """Get decision pattern learner instance.

    Args:
        db: Database session

    Returns:
        Decision pattern learner
    """
    repository = OutcomeRepository(db)
    return DecisionPatternLearner(repository)


# ============================================================================
# OUTCOME TRACKING ENDPOINTS
# ============================================================================


@router.post("/track", response_model=TrackDecisionOutcomeResponseV1)
async def track_decision_outcome(
    request_body: TrackDecisionOutcomeRequestV1,
    current_user: User = Depends(get_current_user),
    service: OutcomeTrackingService = Depends(get_outcome_service),
) -> TrackDecisionOutcomeResponseV1:
    """Track a decision outcome with predictions.

    Creates a new outcome tracking record for a decision, storing:
    - Selected option and decision details
    - Predicted outcomes with confidence intervals
    - Measurement schedule

    Args:
        request_body: Decision outcome tracking request
        current_user: Authenticated user
        service: Outcome tracking service

    Returns:
        Outcome tracking response with outcome ID

    Raises:
        HTTPException: If tracking fails
    """
    try:
        logger.info(
            f"User {current_user.user_id} tracking outcome for session {request_body.session_id}"
        )
        return await service.track_decision_outcome(request_body)
    except Exception as e:
        logger.error(f"Failed to track decision outcome: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track decision outcome: {str(e)}",
        )


@router.post("/record", response_model=RecordActualOutcomeResponseV1)
async def record_actual_outcome(
    request_body: RecordActualOutcomeRequestV1,
    current_user: User = Depends(get_current_user),
    service: OutcomeTrackingService = Depends(get_outcome_service),
) -> RecordActualOutcomeResponseV1:
    """Record actual measured outcomes for a decision.

    Updates an outcome record with actual measurements:
    - Actual metric values
    - Variance from predictions
    - Measurement timestamp

    Args:
        request_body: Actual outcome recording request
        current_user: Authenticated user
        service: Outcome tracking service

    Returns:
        Response confirming measurements recorded

    Raises:
        HTTPException: If outcome not found or recording fails
    """
    try:
        logger.info(
            f"User {current_user.user_id} recording actual outcome for {request_body.outcome_id}"
        )
        return await service.record_actual_outcome(request_body)
    except ValueError as e:
        logger.warning(f"Outcome not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to record actual outcome: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record actual outcome: {str(e)}",
        )


@router.get("/{outcome_id}/analyze", response_model=OutcomeAnalysisResponseV1)
async def analyze_outcome(
    outcome_id: UUID,
    current_user: User = Depends(get_current_user),
    service: OutcomeTrackingService = Depends(get_outcome_service),
) -> OutcomeAnalysisResponseV1:
    """Analyze outcome accuracy and assumption validation.

    Provides detailed analysis of prediction accuracy:
    - Accuracy metrics for each predicted outcome
    - Assumption validation results
    - Accuracy grades

    Args:
        outcome_id: Outcome ID to analyze
        current_user: Authenticated user
        service: Outcome tracking service

    Returns:
        Detailed outcome analysis

    Raises:
        HTTPException: If outcome not found or not measured
    """
    try:
        logger.info(f"User {current_user.user_id} analyzing outcome {outcome_id}")
        return await service.analyze_outcome(outcome_id)
    except ValueError as e:
        logger.warning(f"Cannot analyze outcome: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to analyze outcome: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze outcome: {str(e)}",
        )


@router.get("/session/{session_id}", response_model=List[DecisionOutcomeV1])
async def get_outcomes_for_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    service: OutcomeTrackingService = Depends(get_outcome_service),
) -> List[DecisionOutcomeV1]:
    """Get all outcomes for a session.

    Retrieves all outcome tracking records for a deliberation session.

    Args:
        session_id: Session ID
        current_user: Authenticated user
        service: Outcome tracking service

    Returns:
        List of decision outcomes

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.info(
            f"User {current_user.user_id} retrieving outcomes for session {session_id}"
        )
        return await service.get_outcomes_for_session(session_id)
    except Exception as e:
        logger.error(f"Failed to retrieve outcomes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve outcomes: {str(e)}",
        )


# ============================================================================
# LEARNING INSIGHTS ENDPOINTS
# ============================================================================


@router.post("/learning/insights", response_model=GetLearningInsightsResponseV1)
async def get_learning_insights(
    request_body: GetLearningInsightsRequestV1,
    current_user: User = Depends(get_current_user),
    learner: DecisionPatternLearner = Depends(get_pattern_learner),
) -> GetLearningInsightsResponseV1:
    """Get learning insights from historical outcomes.

    Analyzes historical decision outcomes to identify:
    - Reliable causal paths that predict well
    - Unreliable assumptions frequently violated
    - Missing confounders that improve accuracy

    Args:
        request_body: Learning insights request
        current_user: Authenticated user
        learner: Decision pattern learner

    Returns:
        Learning insights per archetype

    Raises:
        HTTPException: If analysis fails
    """
    try:
        logger.info(
            f"User {current_user.user_id} requesting learning insights "
            f"(archetype: {request_body.archetype})"
        )
        return await learner.get_learning_insights(request_body)
    except Exception as e:
        logger.error(f"Failed to get learning insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get learning insights: {str(e)}",
        )
