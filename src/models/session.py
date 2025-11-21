"""Session-related models."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from uuid import UUID, uuid4

from src.models.enums import SessionStatus, AlignmentMode, DecisionType


class AlignmentSession(BaseModel):
    """Alignment session model."""

    session_id: UUID = Field(default_factory=uuid4)
    team_id: UUID
    decision_topic: str = Field(..., max_length=500)
    decision_context: str = Field(..., max_length=2000)
    decision_type: DecisionType = DecisionType.CUSTOM
    alignment_mode: AlignmentMode = AlignmentMode.EVIDENCE_BACKED
    status: SessionStatus = SessionStatus.COLLECTING

    # Participants with roles
    stakeholders: List[Dict[str, str]]  # {user_id, role, name, email}

    # Analysis results
    shared_ground: Optional[Dict] = None
    disagreement_map: Optional[Dict] = None

    # Scenario link (CRITICAL for ISL integration)
    scenario_model_id: Optional[UUID] = None
    scenario_parameter_deltas: Optional[Dict] = None

    # Decision
    selected_option_id: Optional[UUID] = None

    # Phase C: Multi-round deliberation support
    parent_session_id: Optional[UUID] = None
    reopened_from_id: Optional[UUID] = None
    chain_depth: int = 0

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    created_by: UUID

    class Config:
        json_schema_extra = {
            "example": {
                "team_id": "550e8400-e29b-41d4-a716-446655440000",
                "decision_topic": "Q2 Pricing Strategy",
                "decision_context": "Need to balance revenue growth with retention",
                "decision_type": "pricing",
                "alignment_mode": "evidence_backed",
                "stakeholders": [
                    {"user_id": "uuid1", "role": "owner", "name": "Alice"},
                    {"user_id": "uuid2", "role": "stakeholder", "name": "Bob"},
                ],
            }
        }


class DecisionTemplate(BaseModel):
    """Pre-configured template per decision type."""

    decision_type: DecisionType
    goal_dimensions: List[str]  # Which goals are relevant
    default_outcome_metrics: List[str]  # What ISL should predict
    stakeholder_questions: Dict[str, List[str]]  # Questions per role

    @classmethod
    def get_template(cls, decision_type: DecisionType) -> "DecisionTemplate":
        """Get template for specific decision type."""
        templates = {
            DecisionType.PRICING: cls(
                decision_type=DecisionType.PRICING,
                goal_dimensions=[
                    "revenue_growth",
                    "customer_retention",
                    "brand_perception",
                ],
                default_outcome_metrics=["revenue_growth", "churn_rate", "margin"],
                stakeholder_questions={
                    "PM": [
                        "What revenue target are you aiming for?",
                        "What's your risk tolerance on churn?",
                    ],
                    "Designer": [
                        "How should pricing affect brand perception?",
                        "What customer experience concerns do you have?",
                    ],
                },
            ),
            DecisionType.FEATURE_PRIORITIZATION: cls(
                decision_type=DecisionType.FEATURE_PRIORITIZATION,
                goal_dimensions=[
                    "customer_satisfaction",
                    "competitive_position",
                    "technical_sustainability",
                ],
                default_outcome_metrics=[
                    "adoption_rate",
                    "satisfaction_score",
                    "development_time",
                ],
                stakeholder_questions={
                    "PM": ["Which features drive growth?"],
                    "Engineer": ["What's technically feasible in timeline?"],
                },
            ),
            DecisionType.GTM_STRATEGY: cls(
                decision_type=DecisionType.GTM_STRATEGY,
                goal_dimensions=[
                    "customer_acquisition",
                    "brand_awareness",
                    "time_to_market",
                ],
                default_outcome_metrics=["reach", "conversion", "cost", "timeline"],
                stakeholder_questions={
                    "Marketing": ["What channels are most effective?"],
                    "Sales": ["What messaging resonates with customers?"],
                },
            ),
            DecisionType.RESOURCE_ALLOCATION: cls(
                decision_type=DecisionType.RESOURCE_ALLOCATION,
                goal_dimensions=["team_capacity", "technical_sustainability", "time_to_market"],
                default_outcome_metrics=["velocity", "quality", "burnout_risk"],
                stakeholder_questions={
                    "PM": ["What are the highest priorities?"],
                    "Engineering Manager": ["What's sustainable for the team?"],
                },
            ),
        }
        return templates.get(
            decision_type,
            cls(
                decision_type=DecisionType.CUSTOM,
                goal_dimensions=[
                    "revenue_growth",
                    "customer_retention",
                    "product_quality",
                    "team_capacity",
                ],
                default_outcome_metrics=["outcome_metric_1", "outcome_metric_2"],
                stakeholder_questions={
                    "Stakeholder": ["What outcomes matter most to you?"]
                },
            ),
        )
