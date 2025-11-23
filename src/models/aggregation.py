"""Aggregation intelligence models (Phase 3: Navajas Aggregation).

Models for confidence calibration, strategic behavior detection, and optimal team composition.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime


# ============================================================================
# CONFIDENCE CALIBRATION MODELS
# ============================================================================


class ConfidenceCalibrationFactorsV1(BaseModel):
    """Factors affecting confidence calibration."""

    historical_accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Past prediction accuracy (Brier score)"
    )
    domain_expertise: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Role relevance to decision domain"
    )
    overconfidence_bias: float = Field(
        ...,
        ge=0.0,
        description="Tendency to overstate certainty (0=none, >0=overconfident)"
    )


class ConfidenceAnalysisV1(BaseModel):
    """Confidence calibration analysis for a user."""

    user_id: str = Field(..., description="User ID")
    stated_confidence: float = Field(..., ge=0.0, le=1.0, description="User's stated confidence")
    calibrated_confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence")

    calibration_factors: ConfidenceCalibrationFactorsV1 = Field(
        ...,
        description="Calibration factors"
    )

    recommendation: Literal["increase_weight", "decrease_weight", "unchanged"] = Field(
        ...,
        description="Weight adjustment recommendation"
    )


# ============================================================================
# STRATEGIC BEHAVIOR DETECTION MODELS
# ============================================================================


class DetectedPatternV1(BaseModel):
    """A detected strategic behavior pattern."""

    pattern_type: Literal["anchoring", "conformity", "withholding", "strategic_voting"] = Field(
        ...,
        description="Type of strategic pattern"
    )
    affected_users: List[str] = Field(..., description="Users exhibiting this pattern")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    evidence: List[str] = Field(..., description="Evidence for this pattern")


class MitigationActionV1(BaseModel):
    """Mitigation action applied to a strategic pattern."""

    pattern_type: str = Field(..., description="Pattern type mitigated")
    action: str = Field(..., description="Mitigation action taken")
    effectiveness: float = Field(..., ge=0.0, le=1.0, description="Estimated effectiveness")


class StrategyDetectionV1(BaseModel):
    """Strategic behavior detection results."""

    session_id: str = Field(..., description="Session ID")
    detected_patterns: List[DetectedPatternV1] = Field(
        default_factory=list,
        description="Detected patterns"
    )
    mitigation_applied: List[MitigationActionV1] = Field(
        default_factory=list,
        description="Mitigations applied"
    )


# ============================================================================
# TEAM SIZE ANALYSIS MODELS
# ============================================================================


class TeamSizeAnalysisDetailsV1(BaseModel):
    """Detailed analysis of team composition."""

    diversity_score: float = Field(..., ge=0.0, le=1.0, description="Perspective diversity")
    coordination_cost: float = Field(..., ge=0.0, description="Time to reach consensus")
    collective_accuracy: float = Field(..., ge=0.0, le=1.0, description="Expected quality")


class TeamSizeAnalysisV1(BaseModel):
    """Team size optimization analysis."""

    decision_type: str = Field(..., description="Decision type")
    current_team_size: int = Field(..., ge=1, description="Current team size")
    optimal_range: Dict[str, int] = Field(..., description="Optimal size range (min/max)")

    analysis: TeamSizeAnalysisDetailsV1 = Field(..., description="Analysis details")

    recommendation: Literal["add_members", "reduce_size", "optimal", "run_smaller_groups"] = Field(
        ...,
        description="Size recommendation"
    )
    reasoning: str = Field(..., max_length=500, description="Reasoning for recommendation")


# ============================================================================
# COMMUNICATION PATTERN ANALYSIS MODELS
# ============================================================================


class CommunicationPatternV1(BaseModel):
    """Communication pattern analysis."""

    interaction_type: Literal["public_debate", "private_submission", "anonymous_voting"] = Field(
        ...,
        description="Type of interaction"
    )
    accuracy_impact: float = Field(..., ge=-1.0, le=1.0, description="Impact on accuracy")
    confidence_impact: float = Field(..., ge=-1.0, le=1.0, description="Impact on confidence")
    convergence_impact: float = Field(..., ge=-1.0, le=1.0, description="Impact on convergence speed")


class CommunicationAnalysisV1(BaseModel):
    """Communication pattern analysis results."""

    session_id: str = Field(..., description="Session ID")
    patterns: List[CommunicationPatternV1] = Field(..., description="Observed patterns")

    recommendation: Dict[str, str] = Field(
        ...,
        description="Optimal communication structure and reasoning"
    )


# ============================================================================
# AGGREGATION WEIGHTING MODELS
# ============================================================================


class WeightBreakdownV1(BaseModel):
    """Breakdown of weight components."""

    causal_quality: float = Field(..., ge=0.0, le=1.0, description="Causal quality weight")
    value_alignment: float = Field(..., ge=0.0, le=1.0, description="Value alignment weight")
    calibrated_confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence")
    strategy_penalty: float = Field(..., ge=0.0, le=1.0, description="Strategic behavior penalty")


class RecommendedWeightV1(BaseModel):
    """Recommended weight for a user's input."""

    user_id: str = Field(..., description="User ID")
    final_weight: float = Field(..., ge=0.0, le=1.0, description="Final aggregation weight")
    weight_breakdown: WeightBreakdownV1 = Field(..., description="Weight breakdown")


# ============================================================================
# AGGREGATION ANALYSIS API MODELS
# ============================================================================


class AggregationAnalysisRequestV1(BaseModel):
    """Request for aggregation analysis."""

    session_id: str = Field(..., description="Session ID")
    decision_type: Optional[str] = Field(None, description="Decision type")


class AggregationAnalysisResponseV1(BaseModel):
    """Aggregation analysis response."""

    confidence_calibration: List[ConfidenceAnalysisV1] = Field(
        default_factory=list,
        description="Confidence calibration results"
    )
    strategic_behaviour: StrategyDetectionV1 = Field(
        ...,
        description="Strategic behavior detection"
    )
    team_size_analysis: TeamSizeAnalysisV1 = Field(
        ...,
        description="Team size analysis"
    )
    communication_patterns: CommunicationAnalysisV1 = Field(
        ...,
        description="Communication pattern analysis"
    )

    recommended_weights: List[RecommendedWeightV1] = Field(
        default_factory=list,
        description="Recommended weights for each user"
    )


class AggregationQualityV1(BaseModel):
    """Quality metrics for aggregated result."""

    collective_intelligence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Collective intelligence score"
    )
    diversity_bonus: float = Field(..., ge=0.0, description="Diversity contribution")
    coordination_cost: float = Field(..., ge=0.0, description="Coordination overhead")


class SmartSynthesisRequestV1(BaseModel):
    """Request for smart synthesis with aggregation."""

    session_id: str = Field(..., description="Session ID")
    synthesis_mode: Literal["wisdom_of_crowds", "expert_weighted", "hybrid"] = Field(
        default="hybrid",
        description="Synthesis mode"
    )


class SmartSynthesisResponseV1(BaseModel):
    """Smart synthesis response."""

    synthesis_options: List[Dict] = Field(..., description="Synthesis options")
    aggregation_quality: AggregationQualityV1 = Field(..., description="Aggregation quality")
    warnings: List[str] = Field(default_factory=list, description="Warnings about biases")
