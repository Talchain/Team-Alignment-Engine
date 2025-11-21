"""Portfolio analytics models for Phase D."""

from datetime import datetime
from typing import Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    """Date range for queries."""

    start: datetime
    end: datetime


class PortfolioFilters(BaseModel):
    """Filters for portfolio queries."""

    organization_id: UUID
    date_range: DateRange
    teams: Optional[List[UUID]] = None
    decision_types: Optional[List[str]] = None
    min_risk_score: Optional[float] = Field(None, ge=0, le=1)
    status: Optional[List[str]] = None


class PortfolioMetrics(BaseModel):
    """Aggregated metrics across portfolio."""

    avg_decision_time_days: float = Field(..., description="Average time to decision")
    avg_quality_rating: float = Field(..., description="Average retrospective rating")
    avg_satisfaction_score: float = Field(..., description="Average stakeholder satisfaction")
    total_options_proposed: int
    total_ai_options_used: int
    causal_validation_success_rate: float
    minority_concern_validation_rate: float


class DecisionCluster(BaseModel):
    """Group of related decisions."""

    cluster_id: str
    theme: str = Field(..., description="Common topic/theme")
    session_ids: List[UUID]
    avg_complexity: float
    common_stakeholders: List[str]


class DecisionBottleneck(BaseModel):
    """Detected bottleneck in decision flow."""

    bottleneck_type: Literal["stuck_session", "overloaded_stakeholder", "validation_blocked"]
    session_id: UUID
    description: str
    severity: Literal["low", "medium", "high"]
    recommendation: str


class PortfolioAnalysis(BaseModel):
    """Complete portfolio analytics result."""

    organization_id: UUID
    period: DateRange
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    metrics: PortfolioMetrics
    clusters: List[DecisionCluster]
    bottlenecks: List[DecisionBottleneck]
    health_score: float = Field(..., ge=0, le=1, description="Overall portfolio health")
    strategic_insights: List[str] = Field(..., description="CEE-generated insights")
    generated_at: datetime


class PortfolioAnalysisResponse(BaseModel):
    """API response for portfolio analytics."""

    success: bool = True
    data: PortfolioAnalysis
    request_id: str


# Dependency models


class DependencyType(str):
    """Types of dependencies between decisions."""

    BLOCKS = "blocks"
    DEPENDS_ON = "depends_on"
    RELATES_TO = "relates_to"
    SUPERSEDES = "supersedes"


class DecisionDependency(BaseModel):
    """Dependency between two decisions."""

    dependency_id: UUID
    source_session_id: UUID = Field(..., description="Session that affects target")
    target_session_id: UUID = Field(..., description="Session that is affected")
    dependency_type: str
    description: Optional[str] = Field(None, description="Why this dependency exists")
    created_by: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


class DecisionNode(BaseModel):
    """Node in dependency graph."""

    session_id: UUID
    title: str
    status: str
    progress: float = Field(..., ge=0, le=1)
    blocked_by: List[UUID] = Field(default_factory=list)
    blocking: List[UUID] = Field(default_factory=list)


class GraphMetrics(BaseModel):
    """Metrics about dependency graph."""

    total_nodes: int
    total_edges: int
    max_depth: int = Field(..., description="Longest dependency chain")
    avg_fanout: float = Field(..., description="Average dependencies per session")
    blocked_count: int = Field(..., description="Sessions currently blocked")


class DependencyGraph(BaseModel):
    """Dependency graph for organization."""

    organization_id: UUID
    nodes: List[DecisionNode]
    edges: List[DecisionDependency]
    critical_path: List[UUID] = Field(..., description="Longest path through graph")
    bottlenecks: List[UUID] = Field(..., description="Sessions blocking multiple others")
    graph_metrics: GraphMetrics


# Pattern models


class DecisionPattern(BaseModel):
    """Pattern identified in decision-making."""

    pattern_id: str
    pattern_type: Literal["success", "failure", "neutral"]
    decision_type: str
    sample_size: int
    description: str = Field(..., description="Human-readable pattern description")
    common_characteristics: List[str]
    avg_metrics: Dict[str, float]
    confidence: float = Field(..., ge=0, le=1)
    recommendations: List[str] = Field(default_factory=list)


