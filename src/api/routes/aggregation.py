"""Aggregation intelligence API routes (Phase 3: Navajas)."""

import logging
from fastapi import APIRouter, HTTPException, status, Depends

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.models.aggregation import (
    AggregationAnalysisRequestV1,
    AggregationAnalysisResponseV1,
    SmartSynthesisRequestV1,
    SmartSynthesisResponseV1,
)
from src.services.aggregation_intelligence import AggregationIntelligenceService
from src.services.deliberation_service import DeliberationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/aggregation", tags=["aggregation"])


def get_aggregation_service() -> AggregationIntelligenceService:
    """Get aggregation intelligence service."""
    return AggregationIntelligenceService()


def get_deliberation_service() -> DeliberationService:
    """Get deliberation service."""
    return DeliberationService()


@router.post("/analyze", response_model=AggregationAnalysisResponseV1)
async def analyze_aggregation(
    request_body: AggregationAnalysisRequestV1,
    current_user: User = Depends(get_current_user),
    agg_service: AggregationIntelligenceService = Depends(get_aggregation_service),
    delib_service: DeliberationService = Depends(get_deliberation_service),
) -> AggregationAnalysisResponseV1:
    """Analyze aggregation intelligence for a session."""
    try:
        # Get session
        session = delib_service.sessions.get(request_body.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {request_body.session_id} not found",
            )

        # Detect strategic behavior
        strategy_detection = agg_service.detect_strategic_behavior(session)

        # Analyze team size
        team_size_analysis = agg_service.analyze_team_size(
            session,
            decision_type=request_body.decision_type or "general",
        )

        # Analyze communication patterns
        comm_analysis = agg_service.analyze_communication_patterns(session)

        # Calibrate confidence for each participant
        confidence_calibrations = []
        for participant in session.participants:
            calibration = agg_service.calibrate_confidence(
                user_id=participant.user_id,
                stated_confidence=0.8,  # Default, would come from user input
                domain=request_body.decision_type or "general",
            )
            confidence_calibrations.append(calibration)

        # Compute recommended weights
        # Simplified: use dummy causal/value weights
        causal_weights = {p.user_id: 0.7 for p in session.participants}
        value_weights = {p.user_id: 0.6 for p in session.participants}

        recommended_weights = agg_service.compute_smart_weights(
            session=session,
            causal_weights=causal_weights,
            value_weights=value_weights,
            strategy_detection=strategy_detection,
        )

        return AggregationAnalysisResponseV1(
            confidence_calibration=confidence_calibrations,
            strategic_behaviour=strategy_detection,
            team_size_analysis=team_size_analysis,
            communication_patterns=comm_analysis,
            recommended_weights=recommended_weights,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Aggregation analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/synthesize", response_model=SmartSynthesisResponseV1)
async def smart_synthesis(
    request_body: SmartSynthesisRequestV1,
    current_user: User = Depends(get_current_user),
    agg_service: AggregationIntelligenceService = Depends(get_aggregation_service),
    delib_service: DeliberationService = Depends(get_deliberation_service),
) -> SmartSynthesisResponseV1:
    """Generate smart synthesis with aggregation intelligence."""
    try:
        # Get session
        session = delib_service.sessions.get(request_body.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {request_body.session_id} not found",
            )

        # Analyze aggregation
        strategy_detection = agg_service.detect_strategic_behavior(session)
        diversity = agg_service._measure_diversity(session)

        # Compute aggregation quality
        agg_quality = agg_service.compute_aggregation_quality(session, diversity)

        # Generate warnings
        warnings = []
        for pattern in strategy_detection.detected_patterns:
            if pattern.pattern_type == "conformity" and pattern.confidence > 0.6:
                warnings.append("Conformity detected - results may be biased toward consensus")
            elif pattern.pattern_type == "anchoring" and pattern.confidence > 0.6:
                warnings.append("Anchoring detected - early submissions may have biased later inputs")

        # Get synthesis options (simplified - would integrate with consensus builder)
        synthesis_options = [
            {"description": "Smart synthesis with aggregation intelligence", "score": agg_quality.collective_intelligence_score}
        ]

        return SmartSynthesisResponseV1(
            synthesis_options=synthesis_options,
            aggregation_quality=agg_quality,
            warnings=warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Smart synthesis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
