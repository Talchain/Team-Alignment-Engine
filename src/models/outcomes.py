"""Phase 5: Outcome tracking and learning models.

Data models for:
- Decision outcome tracking
- Predicted vs actual measurements
- Learning insights
- Graph refinement suggestions
"""

from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from src.models.consensus import GraphV1, SynthesisOptionV1


# ============================================================================
# CORE OUTCOME MODELS
# ============================================================================


class AssumptionV1(BaseModel):
    """Key assumption in decision-making."""

    assumption_id: str = Field(..., description="Unique identifier for assumption")
    description: str = Field(..., description="Natural language description")
    causal_path: Dict[str, Any] = Field(
        ...,
        description="Causal path: {source, target, mechanism}",
    )
    confidence: float = Field(..., ge=0, le=1, description="Confidence in assumption")
    testable: bool = Field(..., description="Whether assumption can be tested")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Data to test assumption")


class PredictedOutcomeV1(BaseModel):
    """Predicted outcome for a decision metric."""

    metric: str = Field(..., description="Metric name (e.g., 'revenue', 'churn_rate')")
    predicted_value: float = Field(..., description="Predicted numeric value")
    confidence_interval: Dict[str, float] = Field(
        ...,
        description="Lower and upper bounds: {lower: float, upper: float}",
    )
    time_horizon: str = Field(..., description="When to measure (e.g., '30 days', '90 days')")


class ActualOutcomeV1(BaseModel):
    """Measured actual outcome."""

    metric: str = Field(..., description="Metric name (must match prediction)")
    actual_value: float = Field(..., description="Measured actual value")
    measured_at: datetime = Field(default_factory=datetime.utcnow, description="Measurement timestamp")
    variance_from_prediction: float = Field(
        ...,
        description="(actual - predicted) / predicted",
    )


class DecisionOutcomeV1(BaseModel):
    """Complete decision outcome tracking."""

    outcome_id: UUID = Field(default_factory=uuid4, description="Unique outcome identifier")
    session_id: str = Field(..., description="Links to deliberation session")

    decision: Dict[str, Any] = Field(
        ...,
        description="Decision details: {selected_option, decided_at, decision_graph, key_assumptions}",
    )

    predicted_outcomes: List[PredictedOutcomeV1] = Field(
        ...,
        description="List of predicted metrics with confidence intervals",
    )

    actual_outcomes: Optional[List[ActualOutcomeV1]] = Field(
        None,
        description="List of measured actual outcomes (populated after measurement)",
    )

    status: Literal["predicted", "monitoring", "measured", "analyzed"] = Field(
        default="predicted",
        description="Outcome tracking status",
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    measured_at: Optional[datetime] = None


class OutcomeMeasurementV1(BaseModel):
    """Granular measurement record."""

    measurement_id: UUID = Field(default_factory=uuid4)
    outcome_id: UUID = Field(..., description="Links to decision_outcome")
    metric: str = Field(..., description="Metric being measured")
    actual_value: float = Field(..., description="Measured value")
    predicted_value: float = Field(..., description="Originally predicted value")
    variance: float = Field(..., description="Prediction error percentage")
    measured_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(None, description="Context or explanation")


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================


class TrackDecisionOutcomeRequestV1(BaseModel):
    """Request to track a decision outcome."""

    session_id: str = Field(..., description="Deliberation session ID")
    selected_option: SynthesisOptionV1 = Field(..., description="The chosen decision option")
    predicted_outcomes: List[PredictedOutcomeV1] = Field(
        ...,
        min_length=1,
        description="List of metrics to track",
    )
    measurement_schedule: Optional[List[Dict[str, str]]] = Field(
        None,
        description="When to measure each metric: [{metric, measure_at}]",
    )


class TrackDecisionOutcomeResponseV1(BaseModel):
    """Response after tracking decision."""

    outcome_id: UUID = Field(..., description="Created outcome tracking ID")
    status: str = Field(default="predicted", description="Tracking status")
    next_measurement_date: Optional[str] = Field(
        None,
        description="When to check back for measurements",
    )


class RecordActualOutcomeRequestV1(BaseModel):
    """Request to record actual measured outcomes."""

    outcome_id: UUID = Field(..., description="Outcome tracking ID")
    actual_outcomes: List[ActualOutcomeV1] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, description="Additional context")


