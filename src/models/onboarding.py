"""Onboarding models (Phase 2B: Bayesian Teaching).

Models for efficient team onboarding using decision archetypes.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from uuid import uuid4


# ============================================================================
# DECISION ARCHETYPE MODELS
# ============================================================================


class DecisionArchetypeV1(BaseModel):
    """A decision archetype representing a common decision pattern."""

    archetype_id: str = Field(..., description="Archetype ID")
    name: str = Field(..., description="Archetype name (e.g., 'user_growth_focused')")
    description: str = Field(..., max_length=500, description="Archetype description")

    # Characteristic patterns
    typical_value_weights: Dict[str, float] = Field(
        ...,
        description="Typical value weights for this archetype"
    )
    typical_concerns: List[str] = Field(
        ...,
        description="Common concerns for this archetype"
    )
    typical_constraints: List[str] = Field(
        ...,
        description="Common constraints for this archetype"
    )

    # Examples
    example_decisions: List[str] = Field(
        default_factory=list,
        description="Example decisions this archetype typically makes"
    )


class ArchetypeMatchV1(BaseModel):
    """Match between a user and a decision archetype."""

    archetype: DecisionArchetypeV1 = Field(..., description="Matched archetype")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this match"
    )
    evidence: List[str] = Field(
        ...,
        description="Evidence for this match (e.g., role, past decisions)"
    )


# ============================================================================
# ONBOARDING SESSION MODELS
# ============================================================================


class OnboardingQuestionV1(BaseModel):
    """A question for onboarding."""

    question_id: str = Field(
        default_factory=lambda: f"q-{uuid4()}",
        description="Question ID"
    )
    question_text: str = Field(..., max_length=500, description="Question text")
    question_type: Literal["role", "priority", "constraint", "scenario"] = Field(
        ...,
        description="Question type"
    )

    # Options
    options: List[str] = Field(..., min_length=2, description="Answer options")

    # Bayesian teaching metadata
    expected_information_gain: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Expected information gain from this question"
    )
    discriminates_archetypes: List[str] = Field(
        ...,
        description="Which archetypes this question helps distinguish"
    )


class OnboardingResponseV1(BaseModel):
    """User's response to an onboarding question."""

    question_id: str = Field(..., description="Question ID")
    user_id: str = Field(..., description="User ID")
    selected_option: str = Field(..., description="Selected option")
    response_time_ms: Optional[int] = Field(None, description="Response time")
    responded_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Response timestamp"
    )


class OnboardingProfileV1(BaseModel):
    """User's profile from onboarding."""

    user_id: str = Field(..., description="User ID")

    # Detected archetype
    primary_archetype: Optional[ArchetypeMatchV1] = Field(
        None,
        description="Primary archetype match"
    )
    secondary_archetype: Optional[ArchetypeMatchV1] = Field(
        None,
        description="Secondary archetype (if hybrid)"
    )

    # Inferred preferences
    inferred_value_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Inferred value weights from responses"
    )
    inferred_concerns: List[str] = Field(
        default_factory=list,
        description="Inferred concerns"
    )
    inferred_constraints: List[str] = Field(
        default_factory=list,
        description="Inferred constraints"
    )

    # Confidence
    profile_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this profile"
    )

    questions_answered: int = Field(default=0, description="Number of questions answered")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Profile creation timestamp"
    )


class OnboardingSessionV1(BaseModel):
    """Onboarding session for a user."""

    session_id: str = Field(
        default_factory=lambda: f"onboard-{uuid4()}",
        description="Session ID"
    )
    user_id: str = Field(..., description="User ID")
    decision_context: str = Field(
        ...,
        max_length=1000,
        description="Decision context"
    )

    # Available archetypes
    available_archetypes: List[DecisionArchetypeV1] = Field(
        default_factory=list,
        description="Available decision archetypes"
    )

    # Session state
    status: Literal["active", "completed", "abandoned"] = Field(
        default="active",
        description="Session status"
    )
    questions_presented: List[OnboardingQuestionV1] = Field(
        default_factory=list,
        description="Questions presented"
    )
    responses: List[OnboardingResponseV1] = Field(
        default_factory=list,
        description="User responses"
    )

    # Current profile
    profile: Optional[OnboardingProfileV1] = Field(
        None,
        description="Current onboarding profile"
    )

    # Convergence criteria
    target_confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Target confidence to stop"
    )
    max_questions: int = Field(
        default=7,
        ge=1,
        le=15,
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


class StartOnboardingRequestV1(BaseModel):
    """Request to start onboarding session."""

    user_id: str = Field(..., description="User ID")
    decision_context: str = Field(
        ...,
        max_length=1000,
        description="Decision context"
    )
    user_role: Optional[str] = Field(
        None,
        description="User's role (helps with initial archetype matching)"
    )
    target_confidence: Optional[float] = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Target confidence"
    )
    max_questions: Optional[int] = Field(
        default=7,
        ge=1,
        le=15,
        description="Max questions"
    )


class StartOnboardingResponseV1(BaseModel):
    """Response with first onboarding question."""

    session_id: str = Field(..., description="Session ID")
    first_question: OnboardingQuestionV1 = Field(..., description="First question")
    progress: str = Field(..., description="Progress message")


class SubmitOnboardingResponseRequestV1(BaseModel):
    """Request to submit onboarding response."""

    question_id: str = Field(..., description="Question ID")
    user_id: str = Field(..., description="User ID")
    selected_option: str = Field(..., description="Selected option")
    response_time_ms: Optional[int] = Field(None, description="Response time")


class SubmitOnboardingResponseResponseV1(BaseModel):
    """Response after submitting onboarding response."""

    accepted: bool = Field(..., description="Whether response was accepted")
    next_question: Optional[OnboardingQuestionV1] = Field(
        None,
        description="Next question (None if complete)"
    )
    session_complete: bool = Field(..., description="Whether session is complete")
    profile: Optional[OnboardingProfileV1] = Field(
        None,
        description="Final profile (if complete)"
    )
    progress: str = Field(..., description="Progress message")


class CompleteOnboardingRequestV1(BaseModel):
    """Request to manually complete onboarding."""

    user_id: str = Field(..., description="User ID")
    skip_remaining: bool = Field(
        default=False,
        description="Skip remaining questions and use current profile"
    )


class GetOnboardingProfileResponseV1(BaseModel):
    """Response with onboarding profile."""

    profile: OnboardingProfileV1 = Field(..., description="Onboarding profile")
    session_summary: Dict[str, any] = Field(
        ...,
        description="Session summary"
    )
