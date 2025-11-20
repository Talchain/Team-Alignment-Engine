"""Perspective collection endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Optional
from uuid import UUID

from src.models import StakeholderRole, DecisionTemplate
from src.services import SessionManager, ProfileExtractor

router = APIRouter(prefix="/api/v1/alignment/sessions", tags=["perspectives"])

# Global service instances
session_manager = SessionManager()
profile_extractor = ProfileExtractor()


class SubmitPerspectiveRequest(BaseModel):
    """Request model for submitting perspective."""

    user_id: UUID
    role: str
    desired_outcome: str
    key_concerns: List[str]
    preferred_option: Optional[str] = None
    stakeholder_role: StakeholderRole = StakeholderRole.STAKEHOLDER


@router.post("/{session_id}/perspectives", status_code=status.HTTP_201_CREATED)
async def submit_perspective(session_id: UUID, request: SubmitPerspectiveRequest):
    """
    Submit stakeholder perspective.

    Calls CEE to extract structured profile from free-text input.
    Uses decision_type template to guide extraction.
    """
    # Validate session
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session.status != SessionStatus.COLLECTING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not in collecting phase",
        )

    # Get template for guided extraction
    template = DecisionTemplate.get_template(session.decision_type)

    # Create profile with CEE extraction
    profile = await profile_extractor.create(
        session_id=session_id,
        user_id=request.user_id,
        role=request.role,
        stakeholder_role=request.stakeholder_role,
        desired_outcome=request.desired_outcome,
        key_concerns=request.key_concerns,
        preferred_option=request.preferred_option,
        goal_dimensions=template.goal_dimensions,
        decision_context=session.decision_context,
    )

    # Check if all profiles collected
    expected_count = len(session.stakeholders)
    if await profile_extractor.all_collected(session_id, expected_count):
        # Trigger analysis phase
        await session_manager.update_status(session_id, SessionStatus.ANALYZING)
        # TODO: Trigger async analysis

    return {
        "profile_id": profile.profile_id,
        "status": "processing",
        "session_status": session.status,
    }


@router.get("/{session_id}/perspectives/{profile_id}")
async def get_profile(session_id: UUID, profile_id: UUID):
    """Get extracted profile with raw input."""
    profile = await profile_extractor.get(profile_id)

    if not profile or profile.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {profile_id} not found",
        )

    return {
        "profile_id": profile.profile_id,
        "user_id": profile.user_id,
        "role": profile.role,
        "raw_input": {
            "desired_outcome": profile.desired_outcome,
            "key_concerns": profile.key_concerns,
            "preferred_option": profile.preferred_option,
        },
        "extracted_profile": {
            "goal_weights": profile.goal_weights,
            "risk_tolerance": profile.risk_tolerance,
            "time_horizon": profile.time_horizon,
            "must_have_constraints": profile.must_have_constraints,
            "red_lines": profile.red_lines,
        },
        "extraction_metadata": {
            "confidence": profile.extraction_confidence,
            "source": profile.extraction_source,
        },
    }


# Import SessionStatus after models
from src.models import SessionStatus
