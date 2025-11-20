"""Decision-related models."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from src.models.validation import AssumptionStrength, OutcomeRange


class DecisionBrief(BaseModel):
    """Decision brief model."""

    brief_id: UUID = Field(default_factory=uuid4)
    session_id: UUID

    # Decision
    chosen_option: Dict  # Full ProposedOption
    decision_rationale: str = Field(..., max_length=2000)

    # Consensus
    stakeholder_support: Dict[str, str]  # user_id -> support_level
    consensus_strength: float = Field(..., ge=0, le=1)

    # Validation
    validated_outcomes: Dict[str, OutcomeRange]
    accepted_assumptions: List[AssumptionStrength]
    monitored_risks: List[str]

    # Minority perspectives
    minority_concerns_raised: List[Dict]
    minority_concerns_addressed: List[str]

    # Follow-up
    review_date: datetime
    success_criteria: List[str]
    monitoring_plan: List[str]

    # Link back to scenario
    scenario_model_id: Optional[UUID] = None
    scenario_snapshot: Optional[Dict] = None

    # Metadata
    decision_date: datetime = Field(default_factory=datetime.utcnow)
    participants: List[UUID]
    exported_at: Optional[datetime] = None

    # Telemetry (for learning)
    decision_quality_rating: Optional[int] = Field(None, ge=1, le=10)
    post_decision_notes: Optional[str] = None
