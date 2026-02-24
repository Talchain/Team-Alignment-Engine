"""Preference elicitation API routes (Phase 2A: ActiVA).

Counterfactual-based value elicitation endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.models.preferences import (
    StartPreferenceElicitationRequestV1,
    StartPreferenceElicitationResponseV1,
    SubmitPreferenceResponseRequestV1,
    SubmitPreferenceResponseResponseV1,
    GetValueModelResponseV1,
)
from src.services.preference_elicitation import PreferenceElicitationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_preference_service():
    """Get preference elicitation service instance with managed resources."""
    from src.clients.llm_client import LLMClient

    # Create managed LLMClient with proper cleanup
    async with LLMClient() as llm_client:
        service = PreferenceElicitationService(llm_client=llm_client)
        yield service


# ============================================================================
# PREFERENCE ELICITATION ENDPOINTS
# ============================================================================


@router.post(
    "/start",
    response_model=StartPreferenceElicitationResponseV1,
    status_code=status.HTTP_201_CREATED,
    summary="Start preference elicitation session",
    description="""
Start value elicitation session using counterfactual scenarios.

**Process:**
1. System presents counterfactual scenario with two outcomes
2. User selects preferred outcome and strength
3. System updates Bayesian value model
4. Repeat until convergence (typically 5-7 questions)

**Active Learning:**
- System selects most informative questions
- Focuses on dimensions with highest uncertainty
- Converges faster than traditional surveys

**Output:**
- Weighted value model (e.g., user_growth=0.4, revenue=0.35, eng_cost=0.25)
- Can be used for value-weighted consensus synthesis
""",
)
async def start_preference_elicitation(
    request_body: StartPreferenceElicitationRequestV1,
    current_user: User = Depends(get_current_user),
    service: PreferenceElicitationService = Depends(get_preference_service),
) -> StartPreferenceElicitationResponseV1:
    """Start new preference elicitation session.

    Args:
        request_body: Start request
        service: Preference service

    Returns:
        Session and first scenario
    """
    logger.info(
        f"Starting preference elicitation for user {request_body.user_id}",
        extra={
            "decision_context": request_body.decision_context[:100],
            "value_dimensions": request_body.value_dimensions,
        },
    )

    try:
        session, first_scenario = await service.start_session(
            user_id=request_body.user_id,
            decision_context=request_body.decision_context,
            value_dimensions=request_body.value_dimensions,
            target_convergence=request_body.target_convergence,
            max_questions=request_body.max_questions,
        )

        progress = f"Question 1 of up to {request_body.max_questions}"

        return StartPreferenceElicitationResponseV1(
            session_id=session.session_id,
            first_scenario=first_scenario,
            progress=progress,
        )

    except Exception as e:
        logger.error(f"Failed to start preference elicitation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start preference elicitation: {str(e)}",
        )


@router.post(
    "/{session_id}/respond",
    response_model=SubmitPreferenceResponseResponseV1,
    status_code=status.HTTP_200_OK,
    summary="Submit preference response",
    description="""
Submit response to a counterfactual scenario.

**Response:**
- choice: "A", "B", or "indifferent"
- strength: 0.0 (indifferent) to 1.0 (strong preference)

**Convergence:**
- System checks if value model has converged
- If converged or max questions reached, session completes
- Otherwise, returns next scenario
""",
)
async def submit_preference_response(
    session_id: str,
    request_body: SubmitPreferenceResponseRequestV1,
    current_user: User = Depends(get_current_user),
    service: PreferenceElicitationService = Depends(get_preference_service),
) -> SubmitPreferenceResponseResponseV1:
    """Submit preference response.

    Args:
        session_id: Session ID
        request_body: Response request
        service: Preference service

    Returns:
        Response with next scenario or completion
    """
    logger.info(
        f"Submitting preference response for session {session_id}",
        extra={
            "user_id": request_body.user_id,
            "scenario_id": request_body.scenario_id,
            "choice": request_body.choice,
        },
    )

    try:
        accepted, next_scenario, session_complete = await service.submit_response(
            session_id=session_id,
            user_id=request_body.user_id,
            scenario_id=request_body.scenario_id,
            choice=request_body.choice,
            strength=request_body.strength,
            response_time_ms=request_body.response_time_ms,
        )

        if session_complete:
            # Get final value model
            value_model = service.get_value_model(session_id, request_body.user_id)

            progress = (
                f"Complete! Converged in {value_model.questions_asked} questions "
                f"(convergence score: {value_model.convergence_score:.2f})"
            )

            return SubmitPreferenceResponseResponseV1(
                accepted=accepted,
                next_scenario=None,
                session_complete=True,
                value_model=value_model,
                progress=progress,
            )

        # Session continues
        session = service.sessions[session_id]
        questions_asked = len(session.responses)
        max_questions = session.max_questions

        progress = f"Question {questions_asked + 1} of up to {max_questions}"

        return SubmitPreferenceResponseResponseV1(
            accepted=accepted,
            next_scenario=next_scenario,
            session_complete=False,
            value_model=None,
            progress=progress,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit preference response: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit response: {str(e)}",
        )


@router.get(
    "/{session_id}/model",
    response_model=GetValueModelResponseV1,
    status_code=status.HTTP_200_OK,
    summary="Get current value model",
    description="""
Get current value model for a session.

**Value Model:**
- dimensions: List of value dimensions with weights
- convergence_score: How confident the model is (0-1)
- questions_asked: Number of questions asked so far

**Use Cases:**
- Check current model during session
- Retrieve final model after completion
- Use for value-weighted consensus synthesis
""",
)
async def get_value_model(
    session_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    service: PreferenceElicitationService = Depends(get_preference_service),
) -> GetValueModelResponseV1:
    """Get current value model.

    Args:
        session_id: Session ID
        user_id: User ID (query parameter)
        service: Preference service

    Returns:
        Value model and session summary
    """
    try:
        value_model = service.get_value_model(session_id, user_id)

        session = service.sessions[session_id]

        session_summary = {
            "questions_asked": value_model.questions_asked,
            "convergence_score": value_model.convergence_score,
            "session_status": session.status,
            "max_questions": session.max_questions,
            "target_convergence": session.target_convergence,
        }

        return GetValueModelResponseV1(
            value_model=value_model,
            session_summary=session_summary,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    except Exception as e:
        logger.error(f"Failed to get value model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get value model: {str(e)}",
        )
