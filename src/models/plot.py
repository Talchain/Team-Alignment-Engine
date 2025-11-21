"""Pydantic models for PLoT integration.

TAE POC v02 Integration: Internal-only orchestration endpoint.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from uuid import UUID


# ============================================================================
# REQUEST MODELS
# ============================================================================


class PlotAlignmentRequest(BaseModel):
    """Request model for PLoT alignment session endpoint.

    PLoT sends this to TAE's /api/v1/plot/alignment-session endpoint.
    """

    session_id: Optional[str] = Field(
        None,
        description="Session ID for session-specific data. Null for portfolio queries.",
    )
    organization_id: str = Field(
        ...,
        description="Organization ID for organizational context (D1/D4/D5/D6)",
    )
    capabilities: List[str] = Field(
        default=["core_alignment"],
        description="Requested capabilities: core_alignment, d1_portfolio, d3_dependencies, d4_patterns",
        examples=[["core_alignment", "d3_dependencies", "d4_patterns"]],
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional request context (filters, params, etc.)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-abc123",
                "organization_id": "org-456",
                "capabilities": ["core_alignment", "d3_dependencies", "d4_patterns"],
                "context": {
                    "request_id": "plot-run-xyz789",
                    "user_role": "PM",
                },
            }
        }


# ============================================================================
# RESPONSE MODELS - Nested Structures
# ============================================================================


class SharedGroundData(BaseModel):
    """Shared ground between stakeholders."""

    summary: str = Field(..., description="Plain-English summary from CEE")
    common_goal_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="8-dimension goal weights common across stakeholders",
    )
    aligned_priorities: List[str] = Field(
        default_factory=list,
        description="List of priorities where stakeholders agree",
    )


class DisagreementAxis(BaseModel):
    """Single axis of disagreement between stakeholders."""

    dimension: str = Field(..., description="Goal dimension where disagreement occurs")
    stakeholders_involved: List[str] = Field(
        ..., description="Stakeholders involved in this disagreement"
    )
    severity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Severity of disagreement (0-1)"
    )
    description: str = Field(..., description="Plain-English description")


class DisagreementData(BaseModel):
    """Disagreements between stakeholders."""

    summary: str = Field(..., description="Plain-English summary from CEE")
    axes: List[DisagreementAxis] = Field(
        default_factory=list, description="List of disagreement axes"
    )


class AlignmentData(BaseModel):
    """Core alignment data for a deliberation session."""

    session_state: Literal[
        "collecting_perspectives",
        "proposing_options",
        "deliberating",
        "decided",
        "unknown",
    ] = Field(..., description="Current session state")
    stakeholder_count: int = Field(..., ge=0, description="Number of stakeholders")
    perspectives_collected: int = Field(
        ..., ge=0, description="Number of perspectives collected"
    )
    options_proposed: int = Field(..., ge=0, description="Number of options proposed")
    consensus_level: float = Field(
        ..., ge=0.0, le=1.0, description="Consensus level (0-1 scale)"
    )
    shared_ground: SharedGroundData
    disagreements: DisagreementData


class MinorityConcern(BaseModel):
    """Minority concern from Phase C."""

    concern_id: str
    stakeholder: str
    evidence_based: bool = Field(
        ..., description="Whether concern is evidence-based (ISL validated)"
    )
    addressed: bool = Field(..., description="Whether concern has been addressed")
    description: str


class DecisionQualityMetrics(BaseModel):
    """Decision quality metrics (D1 + Phase B/C)."""

    health_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall decision health score"
    )
    risk_flags: List[str] = Field(
        default_factory=list, description="List of risk flags identified"
    )
    causally_validated: bool = Field(
        ..., description="Whether options are causally validated via ISL"
    )
    assumption_strength: float = Field(
        ..., ge=0.0, le=1.0, description="Strength of assumptions (0-1 scale)"
    )
    minority_concerns: List[MinorityConcern] = Field(
        default_factory=list, description="Minority concerns raised"
    )


class SimilarDecision(BaseModel):
    """Similar past decision from D4: Organizational Patterns."""

    session_id: str
    outcome: Literal["success", "failure", "neutral"]
    similarity: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score to current decision"
    )
    key_lessons: List[str] = Field(
        default_factory=list, description="Key lessons learned"
    )
    timestamp: datetime


class DecisionDependency(BaseModel):
    """Decision dependency from D3."""

    dependent_session_id: str = Field(
        ..., description="Session ID that this session depends on or blocks"
    )
    dependency_type: Literal["blocks", "informs", "conflicts"] = Field(
        ..., description="Type of dependency relationship"
    )
    team: str = Field(..., description="Team owning the dependent session")
    description: Optional[str] = Field(None, description="Dependency description")
    status: Literal["pending", "resolved", "blocked"] = Field(
        default="pending", description="Dependency status"
    )


class TrendInsights(BaseModel):
    """Trend insights from D5: Advanced Analytics."""

    organization_decision_velocity: str = Field(
        ..., description="Decision velocity compared to baseline (e.g., '15% slower')"
    )
    quality_trend: Literal["improving", "declining", "stable"]
    forecast: Optional[Dict[str, Any]] = Field(
        None, description="Optional forecasting data"
    )


class CrossTeamConflict(BaseModel):
    """Cross-team conflict from D6."""

    conflicting_session_id: str
    conflict_type: Literal["temporal", "resource", "scope"]
    severity: Literal["low", "medium", "high"]
    resolution_suggestion: Optional[str] = None


class OrganizationalContext(BaseModel):
    """Organizational context aggregating D1/D3/D4/D5/D6."""

    # D4: Patterns
    similar_decisions: List[SimilarDecision] = Field(
        default_factory=list, description="Similar past decisions (D4)"
    )

    # D3: Dependencies
    dependencies: List[DecisionDependency] = Field(
        default_factory=list, description="Decision dependencies (D3)"
    )

    # D5: Advanced Analytics (DEFERRED for POC v02)
    trend_insights: Optional[TrendInsights] = Field(
        None, description="Trend analysis (D5) - deferred for POC v02"
    )

    # D6: Cross-Team Coordination (DEFERRED for POC v02)
    conflicts: List[CrossTeamConflict] = Field(
        default_factory=list, description="Cross-team conflicts (D6) - deferred"
    )


class RecentAction(BaseModel):
    """Recent collaboration action from D2."""

    user_id: str
    action_type: Literal[
        "vote_cast", "concern_raised", "option_proposed", "perspective_added"
    ]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class CollaborationData(BaseModel):
    """Real-time collaboration data (D2) - DEFERRED for POC v02."""

    active_stakeholders: List[str] = Field(
        default_factory=list, description="Currently active stakeholders"
    )
    recent_actions: List[RecentAction] = Field(
        default_factory=list, description="Recent actions in session"
    )


class CapabilityAvailability(BaseModel):
    """Availability status for each Phase D capability."""

    d1_portfolio_analytics: bool = True
    d2_realtime_collaboration: bool = False  # Deferred for POC v02
    d3_decision_dependencies: bool = True
    d4_organizational_patterns: bool = True
    d5_advanced_analytics: bool = False  # Deferred for POC v02
    d6_cross_team_coordination: bool = False  # Deferred for POC v02


class AvailabilityStatus(BaseModel):
    """Overall TAE availability status."""

    tae_available: bool = Field(
        ..., description="Whether TAE service is available"
    )
    capabilities: CapabilityAvailability = Field(
        default_factory=CapabilityAvailability,
        description="Per-capability availability",
    )
    degraded: bool = Field(
        ..., description="Whether TAE is running in degraded mode"
    )
    degradation_reason: Optional[str] = Field(
        None, description="Reason for degradation if degraded=true"
    )


# ============================================================================
# MAIN RESPONSE MODEL
# ============================================================================


class TaeTeamAlignmentPayload(BaseModel):
    """Main response payload for PLoT alignment session endpoint.

    This is returned to PLoT and included in PLoT's /v1/run response.
    """

    # Metadata
    session_id: Optional[str] = Field(
        None, description="Session ID (null for portfolio queries)"
    )
    organization_id: str = Field(..., description="Organization ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    version: str = Field(..., description="TAE service version (e.g., '2.0.0')")
    request_id: Optional[str] = Field(
        None, description="Request ID from PLoT (for tracing)"
    )

    # Core alignment data (always present for session queries)
    alignment: Optional[AlignmentData] = Field(
        None, description="Core alignment data for session"
    )

    # Decision quality metrics
    decision_quality: Optional[DecisionQualityMetrics] = Field(
        None, description="Decision quality metrics"
    )

    # Organizational context (D1/D3/D4/D5/D6)
    organizational_context: OrganizationalContext = Field(
        default_factory=OrganizationalContext,
        description="Organizational context from Phase D",
    )

    # Collaboration (D2 - deferred for POC v02)
    collaboration: Optional[CollaborationData] = Field(
        None, description="Real-time collaboration data (D2) - deferred for POC v02"
    )

    # Availability
    availability: AvailabilityStatus = Field(
        ..., description="TAE availability status"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-abc123",
                "organization_id": "org-456",
                "timestamp": "2025-11-21T10:00:00Z",
                "version": "2.0.0",
                "request_id": "plot-run-xyz789",
                "alignment": {
                    "session_state": "deliberating",
                    "stakeholder_count": 5,
                    "perspectives_collected": 5,
                    "options_proposed": 3,
                    "consensus_level": 0.65,
                    "shared_ground": {
                        "summary": "All stakeholders prioritize user experience and speed",
                        "common_goal_weights": {
                            "user_satisfaction": 0.9,
                            "performance": 0.85,
                        },
                        "aligned_priorities": ["Fast load times", "Mobile support"],
                    },
                    "disagreements": {
                        "summary": "PM and Designer disagree on implementation complexity",
                        "axes": [
                            {
                                "dimension": "feasibility",
                                "stakeholders_involved": ["PM", "Designer"],
                                "severity_score": 0.7,
                                "description": "PM concerned about 6-week timeline",
                            }
                        ],
                    },
                },
                "decision_quality": {
                    "health_score": 0.75,
                    "risk_flags": ["Timeline pressure", "Technical complexity"],
                    "causally_validated": True,
                    "assumption_strength": 0.68,
                    "minority_concerns": [],
                },
                "organizational_context": {
                    "similar_decisions": [
                        {
                            "session_id": "session-old123",
                            "outcome": "success",
                            "similarity": 0.87,
                            "key_lessons": [
                                "Early prototyping saved 2 weeks",
                                "Designer-developer pairing improved alignment",
                            ],
                            "timestamp": "2025-10-15T14:00:00Z",
                        }
                    ],
                    "dependencies": [
                        {
                            "dependent_session_id": "session-api456",
                            "dependency_type": "blocks",
                            "team": "Platform Team",
                            "description": "Waiting for API design decision",
                            "status": "pending",
                        }
                    ],
                    "conflicts": [],
                },
                "collaboration": None,  # Deferred for POC v02
                "availability": {
                    "tae_available": True,
                    "capabilities": {
                        "d1_portfolio_analytics": True,
                        "d2_realtime_collaboration": False,
                        "d3_decision_dependencies": True,
                        "d4_organizational_patterns": True,
                        "d5_advanced_analytics": False,
                        "d6_cross_team_coordination": False,
                    },
                    "degraded": False,
                    "degradation_reason": None,
                },
            }
        }
