"""Fit calculation models."""

from pydantic import BaseModel, Field
from typing import Dict, List
from datetime import datetime
from uuid import UUID, uuid4

from src.models.enums import FitLevel, ConsensusLevel


class StakeholderFitScore(BaseModel):
    """Fit score for a single stakeholder."""

    stakeholder_id: UUID
    fit_score: float = Field(..., ge=0, le=1)
    fit_level: FitLevel

    satisfies_goals: List[str]
    violates_constraints: List[str]
    explanation: str


class OptionFit(BaseModel):
    """Fit analysis for an option."""

    fit_id: UUID = Field(default_factory=uuid4)
    option_id: UUID

    stakeholder_fits: Dict[str, StakeholderFitScore]  # user_id -> fit
    overall_alignment: float = Field(..., ge=0, le=1)
    consensus_level: ConsensusLevel

    calculated_at: datetime = Field(default_factory=datetime.utcnow)
