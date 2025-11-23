"""Deliberation API routes - Multi-round consensus building.

Science-backed iterative deliberation with anonymous voting and convergence detection.
"""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.database import get_db

from src.models.deliberation import (
    StartDeliberationRequestV1,
    StartDeliberationResponseV1,
    SubmitInputRequestV1,
    SubmitInputResponseV1,
    SubmitVoteRequestV1,
    SubmitVoteResponseV1,
    AdvanceRoundRequestV1,
    AdvanceRoundResponseV1,
    DeliberationStatusResponseV1,
    DeliberationHistoryResponseV1,
    DeliberationTimelineEventV1,
    RoundDetailsV1,
    VoteV1,
)
from src.services.deliberation_service import DeliberationService
from src.api.metrics import (
    consensus_calculation_duration_seconds,
)
from src.config.logging_config import set_logging_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/deliberation", tags=["deliberation"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_deliberation_service(
    db: AsyncSession = Depends(get_db),
) -> DeliberationService:
    """Get deliberation service instance with database session.

    Args:
        db: Database session

    Returns:
        DeliberationService instance
    """
    from src.storage.deliberation_repository import DeliberationRepository
    repository = DeliberationRepository(db)
    return DeliberationService(repository=repository)


# ============================================================================
# DELIBERATION LIFECYCLE ENDPOINTS
# ============================================================================


@router.post(
    "/start",
    response_model=StartDeliberationResponseV1,
    status_code=status.HTTP_201_CREATED,
    summary="Start new deliberation session",
    description="""
Start a multi-round deliberation session for team decision-making.

**Process:**
1. Round 1 (Submission): Participants submit causal graphs + reasoning
2. Round 2 (Synthesis): System generates creative synthesis options
3. Round 3 (Voting): Participants vote anonymously
4. Round 4+ (Refinement): If needed, resolve conflicts and refine positions
5. Convergence: Session concludes when quality threshold met

**Anonymous Voting:**
- Votes remain encrypted during active voting
- Individual votes revealed only after round closes
- Prevents groupthink and social pressure

**Convergence Detection:**
- Quality-based (not just vote count)
- Protects minority positions with strong causal evidence
- Prevents mediocre compromise through causal validation
""",
)
async def start_deliberation(
    request_body: StartDeliberationRequestV1,
    http_request: Request,
    service: DeliberationService = Depends(get_deliberation_service),
) -> StartDeliberationResponseV1:
    """Start a new deliberation session.

    Args:
        request_body: Deliberation start request
        http_request: FastAPI request
        service: Deliberation service

    Returns:
        Session and first round info
    """
    trace_id = http_request.headers.get("X-Request-ID") or f"deliberation-{uuid4()}"

    set_logging_context(
        trace_id=trace_id,
        method=http_request.method,
        endpoint=http_request.url.path,
    )

    logger.info(
        "Starting deliberation session",
        extra={
            "trace_id": trace_id,
            "num_participants": len(request_body.participants),
            "decision_context": request_body.decision_context[:100],
        },
    )

    try:
        session, first_round = await service.start_session(
            decision_context=request_body.decision_context,
            participants=request_body.participants,
            convergence_criteria=request_body.convergence_criteria,
        )

        return StartDeliberationResponseV1(
            session_id=session.session_id,
            round_id=first_round.round_id,
            round_type="submission",
            instructions=f"Submit your perspective: create a causal graph and provide reasoning for the decision: {request_body.decision_context}",
        )

    except Exception as e:
        logger.error(f"Failed to start deliberation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start deliberation: {str(e)}",
        )


@router.post(
    "/{session_id}/submit",
    response_model=SubmitInputResponseV1,
    status_code=status.HTTP_200_OK,
    summary="Submit perspective for current round",
)
async def submit_input(
    session_id: str,
    request_body: SubmitInputRequestV1,
    service: DeliberationService = Depends(get_deliberation_service),
) -> SubmitInputResponseV1:
    """Submit causal graph + reasoning for a submission round.

    Args:
        session_id: Session ID
        request_body: Input submission
        service: Deliberation service

    Returns:
        Acceptance status and causal quality assessment
    """
    logger.info(
        f"Input submission for session {session_id}",
        extra={"user_id": request_body.user_id, "round_id": request_body.round_id},
    )

    try:
        accepted, validation = await service.submit_input(
            session_id=session_id,
            user_id=request_body.user_id,
            round_id=request_body.round_id,
            graph=request_body.graph,
            reasoning=request_body.reasoning,
        )

        return SubmitInputResponseV1(
            accepted=accepted,
            causal_quality=validation["causal_quality"],
            validation_issues=validation["validation_issues"],
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Input submission failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Submission failed: {str(e)}",
        )


