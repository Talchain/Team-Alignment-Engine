"""Analysis-related models."""

from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime
from uuid import UUID, uuid4


class SharedGround(BaseModel):
    """Shared ground analysis model."""

    shared_ground_id: UUID = Field(default_factory=uuid4)
    session_id: UUID

    common_goals: List[Dict]  # [{goal, agreement_score, stakeholder_weights}]
    common_concerns: List[str]
    summary: str  # Plain English

    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DisagreementMap(BaseModel):
    """Disagreement map analysis model."""

    disagreement_map_id: UUID = Field(default_factory=uuid4)
    session_id: UUID

    primary_tensions: List[Dict]  # [{dimension_pair, tension_score, positions}]
    secondary_differences: List[Dict]
    summary: str  # Plain English

    generated_at: datetime = Field(default_factory=datetime.utcnow)
