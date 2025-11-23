"""Onboarding API routes (Phase 2B: Bayesian Teaching)."""

import logging
from fastapi import APIRouter, HTTPException, status, Depends

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.models.onboarding import (
    StartOnboardingRequestV1,
    StartOnboardingResponseV1,
    SubmitOnboardingResponseRequestV1,
    SubmitOnboardingResponseResponseV1,
    GetOnboardingProfileResponseV1,
)
from src.services.onboarding import OnboardingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


def get_onboarding_service() -> OnboardingService:
    """Get onboarding service instance."""
    return OnboardingService()


@router.post("/start", response_model=StartOnboardingResponseV1, status_code=status.HTTP_201_CREATED)
async def start_onboarding(
    request_body: StartOnboardingRequestV1,
    current_user: User = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service),
) -> StartOnboardingResponseV1:
    """Start onboarding session."""
    try:
        session, first_question = await service.start_session(
            user_id=request_body.user_id,
            decision_context=request_body.decision_context,
            user_role=request_body.user_role,
            target_confidence=request_body.target_confidence,
            max_questions=request_body.max_questions,
        )

        return StartOnboardingResponseV1(
            session_id=session.session_id,
            first_question=first_question,
            progress=f"Question 1 of up to {request_body.max_questions}",
        )
    except Exception as e:
        logger.error(f"Onboarding start failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{session_id}/respond", response_model=SubmitOnboardingResponseResponseV1)
async def submit_onboarding_response(
    session_id: str,
    request_body: SubmitOnboardingResponseRequestV1,
    current_user: User = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service),
) -> SubmitOnboardingResponseResponseV1:
    """Submit onboarding response."""
    try:
        accepted, next_question, complete = await service.submit_response(
            session_id=session_id,
            user_id=request_body.user_id,
            question_id=request_body.question_id,
            selected_option=request_body.selected_option,
            response_time_ms=request_body.response_time_ms,
        )

        if complete:
            profile = service.get_profile(session_id, request_body.user_id)
            progress = f"Complete! Profile created in {profile.questions_answered} questions"

            return SubmitOnboardingResponseResponseV1(
                accepted=accepted,
                next_question=None,
                session_complete=True,
                profile=profile,
                progress=progress,
            )

        session = service.sessions[session_id]
        progress = f"Question {len(session.responses) + 1} of up to {session.max_questions}"

        return SubmitOnboardingResponseResponseV1(
            accepted=accepted,
            next_question=next_question,
            session_complete=False,
            profile=None,
            progress=progress,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Onboarding response failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{session_id}/profile", response_model=GetOnboardingProfileResponseV1)
async def get_onboarding_profile(
    session_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service),
) -> GetOnboardingProfileResponseV1:
    """Get onboarding profile."""
    try:
        profile = service.get_profile(session_id, user_id)
        session = service.sessions[session_id]

        return GetOnboardingProfileResponseV1(
            profile=profile,
            session_summary={
                "questions_answered": profile.questions_answered,
                "profile_confidence": profile.profile_confidence,
                "session_status": session.status,
                "primary_archetype": profile.primary_archetype.archetype.name if profile.primary_archetype else None,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Get profile failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
