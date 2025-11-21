"""Option-related models."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
from datetime import datetime
from uuid import UUID, uuid4


class ProposedOption(BaseModel):
    """Proposed option model."""

    option_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    proposed_by: str  # UUID or "ai_generated" or "baseline"
    round_number: int = 1

    # Content
    title: str = Field(..., max_length=200)
    description: str = Field(..., max_length=2000)
    expected_outcome: str = Field(..., max_length=1000)
    causal_rationale: str = Field(..., max_length=2000)

    # Structure
    addresses_goals: List[str]
    trade_offs: List[str]
    key_assumptions: List[Dict]  # [{assumption_id, assumption_text}]

    # Scenario link (CRITICAL)
    scenario_link: Optional[Dict] = None  # {model_id, parameter_deltas}

    # Special flags
    is_baseline: bool = False  # Status quo option

    status: str = "proposed"  # proposed, validating, validated, rejected
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Phase C: AI-powered option metadata
    ai_generation_metadata: Optional[Dict] = None  # AIGenerationMetadata
    synthesis_metadata: Optional[Dict] = None  # SynthesisMetadata
    tuning_metadata: Optional[Dict] = None  # TuningMetadata

    @field_validator("key_assumptions")
    @classmethod
    def validate_assumptions(cls, v: List[Dict]) -> List[Dict]:
        """Validate assumptions have required fields."""
        for assumption in v:
            assert "assumption_id" in assumption, "Must have assumption_id"
            assert "assumption_text" in assumption, "Must have assumption_text"
        return v
