"""Minority concern management endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from src.models import StakeholderRole
from src.services import (
    SessionManager,
    ProfileExtractor,
    ConcernValidator,
    ValidationOrchestrator,
)

router = APIRouter(prefix="/api/v1/alignment/sessions", tags=["concerns"])

# Global service instances
session_manager = SessionManager()
profile_extractor = ProfileExtractor()
concern_validator = ConcernValidator()
validation_orchestrator = ValidationOrchestrator()


class FlagConcernRequest(BaseModel):
    """Request model for flagging a concern."""

    raised_by: UUID
    concern_text: str
    concern_type: str  # assumption, constraint, outcome
    assumption_id_tested: Optional[str] = None
    request_sensitivity_test: bool = False
    factor_to_test: Optional[str] = None
    baseline_value: Optional[float] = None
    alternative_value: Optional[float] = None


@router.post("/{session_id}/options/{option_id}/concerns", status_code=status.HTTP_201_CREATED)
async def flag_concern(
    session_id: UUID, option_id: UUID, request: FlagConcernRequest
):
    """
    Flag minority concern for validation.

    Triggers ISL sensitivity analysis if causal concern.
    """
    # Validate permissions
    profile = await profile_extractor.get_by_user(session_id, request.raised_by)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found for user {request.raised_by}",
        )

    if profile.stakeholder_role == StakeholderRole.OBSERVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Observers cannot flag concerns",
        )

    # Create concern
    concern = await concern_validator.create_concern(
        option_id=option_id,
        raised_by=request.raised_by,
        concern_text=request.concern_text,
        concern_type=request.concern_type,
        assumption_id_tested=request.assumption_id_tested,
    )

    # Trigger sensitivity analysis if requested
    if request.request_sensitivity_test and request.factor_to_test:
        validation = await validation_orchestrator.get_by_option(option_id)
        if not validation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Option not yet validated, cannot run sensitivity analysis",
            )

        await concern_validator.validate_concern(
            concern_id=concern.concern_id,
            validation_id=str(validation.validation_id),
            factor=request.factor_to_test,
            baseline_value=request.baseline_value or 0.0,
            alternative_value=request.alternative_value or 0.0,
        )

    return {
        "concern_id": concern.concern_id,
        "status": concern.status,
        "sensitivity_test_initiated": request.request_sensitivity_test,
    }


@router.get("/{session_id}/concerns/{concern_id}")
async def get_concern_validation(session_id: UUID, concern_id: UUID):
    """Get concern with sensitivity analysis results."""
    concern = await concern_validator.get(concern_id)
    if not concern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concern {concern_id} not found",
        )

    return {
        "concern_id": concern.concern_id,
        "raised_by": concern.raised_by,
        "concern_text": concern.concern_text,
        "concern_type": concern.concern_type,
        "sensitivity_result": (
            concern.causal_validation.dict() if concern.causal_validation else None
        ),
        "status": concern.status,
        "resolution": concern.resolution,
    }
