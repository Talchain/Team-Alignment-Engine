"""Phase C data models for intelligent assistance and learning."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID, uuid4


class AIGenerationMetadata(BaseModel):
    """Metadata for AI-generated options."""

    generation_mode: str  # creative_synthesis, constraint_satisfaction
    tension_addressed: Optional[str] = None
    perspective_weights: Optional[Dict[str, float]] = None
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    cee_request_id: Optional[str] = None


class SynthesisMetadata(BaseModel):
    """Metadata for synthesized hybrid options."""

    source_option_ids: List[UUID]
    elements_preserved: List[str]
    elements_sacrificed: List[str]
    compatibility_score: float
    synthesis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class TuningMetadata(BaseModel):
    """Metadata for tuned options."""

    source_option_id: UUID
    concern_addressed: UUID
    parameters_adjusted: List[Dict]
    preserved_elements: List[str]
    tuning_timestamp: datetime = Field(default_factory=datetime.utcnow)


class AssumptionValidationRecord(BaseModel):
    """Record of assumption validation testing."""

    validation_id: UUID = Field(default_factory=uuid4)
    assumption_id: str
    session_id: UUID
    validation_method: str  # a_b_test, technical_spike, user_research, etc.
    validation_result: str  # confirmed, rejected, modified
    validation_notes: str
    validated_at: datetime
    validated_by: UUID
    updated_assumption: Optional[Dict] = None


class TestStrategy(BaseModel):
    """Recommended strategy for testing an assumption."""

    strategy_type: str  # a_b_test, spike, research, analysis
    description: str
    estimated_time: str  # "1-2 weeks"
    estimated_cost: str  # "Low", "Medium", "High"
    feasibility: str  # "Easy", "Medium", "Hard"
    success_criteria: List[str]


class OutcomeComparison(BaseModel):
    """Comparison of predicted vs actual outcomes."""

    metric: str
    predicted_p50: float
    predicted_range: List[float]  # [p10, p90]
    actual: float
    category: str  # within_range, above_range, below_range
    relative_error: float
    accuracy: float


class DecisionRetrospective(BaseModel):
    """Retrospective analysis of decision outcomes."""

    retrospective_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    brief_id: UUID

    # Actual outcomes
    actual_outcomes: Dict[str, float]
    outcome_comparison: Dict

    # Assumption analysis
    assumption_results: List[Dict]
    assumption_analysis: Dict

    # Narrative and lessons
    narrative: str
    lessons_learned: List[Dict]

    # Metadata
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    recorded_by: Optional[UUID] = None


class SessionChainLink(BaseModel):
    """Link in a multi-round decision chain."""

    round_number: int
    session_id: UUID
    decision_topic: str
    created_at: datetime
    completed_at: Optional[datetime]
    chosen_option: Optional[Dict]
    retrospective_recorded: bool
    reopen_reason: Optional[str]