@router.post(
    "/{session_id}/vote",
    response_model=SubmitVoteResponseV1,
    status_code=status.HTTP_200_OK,
    summary="Submit anonymous vote",
    description="""
Submit anonymous vote for synthesis options.

**Anonymity Guarantee:**
- Your user ID is encrypted before storage
- Individual votes remain anonymous during active voting
- Votes are decrypted only after round closes
- Prevents groupthink and social pressure
""",
)
async def submit_vote(
    session_id: str,
    request_body: SubmitVoteRequestV1,
    service: DeliberationService = Depends(get_deliberation_service),
) -> SubmitVoteResponseV1:
    """Submit vote in a voting round.

    Args:
        session_id: Session ID
        request_body: Vote submission
        service: Deliberation service

    Returns:
        Vote acceptance and count info
    """
    logger.info(
        f"Vote submission for session {session_id}",
        extra={"user_id": request_body.user_id, "round_id": request_body.round_id},
    )

    try:
        # Create vote
        vote = VoteV1(
            user_id=request_body.user_id,
            round_id=request_body.round_id,
            rankings=request_body.rankings,
        )

        accepted, vote_info = await service.submit_vote(
            session_id=session_id,
            user_id=request_body.user_id,
            round_id=request_body.round_id,
            vote=vote,
        )

        return SubmitVoteResponseV1(
            vote_id=vote_info["vote_id"],
            accepted=accepted,
            vote_count=vote_info["vote_count"],
            awaiting_votes_from=vote_info["awaiting_votes_from"],
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Vote submission failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vote submission failed: {str(e)}",
        )


@router.post(
    "/{session_id}/advance",
    response_model=AdvanceRoundResponseV1,
    status_code=status.HTTP_200_OK,
    summary="Advance to next round",
    description="""
Advance deliberation to next round.

**Round Progression:**
- Submission → Synthesis (system generates creative options)
- Synthesis → Voting (participants vote anonymously)
- Voting → Check convergence
  - If converged: Session complete
  - If needs refinement: Refinement round
  - Otherwise: New submission round

**Convergence Criteria:**
- Agreement level ≥ threshold
- Causal quality ≥ threshold
- No unresolved minority evidence
- Overall quality score ≥ minimum
""",
)
async def advance_round(
    session_id: str,
    request_body: AdvanceRoundRequestV1,
    service: DeliberationService = Depends(get_deliberation_service),
) -> AdvanceRoundResponseV1:
    """Advance to next round.

    Args:
        session_id: Session ID
        request_body: Advance request
        service: Deliberation service

    Returns:
        Next round info or final outcome
    """
    logger.info(
        f"Advancing round for session {session_id}",
        extra={"current_round": request_body.current_round_id},
    )

    try:
        next_round, convergence, complete = await service.advance_round(
            session_id=session_id,
            current_round_id=request_body.current_round_id,
        )

        # Get session for final outcome
        session = service.sessions.get(session_id)

        return AdvanceRoundResponseV1(
            next_round=next_round,
            convergence_check=convergence,
            session_complete=complete,
            final_outcome=session.final_outcome if complete else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Round advancement failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Round advancement failed: {str(e)}",
        )


@router.get(
    "/{session_id}/status",
    response_model=DeliberationStatusResponseV1,
    status_code=status.HTTP_200_OK,
    summary="Get session status",
)
async def get_session_status(
    session_id: str,
    service: DeliberationService = Depends(get_deliberation_service),
) -> DeliberationStatusResponseV1:
    """Get current deliberation session status.

    Args:
        session_id: Session ID
        service: Deliberation service

    Returns:
        Session status with current round and next action
    """
    session = service.sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    current_round = session.rounds[-1]

    # Determine next action
    if session.status == "converged":
        next_action = "Session complete - decision reached"
    elif current_round.round_type == "submission":
        submitted = len(current_round.submissions or [])
        total = len(session.participants)
        next_action = f"Awaiting submissions ({submitted}/{total})"
    elif current_round.round_type == "synthesis":
        next_action = "Review synthesis options and proceed to voting"
    elif current_round.round_type == "voting":
        voted = len(current_round.votes or [])
        total = len(session.participants)
        next_action = f"Awaiting votes ({voted}/{total})"
    elif current_round.round_type == "refinement":
        next_action = "Review conflicts and submit refined positions"
    else:
        next_action = "Unknown"

    # Determine who hasn't submitted
    awaiting = []
    if current_round.round_type in ["submission", "refinement"]:
        submitted_users = {s.user_id for s in (current_round.submissions or [])}
        awaiting = [p.user_id for p in session.participants if p.user_id not in submitted_users]
    elif current_round.round_type == "voting":
        # Can't reveal who hasn't voted (anonymous)
        voted_count = len(current_round.votes or [])
        awaiting = [f"anonymous_user_{i}" for i in range(len(session.participants) - voted_count)]

    return DeliberationStatusResponseV1(
        session=session,
        current_round=current_round,
        next_action=next_action,
        awaiting_input_from=awaiting,
    )


