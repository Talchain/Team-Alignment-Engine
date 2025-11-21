"""Phase C API routes: Intelligent Assistance & Learning.

Endpoints for AI-powered option generation, synthesis, tuning,
assumption testing, and decision learning.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from src.clients.cee_client import CEEClient
from src.services.ai_option_generator import AIOptionGenerator
from src.services.option_synthesizer import OptionSynthesizer
from src.services.option_tuner import OptionTuner
from src.services.assumption_testing_advisor import AssumptionTestingAdvisor
from src.services.decision_retrospective import DecisionRetrospectiveService
from src.services.session_reopener import SessionReopener
from src.models.option import ProposedOption
from src.models.concern import MinorityConcern
from src.models.validation import AssumptionStrength
from src.models.phase_c_models import (
    TestStrategy,
    DecisionRetrospective,
    AssumptionValidationRecord,
)
from src.models.session import AlignmentSession
from src.models.decision import DecisionBrief
from src.api.metrics import (
    ai_options_generated_total,
    options_synthesized_total,
    options_tuned_total,
    retrospectives_created_total,
    sessions_reopened_total,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alignment", tags=["phase-c"])


# ============================================================================
# Request/Response Models
# ============================================================================


class GenerateOptionsRequest(BaseModel):
    """Request to generate AI options."""

    generation_mode: str = Field(
        ..., description="creative_synthesis or constraint_satisfaction"
    )
    num_options: int = Field(3, ge=1, le=5, description="Number of options to generate")
    seed: Optional[str] = Field(None, description="Optional seed for determinism")


class SynthesizeOptionsRequest(BaseModel):
    """Request to synthesize options."""

    source_option_ids: List[UUID] = Field(..., min_items=2, max_items=5)
    synthesis_goal: str = Field(..., description="What to optimize for in synthesis")


class TuneOptionRequest(BaseModel):
    """Request to tune an option."""

    option_id: UUID
    concern_id: UUID
    preserve_elements: List[str] = Field(
        default_factory=list,
        description="Elements that must be preserved (e.g., timeline, budget)",
    )


class TestRecommendationsRequest(BaseModel):
    """Request test strategy recommendations."""

    option_id: UUID
    time_to_decision: int = Field(..., ge=1, description="Days until decision needed")
    available_resources: Optional[dict] = Field(
        None, description="Optional resource constraints"
    )


class CreateRetrospectiveRequest(BaseModel):
    """Request to create a decision retrospective."""

    brief_id: UUID
    actual_outcomes: dict = Field(..., description="Actual measured outcomes")
    assumption_validations: List[dict] = Field(
        default_factory=list, description="Assumption validation records"
    )


class ReopenSessionRequest(BaseModel):
    """Request to reopen a session."""

    reopen_rationale: str = Field(..., description="Why session is being reopened")


# ============================================================================
# Dependency Injection
# ============================================================================


async def get_cee_client() -> CEEClient:
    """Get CEE client instance."""
    client = CEEClient()
    try:
        yield client
    finally:
        await client.close()


# ============================================================================
# C1: AI Option Generation
# ============================================================================


@router.post("/sessions/{session_id}/generate-options")
async def generate_options(
    session_id: UUID,
    request: GenerateOptionsRequest,
    cee: CEEClient = Depends(get_cee_client),
) -> List[ProposedOption]:
    """
    Generate creative options using AI (Phase C: C1).

    This endpoint uses AI to generate 2-3 options that bridge stakeholder
    disagreements or satisfy all constraints.

    **Generation Modes:**
    - `creative_synthesis`: Generate novel options that bridge disagreements
    - `constraint_satisfaction`: Generate options respecting all red lines

    **Returns:**
    - List of AI-generated ProposedOption objects with AIGenerationMetadata
    """
    logger.info(
        "AI option generation requested",
        extra={
            "session_id": str(session_id),
            "mode": request.generation_mode,
            "num_options": request.num_options,
        },
    )

    try:
        # TODO: Fetch session, profiles, disagreement_map from database
        # For now, this is a placeholder that shows the service integration
        generator = AIOptionGenerator(cee)

        # Placeholder data - replace with actual DB queries
        profiles = []
        decision_context = "Placeholder context"
        disagreement_map = {}

        options = await generator.generate_options(
            session_id=session_id,
            profiles=profiles,
            decision_context=decision_context,
            disagreement_map=disagreement_map,
            generation_mode=request.generation_mode,
            num_options=request.num_options,
            seed=request.seed,
        )

        ai_options_generated_total.labels(mode=request.generation_mode).inc(
            len(options)
        )

        return options

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        logger.error(
            "AI option generation failed",
            extra={"session_id": str(session_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate options",
        )


# ============================================================================
# C2: Option Synthesis
# ============================================================================


@router.post("/sessions/{session_id}/synthesize-options")
async def synthesize_options(
    session_id: UUID,
    request: SynthesizeOptionsRequest,
    cee: CEEClient = Depends(get_cee_client),
) -> ProposedOption:
    """
    Synthesize a hybrid option from multiple source options (Phase C: C2).

    Combines elements from 2+ options to create a hybrid that preserves
    the best aspects of each while eliminating conflicts.

    **Returns:**
    - Synthesized ProposedOption with SynthesisMetadata
    """
    logger.info(
        "Option synthesis requested",
        extra={
            "session_id": str(session_id),
            "num_sources": len(request.source_option_ids),
        },
    )

    try:
        synthesizer = OptionSynthesizer(cee)

        # TODO: Fetch source options, profiles from database
        source_options = []
        profiles = []
        decision_context = "Placeholder context"

        synthesized_option = await synthesizer.synthesize_options(
            session_id=session_id,
            source_options=source_options,
            profiles=profiles,
            decision_context=decision_context,
            synthesis_goal=request.synthesis_goal,
        )

        options_synthesized_total.inc()

        return synthesized_option

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Option synthesis failed",
            extra={"session_id": str(session_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to synthesize options",
        )


# ============================================================================
# C3: Option Tuning
# ============================================================================


@router.post("/sessions/{session_id}/tune-option")
async def tune_option(
    session_id: UUID,
    request: TuneOptionRequest,
    cee: CEEClient = Depends(get_cee_client),
) -> ProposedOption:
    """
    Tune an option to address a minority concern (Phase C: C3).

    Adjusts an option to address a stakeholder's concern while preserving
    core elements that others value.

    **Returns:**
    - Tuned ProposedOption with TuningMetadata
    """
    logger.info(
        "Option tuning requested",
        extra={
            "session_id": str(session_id),
            "option_id": str(request.option_id),
            "concern_id": str(request.concern_id),
        },
    )

    try:
        tuner = OptionTuner(cee)

        # TODO: Fetch option, concern, profiles from database
        option = None  # Placeholder
        concern = None  # Placeholder
        profiles = []
        decision_context = "Placeholder context"

        tuned_option = await tuner.tune_option(
            session_id=session_id,
            option=option,
            concern=concern,
            profiles=profiles,
            decision_context=decision_context,
            preserve_elements=request.preserve_elements,
        )

        options_tuned_total.inc()

        return tuned_option

    except Exception as e:
        logger.error(
            "Option tuning failed",
            extra={"session_id": str(session_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to tune option",
        )


# ============================================================================
# C4: Assumption Testing Recommendations
# ============================================================================


@router.post("/sessions/{session_id}/test-recommendations")
async def get_test_recommendations(
    session_id: UUID,
    request: TestRecommendationsRequest,
    cee: CEEClient = Depends(get_cee_client),
) -> List[TestStrategy]:
    """
    Get recommendations for testing assumptions (Phase C: C4).

    Analyzes option assumptions and recommends which to validate before
    deciding, along with suggested validation methods.

    **Returns:**
    - List of TestStrategy recommendations, prioritized by importance
    """
    logger.info(
        "Test recommendations requested",
        extra={
            "session_id": str(session_id),
            "option_id": str(request.option_id),
            "days_to_decision": request.time_to_decision,
        },
    )

    try:
        advisor = AssumptionTestingAdvisor(cee)

        # TODO: Fetch option and assumptions from database
        option = None  # Placeholder
        assumptions = []  # Placeholder
        decision_context = "Placeholder context"

        strategies = await advisor.recommend_test_strategies(
            option=option,
            assumptions=assumptions,
            decision_context=decision_context,
            time_to_decision=request.time_to_decision,
            available_resources=request.available_resources,
        )

        return strategies

    except Exception as e:
        logger.error(
            "Test recommendations failed",
            extra={"session_id": str(session_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate test recommendations",
        )


# ============================================================================
# C5: Decision Retrospective
# ============================================================================


@router.post("/sessions/{session_id}/retrospective")
async def create_retrospective(
    session_id: UUID,
    request: CreateRetrospectiveRequest,
    cee: CEEClient = Depends(get_cee_client),
) -> DecisionRetrospective:
    """
    Create a decision retrospective (Phase C: C5).

    Captures actual outcomes, compares to predictions, analyzes which
    assumptions held, and generates lessons learned.

    **Returns:**
    - DecisionRetrospective with lessons learned and recommendations
    """
    logger.info(
        "Retrospective creation requested",
        extra={
            "session_id": str(session_id),
            "brief_id": str(request.brief_id),
            "num_outcomes": len(request.actual_outcomes),
        },
    )

    try:
        retrospective_service = DecisionRetrospectiveService(cee)

        # TODO: Fetch brief, convert validation records from database
        brief = None  # Placeholder
        decision_context = "Placeholder context"
        recorded_by = UUID("00000000-0000-0000-0000-000000000000")  # Placeholder

        # Convert validation dicts to AssumptionValidationRecord objects
        validations = [
            AssumptionValidationRecord(**v)
            for v in request.assumption_validations
        ]

        retrospective = await retrospective_service.create_retrospective(
            session_id=session_id,
            brief=brief,
            actual_outcomes=request.actual_outcomes,
            assumption_validations=validations,
            decision_context=decision_context,
            recorded_by=recorded_by,
        )

        retrospectives_created_total.inc()

        return retrospective

    except Exception as e:
        logger.error(
            "Retrospective creation failed",
            extra={"session_id": str(session_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create retrospective",
        )


# ============================================================================
# C6: Session Reopening
# ============================================================================


@router.post("/sessions/{session_id}/reopen")
async def reopen_session(
    session_id: UUID,
    request: ReopenSessionRequest,
) -> AlignmentSession:
    """
    Reopen a session for multi-round deliberation (Phase C: C6).

    Creates a new session linked to the original, allowing teams to
    revisit decisions when assumptions fail or context changes.

    **Returns:**
    - New AlignmentSession linked to original via parent_session_id
    """
    logger.info(
        "Session reopen requested",
        extra={
            "session_id": str(session_id),
        },
    )

    try:
        reopener = SessionReopener()

        # TODO: Fetch original session and retrospective from database
        original_session = None  # Placeholder
        retrospective = None  # Placeholder
        created_by = UUID("00000000-0000-0000-0000-000000000000")  # Placeholder

        new_session = await reopener.reopen_session(
            original_session=original_session,
            retrospective=retrospective,
            reopen_rationale=request.reopen_rationale,
            created_by=created_by,
        )

        sessions_reopened_total.inc()

        return new_session

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Session reopen failed",
            extra={"session_id": str(session_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reopen session",
        )


# ============================================================================
# Organizational Recommendations
# ============================================================================


@router.get("/teams/{team_id}/recommendations")
async def get_organizational_recommendations(
    team_id: UUID,
    cee: CEEClient = Depends(get_cee_client),
) -> dict:
    """
    Get organizational recommendations from team's retrospectives (Phase C: C5).

    Analyzes patterns across multiple decisions to identify team strengths,
    areas for improvement, and recommended process changes.

    **Returns:**
    - Organizational recommendations including patterns, strengths, and improvements
    """
    logger.info(
        "Org recommendations requested",
        extra={"team_id": str(team_id)},
    )

    try:
        retrospective_service = DecisionRetrospectiveService(cee)

        # TODO: Fetch all retrospectives for team from database
        retrospectives = []  # Placeholder

        recommendations = await retrospective_service.generate_organizational_recommendations(
            team_id=team_id,
            retrospectives=retrospectives,
        )

        return recommendations

    except Exception as e:
        logger.error(
            "Org recommendations failed",
            extra={"team_id": str(team_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate organizational recommendations",
        )
