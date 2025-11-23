"""Preference elicitation models (Phase 2A: ActiVA).

Models for counterfactual-based value elicitation using active learning.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from uuid import uuid4


# ============================================================================
# COUNTERFACTUAL SCENARIO MODELS
# ============================================================================


class CounterfactualScenarioV1(BaseModel):
    """A counterfactual scenario pair for value elicitation.

    Presents two alternative outcomes that differ on specific value dimensions.
    """

    scenario_id: str = Field(
        default_factory=lambda: f"scenario-{uuid4()}",
        description="Unique scenario ID"
    )
    question: str = Field(
        ...,
        max_length=500,
        description="Question prompt for user"
    )

    # Option A
    option_a: str = Field(
        ...,
        max_length=1000,
        description="First outcome description"
    )
    option_a_values: Dict[str, float] = Field(
        ...,
        description="Value scores for option A (dimension → score 0-1)"
    )

    # Option B
    option_b: str = Field(
        ...,
        max_length=1000,
        description="Alternative outcome description"
    )
    option_b_values: Dict[str, float] = Field(
        ...,
        description="Value scores for option B (dimension → score 0-1)"
    )

    # Metadata
    discriminating_dimensions: List[str] = Field(
        ...,
        description="Value dimensions that differ most between options"
    )
    expected_information_gain: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Expected information gain from this question"
    )


class PreferenceResponseV1(BaseModel):
    """User's response to a counterfactual scenario."""

    scenario_id: str = Field(..., description="Scenario ID")
    user_id: str = Field(..., description="User ID")

    choice: Literal["A", "B", "indifferent"] = Field(
        ...,
        description="User's choice"
    )
    strength: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Strength of preference (0=indifferent, 1=strong)"
    )

    response_time_ms: Optional[int] = Field(
        None,
        description="Time taken to respond (for quality assessment)"
    )
    responded_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Response timestamp"
    )


# ============================================================================
# VALUE MODEL
# ============================================================================


class ValueDimensionV1(BaseModel):
    """A single value dimension with estimated weight."""

    dimension: str = Field(..., description="Value dimension name")
    weight: float = Field(..., ge=0.0, le=1.0, description="Estimated weight (0-1)")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this weight estimate"
    )

    # Bayesian posterior parameters
    alpha: float = Field(..., gt=0.0, description="Dirichlet alpha parameter")
    samples_count: int = Field(default=0, description="Number of samples observed")


class ValueModelV1(BaseModel):
    """User's inferred value model from preference responses."""

    user_id: str = Field(..., description="User ID")
    dimensions: List[ValueDimensionV1] = Field(
        ...,
        description="Value dimensions with weights"
    )

    convergence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How well converged the model is (0=uncertain, 1=confident)"
    )
    questions_asked: int = Field(..., ge=0, description="Number of questions asked")

    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Last update timestamp"
    )


# ============================================================================
# PREFERENCE ELICITATION SESSION
# ============================================================================


class PreferenceElicitationSessionV1(BaseModel):
    """Session for eliciting user values through counterfactual questions."""

    session_id: str = Field(
        default_factory=lambda: f"pref-session-{uuid4()}",
        description="Unique session ID"
    )
    user_id: str = Field(..., description="User ID")
    decision_context: str = Field(
        ...,
        max_length=1000,
        description="Decision context for elicitation"
    )

    # Value dimensions to elicit
    value_dimensions: List[str] = Field(
        ...,
        min_length=2,
        description="Value dimensions to elicit weights for"
    )

    # Session state
    status: Literal["active", "converged", "abandoned"] = Field(
        default="active",
        description="Session status"
    )
    scenarios_presented: List[CounterfactualScenarioV1] = Field(
        default_factory=list,
        description="Scenarios shown to user"
    )
    responses: List[PreferenceResponseV1] = Field(
        default_factory=list,
        description="User responses"
    )

    # Current value model
    value_model: Optional[ValueModelV1] = Field(
        None,
        description="Current estimated value model"
    )

    # Convergence criteria
    target_convergence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Target convergence score to stop"
    )
    max_questions: int = Field(
        default=7,
        ge=1,
        le=20,
        description="Maximum questions to ask"
    )

    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Session creation timestamp"
    )
    completed_at: Optional[str] = Field(
        None,
        description="Session completion timestamp"
    )


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================


class StartPreferenceElicitationRequestV1(BaseModel):
    """Request to start preference elicitation session."""

    user_id: str = Field(..., description="User ID")
    decision_context: str = Field(
        ...,
        max_length=1000,
        description="Decision context (e.g., 'feature prioritization for Q1')"
    )
    value_dimensions: List[str] = Field(
        ...,
        min_length=2,
        description="Value dimensions to elicit (e.g., ['user_growth', 'revenue', 'eng_cost'])"
    )
    target_convergence: Optional[float] = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Target convergence score"
    )
    max_questions: Optional[int] = Field(
        default=7,
        ge=1,
        le=20,
        description="Max questions to ask"
    )


class StartPreferenceElicitationResponseV1(BaseModel):
    """Response with first scenario."""

    session_id: str = Field(..., description="Session ID")
    first_scenario: CounterfactualScenarioV1 = Field(
        ...,
        description="First counterfactual scenario"
    )
    progress: str = Field(
        ...,
        description="Progress message (e.g., 'Question 1 of up to 7')"
    )


class SubmitPreferenceResponseRequestV1(BaseModel):
    """Request to submit preference response."""

    scenario_id: str = Field(..., description="Scenario ID")
    user_id: str = Field(..., description="User ID")
    choice: Literal["A", "B", "indifferent"] = Field(
        ...,
        description="User's choice"
    )
    strength: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Strength of preference"
    )
    response_time_ms: Optional[int] = Field(
        None,
        description="Response time in milliseconds"
    )


class SubmitPreferenceResponseResponseV1(BaseModel):
    """Response after submitting preference."""

    accepted: bool = Field(..., description="Whether response was accepted")
    next_scenario: Optional[CounterfactualScenarioV1] = Field(
        None,
        description="Next scenario (None if session complete)"
    )
    session_complete: bool = Field(..., description="Whether session has converged")
    value_model: Optional[ValueModelV1] = Field(
        None,
        description="Current value model (if session complete)"
    )
    progress: str = Field(
        ...,
        description="Progress message"
    )


class GetValueModelResponseV1(BaseModel):
    """Response with user's value model."""

    value_model: ValueModelV1 = Field(..., description="User's value model")
    session_summary: Dict[str, any] = Field(
        ...,
        description="Session summary (questions_asked, convergence_score, etc.)"
    )