@router.get(
    "/{session_id}/history",
    response_model=DeliberationHistoryResponseV1,
    status_code=status.HTTP_200_OK,
    summary="Get deliberation history",
    description="""
Get complete deliberation history for audit trail.

**Includes:**
- Timeline of all events
- Detailed breakdown of each round
- All inputs, options, votes (decrypted after rounds close)
- Convergence assessments

**Use Cases:**
- "Why did we choose option X?" → full deliberation journey
- "Who raised concern Y?" → round + reasoning
- "What evidence supported decision?" → causal paths from all inputs
""",
)
async def get_session_history(
    session_id: str,
    service: DeliberationService = Depends(get_deliberation_service),
) -> DeliberationHistoryResponseV1:
    """Get complete deliberation history.

    Args:
        session_id: Session ID
        service: Deliberation service

    Returns:
        Complete history with timeline and round details
    """
    session = service.sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Build timeline
    timeline = []
    for round_obj in session.rounds:
        # Round start
        timeline.append(
            DeliberationTimelineEventV1(
                timestamp=round_obj.started_at,
                event_type=f"round_start_{round_obj.round_type}",
                round_number=round_obj.round_number,
                description=f"Round {round_obj.round_number} ({round_obj.round_type}) started",
                actor="system",
            )
        )

        # Submissions
        if round_obj.submissions:
            for submission in round_obj.submissions:
                timeline.append(
                    DeliberationTimelineEventV1(
                        timestamp=submission.submitted_at,
                        event_type="submission",
                        round_number=round_obj.round_number,
                        description=f"Perspective submitted",
                        actor=submission.user_id,
                    )
                )

        # Synthesis
        if round_obj.synthesis_options:
            timeline.append(
                DeliberationTimelineEventV1(
                    timestamp=round_obj.started_at,  # Approximate
                    event_type="synthesis",
                    round_number=round_obj.round_number,
                    description=f"Generated {len(round_obj.synthesis_options)} synthesis options",
                    actor="system",
                )
            )

        # Votes
        if round_obj.votes:
            for vote in round_obj.votes:
                timeline.append(
                    DeliberationTimelineEventV1(
                        timestamp=vote.submitted_at,
                        event_type="vote",
                        round_number=round_obj.round_number,
                        description="Vote submitted (anonymous)",
                        actor="anonymous",
                    )
                )

        # Round end
        if round_obj.completed_at:
            timeline.append(
                DeliberationTimelineEventV1(
                    timestamp=round_obj.completed_at,
                    event_type=f"round_end_{round_obj.round_type}",
                    round_number=round_obj.round_number,
                    description=f"Round {round_obj.round_number} completed",
                    actor="system",
                )
            )

    # Build round details
    round_details = []
    for round_obj in session.rounds:
        # Compute vote summary if voting round
        votes_summary = None
        if round_obj.round_type == "voting" and round_obj.votes:
            votes_summary = service._compute_vote_summary(round_obj, round_obj.votes)

        round_details.append(
            RoundDetailsV1(
                round_id=round_obj.round_id,
                round_type=round_obj.round_type,
                inputs=round_obj.submissions,
                synthesis_options=round_obj.synthesis_options,
                votes=votes_summary,
                convergence=round_obj.convergence_status,
            )
        )

    return DeliberationHistoryResponseV1(
        session=session,
        timeline=sorted(timeline, key=lambda x: x.timestamp),
        round_details=round_details,
    )


@router.get(
    "/{session_id}/health",
    status_code=status.HTTP_200_OK,
    summary="Health check for session",
)
async def session_health(
    session_id: str,
    service: DeliberationService = Depends(get_deliberation_service),
) -> JSONResponse:
    """Check if session exists and is healthy.

    Args:
        session_id: Session ID
        service: Deliberation service

    Returns:
        Health status
    """
    session = service.sessions.get(session_id)
    if not session:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": "not_found", "session_id": session_id},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "session_id": session_id,
            "session_status": session.status,
            "current_round": session.rounds[-1].round_number if session.rounds else 0,
        },
    )
