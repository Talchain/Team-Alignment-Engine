"""Concern-related models."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

from src.models.enums import ConcernStatus


class SensitivityResult(BaseModel):
    """Sensitivity analysis result."""

    factor_tested: str
    baseline_outcome: float
    alternative_outcome: float
    outcome_delta: float
    is_material: bool
    explanation: str


class MinorityConcern(BaseModel):
    """Minority concern model."""

    concern_id: UUID = Field(default_factory=uuid4)
    option_id: UUID
    raised_by: UUID

    concern_text: str = Field(..., max_length=1000)
    concern_type: str  # assumption, constraint, outcome
    assumption_id_tested: Optional[str] = None  # Link to assumption

    # Validation
    sensitivity_tested: bool = False
    causal_validation: Optional[SensitivityResult] = None

    # Resolution
    status: ConcernStatus = ConcernStatus.RAISED
    resolution: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