class OrganizationalPatterns(BaseModel):
    """All patterns identified for organization."""

    organization_id: UUID
    analysis_period: DateRange
    sample_size: int
    patterns: List[DecisionPattern]
    best_practices: List[str] = Field(..., description="CEE-generated best practices")
    generated_at: datetime


# Analytics models


class DataPoint(BaseModel):
    """Single data point in time series."""

    timestamp: datetime
    value: float
    sample_size: int


class TrendLine(BaseModel):
    """Linear trend fit."""

    slope: float = Field(..., description="Trend direction (positive = improving)")
    intercept: float
    r_squared: float = Field(..., description="Fit quality (0-1)")
    direction: Literal["improving", "stable", "declining"]


class Changepoint(BaseModel):
    """Significant shift in metric."""

    timestamp: datetime
    magnitude: float
    confidence: float = Field(..., ge=0, le=1)
    likely_cause: Optional[str] = None


class ForecastPoint(BaseModel):
    """Forecasted data point."""

    timestamp: datetime
    predicted_value: float
    confidence_interval_lower: float
    confidence_interval_upper: float


class TrendAnalysis(BaseModel):
    """Trend analysis for a metric."""

    metric: str
    period: DateRange
    granularity: Literal["weekly", "monthly"]
    time_series: List[DataPoint]
    moving_avg_3: List[float]
    moving_avg_6: List[float]
    trend: TrendLine
    changepoints: List[Changepoint]
    forecast: List[ForecastPoint]


class GroupMetrics(BaseModel):
    """Metrics for a comparison group."""

    group_id: str
    sample_size: int
    avg_decision_time_days: float
    avg_quality_rating: float
    causal_validation_rate: float
    ai_usage_rate: float


class PercentileRanking(BaseModel):
    """Percentile ranking for a group."""

    metric: str
    percentile: int = Field(..., ge=0, le=100)
    rank: int
    total_groups: int


class OutlierGroup(BaseModel):
    """Group identified as outlier."""

    group_id: str
    metric: str
    value: float
    deviation_from_mean: float
    direction: Literal["above", "below"]


class ComparativeBenchmark(BaseModel):
    """Comparative benchmark across groups."""

    organization_id: UUID
    compare_by: Literal["team", "decision_type", "time_period"]
    group_metrics: Dict[str, GroupMetrics]
    rankings: Dict[str, PercentileRanking]
    outliers: List[OutlierGroup]


# Coordination models


class CoordinationStatus(str):
    """Status of coordination group."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CoordinationGroup(BaseModel):
    """Group of coordinated decisions."""

    group_id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    session_ids: List[UUID]
    coordinator_id: str
    created_at: datetime
    status: str


class ConflictDetection(BaseModel):
    """Detected conflict across coordinated decisions."""

    conflict_type: Literal["timeline", "resource", "assumption", "goal"]
    session_ids: List[UUID]
    description: str
    severity: Literal["low", "medium", "high"]
    resolution_suggestions: List[str] = Field(default_factory=list)


class CoordinationView(BaseModel):
    """Unified view of coordinated decisions."""

    group: CoordinationGroup
    sessions: List[Dict]  # Simplified session data
    shared_themes: List[str]
    conflicts: List[ConflictDetection]
    recommendations: List[str]
    coordination_health: float = Field(..., ge=0, le=1)


# Collaboration models


class UserPresence(BaseModel):
    """User presence in session."""

    user_id: str
    display_name: str
    status: Literal["active", "idle", "away"]
    connected_at: datetime
    last_activity: datetime
    current_view: Optional[str] = None


class CollaborationAction(BaseModel):
    """Action in collaborative session."""

    action_type: Literal[
        "option_proposed",
        "option_edited",
        "vote_cast",
        "concern_raised",
        "typing_start",
        "typing_stop",
        "cursor_move"
    ]
    target_id: Optional[UUID] = None
    data: Dict[str, str] = Field(default_factory=dict)
    persist: bool = True


class SessionState(BaseModel):
    """Current state of collaborative session."""

    session_id: UUID
    status: str
    online_users: List[UserPresence]
    recent_actions: List[CollaborationAction]
    unread_count: int
