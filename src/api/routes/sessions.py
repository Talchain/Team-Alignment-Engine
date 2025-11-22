"""Session management endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from src.models import SessionStatus, DecisionType, AlignmentMode
from src.services import SessionManager
from src.auth import get_current_active_user, require_role, User

router = APIRouter(prefix="/api/v1/alignment/sessions", tags=["sessions"])

# Global service instances (would use dependency injection in production)
session_manager = SessionManager()


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    team_id: UUID
    decision_topic: str = Field(..., min_length=1, max_length=500, description="Decision topic")
    decision_context: str = Field(..., min_length=1, max_length=2000, description="Decision context")
    decision_type: DecisionType = DecisionType.CUSTOM
    alignment_mode: AlignmentMode = AlignmentMode.EVIDENCE_BACKED
    stakeholders: List[Dict[str, str]] = Field(..., min_items=1, max_items=50, description="Stakeholders")
    scenario_model_id: Optional[UUID] = None


class CreateSessionResponse(BaseModel):
    """Response model for session creation."""

    session_id: UUID
    status: SessionStatus
    invite_links: Dict[str, str]


class SessionResponse(BaseModel):
    """Session status response."""

    session_id: UUID
    status: SessionStatus
    decision_topic: str
    alignment_mode: AlignmentMode
    progress: Dict
    shared_ground: Optional[Dict] = None
    disagreement_map: Optional[Dict] = None


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_active_user)
) -> CreateSessionResponse:
    """
    Create new alignment session.

    Requires authentication. User must be team_lead or admin role.
    Automatically includes baseline "Status Quo" option.
    Configures goal dimensions based on decision_type template.
    """
    # Verify user has permission to create sessions for this team
    if current_user.role not in ["admin", "team_lead"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required role: admin or team_lead"
        )

    # Create session
    session = await session_manager.create(
        team_id=request.team_id,
        decision_topic=request.decision_topic,
        decision_context=request.decision_context,
        decision_type=request.decision_type,
        alignment_mode=request.alignment_mode,
        stakeholders=request.stakeholders,
        created_by=current_user.user_id,
        scenario_model_id=request.scenario_model_id,
    )

    # Generate invite links
    invite_links = await session_manager.generate_invite_links(session.session_id)

    # TODO: Create baseline option automatically

    return CreateSessionResponse(
        session_id=session.session_id,
        status=session.status,
        invite_links=invite_links,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user)
) -> SessionResponse:
    """Get session status and progress. Requires authentication."""
    session = await session_manager.get(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # TODO: Get actual counts from managers
    progress = {
        "profiles_collected": 0,
        "profiles_total": len(session.stakeholders),
        "options_proposed": 0,
        "options_validated": 0,
        "current_phase": session.status,
    }

    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        decision_topic=session.decision_topic,
        alignment_mode=session.alignment_mode,
        progress=progress,
        shared_ground=session.shared_ground,
        disagreement_map=session.disagreement_map,
    )


@router.patch("/{session_id}/status")
async def update_session_status(
    session_id: UUID,
    new_status: SessionStatus,
    current_user: User = Depends(require_role(["admin", "team_lead"]))
):
    """Update session status. Requires admin or team_lead role."""
    session = await session_manager.get(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    await session_manager.update_status(session_id, new_status)

    return {"session_id": session_id, "status": new_status}