class RecordActualOutcomeResponseV1(BaseModel):
    """Response after recording actual outcomes."""

    outcome_id: UUID
    measurements_recorded: int = Field(..., description="Number of measurements added")
    status: str = Field(..., description="Updated tracking status")


class AccuracyAnalysisV1(BaseModel):
    """Accuracy analysis for a single metric."""

    metric: str
    prediction_error: float = Field(..., description="Absolute percentage error")
    within_confidence_interval: bool = Field(..., description="Was actual within predicted CI?")
    accuracy_grade: Literal["excellent", "good", "poor"] = Field(
        ...,
        description="excellent: <10% error, good: <20%, poor: >=20%",
    )


class AssumptionValidationV1(BaseModel):
    """Validation status for a key assumption."""

    assumption_id: str
    validated: bool = Field(..., description="Did assumption hold true?")
    evidence: List[str] = Field(..., description="Evidence for/against assumption")


class OutcomeAnalysisResponseV1(BaseModel):
    """Detailed analysis of decision outcome."""

    outcome: DecisionOutcomeV1
    accuracy_analysis: List[AccuracyAnalysisV1] = Field(
        ...,
        description="Accuracy for each predicted metric",
    )
    assumption_validation: List[AssumptionValidationV1] = Field(
        ...,
        description="Which assumptions held up?",
    )


# ============================================================================
# LEARNING & PATTERN DETECTION
# ============================================================================


class ReliablePathV1(BaseModel):
    """A causal path that historically predicts well."""

    path: Dict[str, Any] = Field(..., description="Causal path structure")
    historical_accuracy: float = Field(..., ge=0, le=1, description="Avg prediction accuracy")
    sample_size: int = Field(..., ge=1, description="Number of historical observations")


class UnreliableAssumptionV1(BaseModel):
    """An assumption frequently violated in practice."""

    assumption: str = Field(..., description="Assumption description")
    violation_rate: float = Field(..., ge=0, le=1, description="How often violated")
    typical_variance: float = Field(..., description="Typical prediction error when violated")


class MissingConfounderV1(BaseModel):
    """A confounder discovered through outcome analysis."""

    confounder: str = Field(..., description="Variable name")
    discovered_in: List[str] = Field(..., description="List of outcome_ids where discovered")
    impact_on_accuracy: float = Field(
        ...,
        description="How much accuracy improved when confounder considered",
    )


class LearningInsightV1(BaseModel):
    """Learning insights for a decision archetype."""

    archetype: str = Field(..., description="Decision archetype")
    reliable_paths: List[ReliablePathV1] = Field(default_factory=list)
    unreliable_assumptions: List[UnreliableAssumptionV1] = Field(default_factory=list)
    missing_confounders: List[MissingConfounderV1] = Field(default_factory=list)


class LearningInsightsV1(BaseModel):
    """Aggregated learning insights across archetypes."""

    insights: List[LearningInsightV1] = Field(..., description="Per-archetype insights")


# ============================================================================
# GRAPH REFINEMENT SUGGESTIONS
# ============================================================================


class RefinementEvidenceV1(BaseModel):
    """Evidence supporting a refinement suggestion."""

    source: Literal["historical_learning", "similar_decision", "causal_theory"]
    details: str = Field(..., description="Explanation of evidence")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in evidence")


