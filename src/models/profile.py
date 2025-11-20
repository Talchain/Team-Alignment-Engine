"""Profile-related models."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict
from datetime import datetime
from uuid import UUID, uuid4

from src.models.enums import StakeholderRole, RiskLevel, TimeHorizon


class StakeholderProfile(BaseModel):
    """Stakeholder profile model."""

    profile_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    user_id: UUID
    role: str  # PM, Designer, Engineer, etc.
    stakeholder_role: StakeholderRole = StakeholderRole.STAKEHOLDER

    # Raw input
    desired_outcome: str = Field(..., max_length=1000)
    key_concerns: List[str] = Field(..., max_length=5)
    preferred_option: Optional[str] = Field(None, max_length=1000)

    # Extracted profile (via CEE)
    goal_weights: Dict[str, float]  # 0-1 per dimension
    risk_tolerance: RiskLevel
    time_horizon: TimeHorizon
    must_have_constraints: List[str] = Field(default_factory=list)
    red_lines: List[str] = Field(default_factory=list)

    # Extraction metadata
    extraction_confidence: float = Field(default=1.0, ge=0, le=1)
    extraction_source: str = "cee"  # or "heuristic" if degraded

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("goal_weights")
    @classmethod
    def validate_goal_weights(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate goal weights are between 0-1."""
        assert all(0 <= w <= 1 for w in v.values()), "Goal weights must be 0-1"
        return v


# Import Optional after other imports to avoid circular dependency
from typing import Optional
