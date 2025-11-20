"""Decision finalization endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from src.models import StakeholderRole, SessionStatus, AssumptionStrength
from src.services import (
    SessionManager,
    ProfileExtractor,
    FitCalculator,
    ValidationOrchestrator,
    ConcernValidator,
    DecisionDocumenter,
)
from src.api.routes.options import options

router = APIRouter(prefix="/api/v1/alignment/sessions", tags=["decisions"])

# Global service instances
session_manager = SessionManager()
profile_extractor = ProfileExtractor()
fit_calculator = FitCalculator()
validation_orchestrator = ValidationOrchestrator()
concern_validator = ConcernValidator()
decision_documenter = DecisionDocumenter()


class RecordDecisionRequest(BaseModel):
    """Request model for recording a decision."""

    decided_by: UUID
    chosen_option_id: UUID
    decision_rationale: str
    stakeholder_support: Dict[str, str]  # user_id -> support_level
    accepted_assumptions: List[Dict]
    monitored_risks: List[str]
    minority_concerns_addressed: List[str]
    review_date: datetime
    success_criteria: List[str]
    monitoring_plan: List[str]
    scenario_snapshot: Optional[Dict] = None


class RateDecisionRequest(BaseModel):
    """Request model for rating a decision."""

    rating: int  # 1-10
    notes: Optional[str] = None


@router.post("/{session_id}/decide", status_code=status.HTTP_201_CREATED)
async def record_decision(session_id: UUID, request: RecordDecisionRequest):
    """
    Record final decision with full audit trail.

    Requires owner/facilitator role.
    """
    # Validate permissions
    profile = await profile_extractor.get_by_user(session_id, request.decided_by)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found for user {request.decided_by}",
        )

    if profile.stakeholder_role not in [
        StakeholderRole.OWNER,
        StakeholderRole.FACILITATOR,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner/facilitator can finalize decision",
        )

    # Get session
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Get chosen option
    option = options.get(request.chosen_option_id)
    if not option or option.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Option {request.chosen_option_id} not found",
        )

    # Get validation
    validation = await validation_orchestrator.get_by_option(
        request.chosen_option_id
    )

    # Get concerns
    concerns = await concern_validator.get_all_by_option(request.chosen_option_id)

    # Calculate consensus strength
    consensus_strength = await fit_calculator.calculate_consensus_strength(
        request.stakeholder_support
    )

    # Convert accepted assumptions to AssumptionStrength objects
    accepted_assumptions = []
    for assump_dict in request.accepted_assumptions:
        from src.models import EvidenceLevel, ImpactLevel

        accepted_assumptions.append(
            AssumptionStrength(
                assumption_id=assump_dict.get("assumption_id", ""),
                assumption_text=assump_dict.get("assumption_text", ""),
                evidence_strength=EvidenceLevel(
                    assump_dict.get("evidence_strength", "medium")
                ),
                impact_if_wrong=ImpactLevel(
                    assump_dict.get("impact_if_wrong", "medium")
                ),
                source=assump_dict.get("source"),
            )
        )

    # Create decision brief
    brief = await decision_documenter.create(
        session_id=session_id,
        chosen_option=option.dict(),
        decision_rationale=request.decision_rationale,
        stakeholder_support=request.stakeholder_support,
        consensus_strength=consensus_strength,
        validated_outcomes=(
            validation.predicted_outcomes if validation else {}
        ),
        accepted_assumptions=accepted_assumptions,
        monitored_risks=request.monitored_risks,
        minority_concerns_raised=[c.dict() for c in concerns],
        minority_concerns_addressed=request.minority_concerns_addressed,
        review_date=request.review_date,
        success_criteria=request.success_criteria,
        monitoring_plan=request.monitoring_plan,
        participants=[UUID(s["user_id"]) for s in session.stakeholders],
        scenario_model_id=session.scenario_model_id,
        scenario_snapshot=request.scenario_snapshot,
    )

    # Update session
    await session_manager.update_status(session_id, SessionStatus.COMPLETE)
    await session_manager.set_selected_option(session_id, request.chosen_option_id)

    return {
        "brief_id": brief.brief_id,
        "session_id": session_id,
        "status": SessionStatus.COMPLETE,
        "decision_brief_url": f"/api/v1/alignment/sessions/{session_id}/brief",
    }


@router.get("/{session_id}/brief")
async def export_decision_brief(session_id: UUID):
    """Export complete decision brief."""
    brief = await decision_documenter.get_by_session(session_id)

    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No decision brief found for session {session_id}",
        )

    # Mark as exported
    brief.exported_at = datetime.utcnow()
    await decision_documenter.update(brief)

    return brief.dict()


@router.post("/{session_id}/brief/rate")
async def rate_decision_quality(session_id: UUID, request: RateDecisionRequest):
    """
    Post-decision quality rating (for learning).

    Called by team after decision plays out.
    """
    brief = await decision_documenter.get_by_session(session_id)

    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No decision brief found for session {session_id}",
        )

    await decision_documenter.rate_decision(
        brief.brief_id, request.rating, request.notes
    )

    return {"status": "recorded", "rating": request.rating}