class GraphDeltaV1(BaseModel):
    """Changes to apply to a graph."""

    nodes_added: Optional[List[Dict[str, Any]]] = Field(None, description="Nodes to add")
    edges_added: Optional[List[Dict[str, str]]] = Field(None, description="Edges to add")
    edges_removed: Optional[List[str]] = Field(None, description="Edge IDs to remove")


class ProposedChangeV1(BaseModel):
    """Proposed change to graph."""

    action: str = Field(..., description="Human-readable description (e.g., 'Add node Market Conditions')")
    graph_delta: GraphDeltaV1 = Field(..., description="Structural changes")


class ExpectedImpactV1(BaseModel):
    """Expected impact of applying suggestion."""

    prediction_accuracy_improvement: float = Field(
        ...,
        description="Estimated accuracy improvement (percentage points)",
    )
    causal_validity_improvement: float = Field(
        ...,
        description="Estimated causal validity improvement",
    )


class RefinementSuggestionV1(BaseModel):
    """A single graph refinement suggestion."""

    suggestion_id: str = Field(default_factory=lambda: str(uuid4()))
    suggestion_type: Literal[
        "add_node", "add_edge", "remove_edge", "add_confounder", "add_mediator"
    ]

    rationale: str = Field(..., description="Why this suggestion is made")
    evidence: RefinementEvidenceV1 = Field(..., description="Supporting evidence")

    proposed_change: ProposedChangeV1 = Field(..., description="What to change")
    expected_impact: ExpectedImpactV1 = Field(..., description="Expected improvement")

    auto_apply: bool = Field(
        default=False,
        description="Can be auto-applied without user review",
    )
    requires_user_approval: bool = Field(
        default=True,
        description="Requires explicit user approval",
    )


class RefinementSuggestionsV1(BaseModel):
    """Collection of refinement suggestions for a graph."""

    session_id: str
    current_graph: GraphV1

    suggestions: List[RefinementSuggestionV1] = Field(default_factory=list)

    summary: Dict[str, int] = Field(
        ...,
        description="{high_confidence: int, medium_confidence: int, auto_applicable: int}",
    )


# ============================================================================
# AGENT API MODELS
# ============================================================================


class AnalyzeGraphRequestV1(BaseModel):
    """Request to analyze graph for improvements."""

    session_id: str
    graph: GraphV1
    include_learning: bool = Field(
        default=True,
        description="Include historical learning in analysis",
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0,
        le=1,
        description="Only show suggestions above this confidence",
    )


class AnalyzeGraphResponseV1(BaseModel):
    """Response with graph analysis and suggestions."""

    refinement_suggestions: RefinementSuggestionsV1
    learning_insights: LearningInsightsV1
    similar_decisions: List[DecisionOutcomeV1] = Field(
        default_factory=list,
        description="Similar historical decisions for reference",
    )


class ApplySuggestionsRequestV1(BaseModel):
    """Request to apply refinement suggestions."""

    session_id: str
    suggestion_ids: List[str] = Field(..., min_length=1, description="Which suggestions to apply")
    user_approved: bool = Field(..., description="User explicitly approved changes")


class ApplySuggestionsResponseV1(BaseModel):
    """Response after applying suggestions."""

    refined_graph: GraphV1 = Field(..., description="Graph with suggestions applied")
    applied_suggestions: List[RefinementSuggestionV1] = Field(
        ...,
        description="Suggestions that were successfully applied",
    )
    validation_result: Dict[str, Any] = Field(
        ...,
        description="ISL validation result for refined graph",
    )


class GetLearningInsightsRequestV1(BaseModel):
    """Request for learning insights."""

    archetype: Optional[str] = Field(None, description="Filter by archetype")
    min_sample_size: int = Field(
        default=3,
        ge=1,
        description="Minimum historical observations required",
    )


class GetLearningInsightsResponseV1(BaseModel):
    """Response with learning insights."""

    insights: LearningInsightsV1
    total_outcomes_analyzed: int = Field(..., description="Total outcomes in learning database")
