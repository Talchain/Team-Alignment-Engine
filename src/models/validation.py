"""Validation-related models."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from src.models.enums import ValidationStatus, EvidenceLevel, ImpactLevel


class AssumptionStrength(BaseModel):
    """Assumption strength assessment."""

    assumption_id: str  # Stable ID matching ISL node
    assumption_text: str
    evidence_strength: EvidenceLevel
    impact_if_wrong: ImpactLevel
    source: Optional[str] = None


class OutcomeRange(BaseModel):
    """Outcome range prediction."""

    metric: str
    p10: float
    p50: float
    p90: float
    unit: str  # %, $M, days, etc.
    confidence: EvidenceLevel


class CausalValidation(BaseModel):
    """Causal validation result model."""

    validation_id: UUID = Field(default_factory=uuid4)
    option_id: UUID

    # Validation status
    is_identifiable: bool
    validation_status: ValidationStatus
    data_sufficiency: str = "sufficient"  # sufficient, limited, insufficient

    # Predictions (from ISL)
    predicted_outcomes: Dict[str, OutcomeRange]

    # Assumptions (with stable IDs)
    key_assumptions: List[AssumptionStrength]

    # Warnings
    warnings: List[str] = Field(default_factory=list)
    quality_concerns: List[str] = Field(default_factory=list)

    # Sensitivity (if tested)
    sensitivity_factors: List[Dict] = Field(default_factory=list)

    # Raw ISL response (for debugging)
    isl_response: Dict
    isl_request_id: Optional[str] = None

    validated_at: datetime = Field(default_factory=datetime.utcnow)
