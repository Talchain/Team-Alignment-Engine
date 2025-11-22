"""Validated request models with comprehensive input validation."""

from pydantic import BaseModel, Field, EmailStr, validator, constr
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

# String length constraints matching database limits
SHORT_STRING = constr(min_length=1, max_length=100)
MEDIUM_STRING = constr(min_length=1, max_length=500)
LONG_STRING = constr(min_length=1, max_length=2000)
EXTRA_LONG_STRING = constr(min_length=1, max_length=5000)


class CreateOptionRequest(BaseModel):
    """Validated request for creating an option."""

    session_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    expected_outcome: str = Field(..., min_length=1, max_length=1000)
    causal_rationale: str = Field(..., min_length=10, max_length=2000)
    addresses_goals: List[str] = Field(..., min_items=1, max_items=20)
    trade_offs: List[str] = Field(..., max_items=20)
    key_assumptions: List[str] = Field(..., min_items=1, max_items=50)
    proposed_by: str = Field(..., max_length=100)

    @validator("addresses_goals", "trade_offs", "key_assumptions", each_item=True)
    def validate_string_items(cls, v):
        """Validate each string item in lists."""
        if not v or len(v) > 500:
            raise ValueError("List items must be 1-500 characters")
        return v


class CreateConcernRequest(BaseModel):
    """Validated request for raising a concern."""

    option_id: UUID
    concern_text: str = Field(..., min_length=10, max_length=1000)
    concern_type: str = Field(..., regex="^(assumption|outcome|fairness|risk)$")
    assumption_id_tested: Optional[str] = Field(None, max_length=100)

    @validator("concern_text")
    def validate_concern_text(cls, v):
        """Ensure concern text is substantive."""
        if v.strip() == "" or len(v.strip()) < 10:
            raise ValueError("Concern must be at least 10 characters")
        return v.strip()


class UpdateSessionStatusRequest(BaseModel):
    """Validated request for updating session status."""

    status: str = Field(..., regex="^(collecting|analyzing|proposing|validating|deciding|complete)$")


class CreateDecisionRequest(BaseModel):
    """Validated request for making a decision."""

    session_id: UUID
    chosen_option_id: UUID
    decision_rationale: str = Field(..., min_length=20, max_length=2000)
    stakeholder_support: Dict[str, str] = Field(..., min_items=1)
    monitored_risks: List[str] = Field(default_factory=list, max_items=20)
    success_criteria: List[str] = Field(..., min_items=1, max_items=10)

    @validator("decision_rationale")
    def validate_rationale(cls, v):
        """Ensure decision rationale is substantive."""
        if len(v.split()) < 5:
            raise ValueError("Rationale must contain at least 5 words")
        return v


class RateLimitBypass(BaseModel):
    """Internal API key for bypassing rate limits."""

    api_key: str = Field(..., min_length=32, max_length=128)


# Add validation to prevent common injection patterns
def contains_sql_injection_pattern(value: str) -> bool:
    """Check for common SQL injection patterns."""
    dangerous_patterns = [
        "';",
        "--",
        "/*",
        "*/",
        "xp_",
        "sp_",
        "DROP ",
        "DELETE ",
        "TRUNCATE ",
        "UPDATE ",
        "INSERT ",
        "EXEC",
        "EXECUTE",
    ]
    upper_value = value.upper()
    return any(pattern in upper_value for pattern in dangerous_patterns)


def validate_safe_string(cls, v):
    """Validator to prevent SQL injection attempts."""
    if contains_sql_injection_pattern(v):
        raise ValueError("Invalid characters detected")
    return v
