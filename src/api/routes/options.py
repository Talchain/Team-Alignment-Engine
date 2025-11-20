"""Option management endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Optional
from uuid import UUID

from src.models import SessionStatus, ProposedOption, DecisionTemplate, AlignmentMode
from src.services import (
    SessionManager,
    ProfileExtractor,
    FitCalculator,
    ValidationOrchestrator,
)

router = APIRouter(prefix="/api/v1/alignment/sessions", tags=["options"])

# Global service instances
session_manager = SessionManager()
profile_extractor = ProfileExtractor()
fit_calculator = FitCalculator()
validation_orchestrator = ValidationOrchestrator()

# In-memory option storage (would use database in production)
options: Dict[UUID, ProposedOption] = {}


class ProposeOptionRequest(BaseModel):
    """Request model for proposing an option."""

    proposed_by: str
    title: str
    description: str
    expected_outcome: str
    causal_rationale: str
    addresses_goals: List[str]
    trade_offs: List[str]
    key_assumptions: List[Dict[str, str]]
    scenario_link: Optional[Dict] = None


@router.post("/{session_id}/options", status_code=status.HTTP_201_CREATED)
async def propose_option(session_id: UUID, request: ProposeOptionRequest):
    """
    Propose option for consideration.

    Immediately triggers:
    1. Fit calculation (vs all profiles)
    2. ISL validation (if evidence_backed mode)
    """
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session.status != SessionStatus.DELIBERATING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not in deliberating phase",
        )

    # Create option
    option = ProposedOption(
        session_id=session_id,
        proposed_by=request.proposed_by,
        title=request.title,
        description=request.description,
        expected_outcome=request.expected_outcome,
        causal_rationale=request.causal_rationale,
        addresses_goals=request.addresses_goals,
        trade_offs=request.trade_offs,
        key_assumptions=request.key_assumptions,
        scenario_link=request.scenario_link,
        is_baseline=False,
    )

    options[option.option_id] = option

    # Calculate fit scores
    profiles = await profile_extractor.get_all(session_id)
    fit = await fit_calculator.calculate_all_fits(option, profiles)

    # Trigger ISL validation if evidence_backed mode
    validation_in_progress = False
    if session.alignment_mode == AlignmentMode.EVIDENCE_BACKED:
        option.status = "validating"
        validation_in_progress = True

        # Get outcome metrics from template
        template = DecisionTemplate.get_template(session.decision_type)

        # Async validation (in production, queue this)
        validation = await validation_orchestrator.validate_option(
            option,
            template.default_outcome_metrics,
            "quarterly",  # Default time horizon
        )
        option.status = "validated"

    options[option.option_id] = option

    return {
        "option_id": option.option_id,
        "status": option.status,
        "validation_in_progress": validation_in_progress,
    }


@router.get("/{session_id}/options/{option_id}")
async def get_option_with_validation(session_id: UUID, option_id: UUID):
    """
    Get option with fit analysis and causal validation.

    Returns three-tier structure:
    - Tier 1: Summary (default)
    - Tier 2: Detailed (on expand)
    - Tier 3: Full ISL output (expert view)
    """
    option = options.get(option_id)
    if not option or option.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Option {option_id} not found",
        )

    # Get fit analysis
    fit = await fit_calculator.get_by_option(option_id)

    # Get validation
    validation = await validation_orchestrator.get_by_option(option_id)

    # Tier 1: Summary
    summary = {
        "option_id": option.option_id,
        "title": option.title,
        "description": option.description,
        "is_baseline": option.is_baseline,
    }

    if fit:
        summary["fit_summary"] = {
            "overall_alignment": fit.overall_alignment,
            "consensus_level": fit.consensus_level,
            "stakeholder_fits": {
                user_id: {
                    "fit_level": fit_score.fit_level,
                    "explanation": fit_score.explanation,
                }
                for user_id, fit_score in fit.stakeholder_fits.items()
            },
        }

    if validation:
        summary["validation_summary"] = {
            "status": validation.validation_status,
            "data_sufficiency": validation.data_sufficiency,
            "key_outcomes": {
                metric: f"{outcome.p50:.1%} (range: {outcome.p10:.1%} to {outcome.p90:.1%})"
                for metric, outcome in validation.predicted_outcomes.items()
            },
            "warnings": validation.warnings,
        }

    return {
        "tier1_summary": summary,
        "tier2_details": {
            "option": option.dict(),
            "fit_analysis": fit.dict() if fit else None,
            "causal_validation": validation.dict() if validation else None,
        },
    }
