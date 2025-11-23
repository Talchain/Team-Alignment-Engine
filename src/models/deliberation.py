"""Deliberation system data models.

Multi-round deliberation with anonymous voting, convergence detection,
and causal evidence validation.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from uuid import uuid4

from src.models.consensus import (
    TeamInputV1,
    GraphV1,
    SynthesisOptionV1,
    ConflictAnalysisV1,
    ConsensusWarningV1,
    CausalQualityV1,
)


# ============================================================================
# VOTING MODELS
# ============================================================================


class VoteRankingV1(BaseModel):
    """Ranking for a single synthesis option."""

    option_id: str = Field(..., description="ID of synthesis option")
    rank: int = Field(..., ge=1, description="Rank (1 = best)")
    reasoning: Optional[str] = Field(None, max_length=500, description="Optional reasoning for ranking")


class VoteV1(BaseModel):
    """Anonymous vote submission."""

    vote_id: str = Field(default_factory=lambda: f"vote-{uuid4()}", description="Unique vote ID")
    user_id: str = Field(..., description="User ID (encrypted during active voting)")
    round_id: str = Field(..., description="Round this vote belongs to")

    rankings: List[VoteRankingV1] = Field(..., min_length=1, description="Option rankings")

    submitted_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Submission timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vote_id": "vote-abc123",
                "user_id": "encrypted_user_xyz",
                "round_id": "round-001",
                "rankings": [
                    {"option_id": "opt-1", "rank": 1, "reasoning": "Best balances growth and quality"},
                    {"option_id": "opt-2", "rank": 2},
                    {"option_id": "opt-3", "rank": 3},
                ],
                "submitted_at": "2025-01-15T14:30:00Z"
            }
        }


class OptionScoreV1(BaseModel):
    """Aggregated scoring for a synthesis option."""

    option_id: str
    avg_rank: float = Field(..., description="Average rank (lower is better)")
    vote_distribution: List[int] = Field(..., description="Count of votes at each rank [#rank1, #rank2, ...]")
    total_votes: int


class VotingSummaryV1(BaseModel):
    """Aggregated voting results for a round."""

    round_id: str
    total_votes: int

    option_scores: List[OptionScoreV1] = Field(..., description="Scores for each option")

    agreement_level: float = Field(..., ge=0.0, le=1.0, description="Inter-rater agreement (Kendall tau)")

    # Revealed only after round closes
    individual_votes: Optional[List[VoteV1]] = Field(None, description="Individual votes (decrypted post-round)")


# ============================================================================
# CONVERGENCE MODELS
# ============================================================================


class ConvergenceMetricsV1(BaseModel):
    """Detailed convergence metrics."""

    agreement_level: float = Field(..., ge=0.0, le=1.0, description="Vote agreement")
    causal_quality: float = Field(..., ge=0.0, le=1.0, description="Average causal quality score")
    creative_synthesis: float = Field(..., ge=0.0, le=1.0, description="Average creative score")
    minority_protected: bool = Field(..., description="Minority position protection triggered")
    conflicts_resolved: int = Field(..., ge=0, description="Number of conflicts resolved")
    conflicts_remaining: int = Field(..., ge=0, description="Number of conflicts still unresolved")


class ConvergenceStatusV1(BaseModel):
    """Convergence assessment for a deliberation session."""

    converged: bool = Field(..., description="Whether consensus has been reached")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Composite quality metric")

    metrics: ConvergenceMetricsV1

    recommendation: Literal["continue", "converge", "needs_refinement"] = Field(
        ..., description="Recommended next action"
    )
    reason: str = Field(..., description="Human-readable explanation")


# ============================================================================
# ROUND MODELS
# ============================================================================


class DeliberationRoundV1(BaseModel):
    """Single round in a deliberation session."""

    round_id: str = Field(default_factory=lambda: f"round-{uuid4()}", description="Unique round ID")
    session_id: str = Field(..., description="Session this round belongs to")
    round_number: int = Field(..., ge=1, description="Round number (1-indexed)")
    round_type: Literal["submission", "synthesis", "voting", "refinement"] = Field(
        ..., description="Type of round"
    )

    started_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Round start time"
    )
    completed_at: Optional[str] = Field(None, description="Round completion time")

    # Per-round data
    submissions: Optional[List[TeamInputV1]] = Field(None, description="Team inputs (submission rounds)")
    synthesis_options: Optional[List[SynthesisOptionV1]] = Field(None, description="Generated options (synthesis rounds)")
    votes: Optional[List[VoteV1]] = Field(None, description="Votes (voting rounds)")
    conflicts: Optional[List[ConflictAnalysisV1]] = Field(None, description="Detected conflicts")
    convergence_status: Optional[ConvergenceStatusV1] = Field(None, description="Convergence assessment")


# ============================================================================
# SESSION MODELS
# ============================================================================


class ParticipantV1(BaseModel):
    """Participant in a deliberation session."""

    user_id: str = Field(..., description="Pseudonymous user ID")
    role: Optional[str] = Field(None, description="Optional role (e.g., PM, Designer, Engineer)")
    joined_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Join timestamp"
    )


class FinalOutcomeV1(BaseModel):
    """Final outcome of converged deliberation."""

    selected_option: SynthesisOptionV1 = Field(..., description="Chosen synthesis option")
    consensus_level: float = Field(..., ge=0.0, le=1.0, description="Final agreement level")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Final quality score")
    converged_at: str = Field(..., description="Convergence timestamp")


class ConvergenceCriteriaV1(BaseModel):
    """Criteria for determining convergence."""

    min_quality_score: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum quality threshold")
    max_rounds: int = Field(default=5, ge=1, le=20, description="Maximum rounds before forced decision")
    min_agreement: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum agreement level")


class DeliberationSessionV1(BaseModel):
    """Multi-round deliberation session."""

    session_id: str = Field(default_factory=lambda: f"session-{uuid4()}", description="Unique session ID")
    decision_context: str = Field(..., max_length=1000, description="Decision background context")

    participants: List[ParticipantV1] = Field(..., min_length=2, description="Session participants")

    rounds: List[DeliberationRoundV1] = Field(default_factory=list, description="Deliberation rounds")

    convergence_criteria: ConvergenceCriteriaV1 = Field(
        default_factory=ConvergenceCriteriaV1,
        description="Convergence criteria"
    )

    final_outcome: Optional[FinalOutcomeV1] = Field(None, description="Final outcome if converged")

    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Session creation time"
    )
    status: Literal["active", "converged", "abandoned"] = Field(default="active", description="Session status")


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================


class StartDeliberationRequestV1(BaseModel):
    """Request to start a new deliberation session."""

    decision_context: str = Field(..., max_length=1000, description="Decision background")
    participants: List[str] = Field(..., min_length=2, max_length=20, description="Participant user IDs")
    convergence_criteria: Optional[ConvergenceCriteriaV1] = Field(None, description="Optional convergence criteria")


class StartDeliberationResponseV1(BaseModel):
    """Response from starting a deliberation session."""

    session_id: str
    round_id: str = Field(..., description="ID of first round")
    round_type: Literal["submission"] = Field(..., description="First round type (always submission)")
    instructions: str = Field(..., description="What participants should do")
    deadline: Optional[str] = Field(None, description="Optional round deadline")


class SubmitInputRequestV1(BaseModel):
    """Request to submit input for a round."""

    user_id: str = Field(..., description="Participant user ID")
    round_id: str = Field(..., description="Round ID")
    graph: GraphV1 = Field(..., description="Causal graph")
    reasoning: str = Field(..., max_length=2000, description="Natural language reasoning")


class SubmitInputResponseV1(BaseModel):
    """Response from input submission."""

    accepted: bool = Field(..., description="Whether submission was accepted")
    causal_quality: CausalQualityV1 = Field(..., description="Causal quality assessment")
    validation_issues: List[str] = Field(default_factory=list, description="Validation warnings/errors")


class SubmitVoteRequestV1(BaseModel):
    """Request to submit a vote."""

    user_id: str = Field(..., description="Participant user ID")
    round_id: str = Field(..., description="Round ID")
    rankings: List[VoteRankingV1] = Field(..., min_length=1, description="Option rankings")


class SubmitVoteResponseV1(BaseModel):
    """Response from vote submission."""

    vote_id: str
    accepted: bool
    vote_count: int = Field(..., description="Total votes received so far")
    awaiting_votes_from: int = Field(..., description="Number of participants who haven't voted")


class AdvanceRoundRequestV1(BaseModel):
    """Request to advance to next round."""

    session_id: str
    current_round_id: str


class AdvanceRoundResponseV1(BaseModel):
    """Response from advancing round."""

    next_round: Optional[DeliberationRoundV1] = Field(None, description="Next round (if session continues)")
    convergence_check: Optional[ConvergenceStatusV1] = Field(None, description="Convergence assessment")
    session_complete: bool = Field(..., description="Whether session has concluded")
    final_outcome: Optional[FinalOutcomeV1] = Field(None, description="Final outcome if converged")


class DeliberationStatusResponseV1(BaseModel):
    """Current status of a deliberation session."""

    session: DeliberationSessionV1
    current_round: DeliberationRoundV1
    next_action: str = Field(..., description="Human-readable next step")
    awaiting_input_from: List[str] = Field(default_factory=list, description="User IDs who haven't submitted")


class DeliberationTimelineEventV1(BaseModel):
    """Event in deliberation timeline."""

    timestamp: str
    event_type: str
    round_number: int
    description: str
    actor: Optional[str] = Field(None, description="User ID or 'system'")


class RoundDetailsV1(BaseModel):
    """Detailed breakdown of a single round."""

    round_id: str
    round_type: str
    inputs: Optional[List[TeamInputV1]] = None
    synthesis_options: Optional[List[SynthesisOptionV1]] = None
    votes: Optional[VotingSummaryV1] = None
    convergence: Optional[ConvergenceStatusV1] = None


class DeliberationHistoryResponseV1(BaseModel):
    """Complete deliberation history."""

    session: DeliberationSessionV1
    timeline: List[DeliberationTimelineEventV1]
    round_details: List[RoundDetailsV1]


# ============================================================================
# ENHANCED CONFLICT DIAGNOSIS MODELS
# ============================================================================


class ResolutionCriteriaV1(BaseModel):
    """Criteria for resolving a test."""

    outcome: str = Field(..., description="Expected test outcome")
    supports_hypothesis: Literal["A", "B", "neither"] = Field(..., description="Which hypothesis this supports")


class SuggestedTestV1(BaseModel):
    """Details of suggested experiment."""

    description: str = Field(..., max_length=500)
    test_type: Literal["A/B test", "observational study", "historical analysis", "expert consultation"]

    metrics: List[str] = Field(..., description="What to measure")
    intervention: Optional[str] = Field(None, description="Intervention (for A/B tests)")

    resolution_criteria: List[ResolutionCriteriaV1]

    estimated_duration: str
    estimated_cost: Literal["low", "medium", "high"]
    confidence_gain: float = Field(..., ge=0.0, le=1.0, description="Expected uncertainty reduction")


class DecisiveTestV1(BaseModel):
    """Decisive test to resolve causal conflict."""

    conflict_id: str
    hypothesis_a: str
    hypothesis_b: str

    suggested_test: SuggestedTestV1

    alternative_resolution: Optional[str] = Field(None, description="Fallback if test infeasible")


class ParetoOptionV1(BaseModel):
    """Option in Pareto frontier."""

    option_id: str
    scores: Dict[str, float] = Field(..., description="Score for each dimension")
    pareto_optimal: bool = Field(..., description="Whether this is Pareto optimal")
    dominated_by: List[str] = Field(default_factory=list, description="Options that strictly dominate this")


class DimensionV1(BaseModel):
    """Dimension for Pareto analysis."""

    dimension: str
    unit: str
    stakeholders_prioritizing: List[str] = Field(..., description="User IDs prioritizing this dimension")


class ParetoAnalysisV1(BaseModel):
    """Pareto frontier analysis for values conflicts."""

    conflict_id: str
    dimensions: List[DimensionV1]
    pareto_options: List[ParetoOptionV1]
    recommendation: str


class AlternativePathV1(BaseModel):
    """Alternative path to shared goal."""

    path_description: str
    supporting_stakeholders: List[str]
    causal_mechanism: str
    potential_synergies: List[str]


class SharedGoalV1(BaseModel):
    """Shared goal extracted from conflicting positions."""

    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[str] = Field(..., description="Quotes showing agreement")


class ReframingAnalysisV1(BaseModel):
    """Reframing analysis for framing conflicts."""

    conflict_id: str
    original_positions: List[str]

    shared_goal: SharedGoalV1
    alternative_paths: List[AlternativePathV1]

    reframed_question: str = Field(..., description="New framing emphasizing shared goal")


# ============================================================================
# EVIDENCE TRACKING MODELS
# ============================================================================


class CausalPathV1(BaseModel):
    """Causal path in a graph."""

    source_node: str
    target_node: str
    mechanism: List[str] = Field(..., description="Intermediate nodes")
    edge_types: List[str] = Field(..., description="Causal relationship types")


class EvidenceItemV1(BaseModel):
    """Single evidence item linking reasoning to causal graph."""

    evidence_id: str = Field(default_factory=lambda: f"evidence-{uuid4()}")
    user_id: str
    round_id: str

    claim: str = Field(..., description="Natural language causal claim")

    causal_path: CausalPathV1

    evidence_type: Literal["data", "domain_expertise", "prior_experience", "literature"]
    evidence_source: Optional[str] = None
    evidence_strength: Literal["strong", "moderate", "weak", "unsupported"]

    supported_by_isl: bool
    robustness_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    conflicts_with: List[str] = Field(default_factory=list, description="Evidence IDs of contradicting claims")


class UnsupportedClaimWarningV1(BaseModel):
    """Warning about unsupported causal claim."""

    claim: str
    user_id: str
    issue: Literal["no_causal_path", "unidentified", "contradicts_evidence", "low_robustness"]
    suggestion: str


class ExperimentSuggestionV1(BaseModel):
    """Suggested experiment to test disputed mechanism."""

    experiment_id: str = Field(default_factory=lambda: f"exp-{uuid4()}")
    motivation: str

    disputed_mechanism: Dict[str, Any] = Field(..., description="Nodes and hypothesis strength")

    experiment: Dict[str, Any] = Field(..., description="Experiment details")

    priority: Literal["high", "medium", "low"]


# ============================================================================
# FACET ROBUSTNESS MODELS
# ============================================================================


class RobustRegionV1(BaseModel):
    """Region of robust counterfactuals."""

    interventions: List[str]
    all_lead_to: str = Field(..., description="Consistent outcome")


class RobustnessDetailsV1(BaseModel):
    """Detailed robustness analysis."""

    scenarios_tested: int = Field(..., ge=0)
    scenarios_supporting: int = Field(..., ge=0)
    scenarios_contradicting: int = Field(..., ge=0)

    robust_region: Optional[RobustRegionV1] = None


class ConfidenceIntervalV1(BaseModel):
    """Confidence interval for robustness estimate."""

    lower: float = Field(..., ge=0.0, le=1.0)
    upper: float = Field(..., ge=0.0, le=1.0)
    confidence_level: float = Field(default=0.95, ge=0.0, le=1.0)


class SensitivityFactorV1(BaseModel):
    """Sensitivity to confounding variable."""

    factor: str
    impact_on_estimate: Literal["high", "medium", "low"]


class RobustnessAnalysisV1(BaseModel):
    """FACET robustness analysis for causal claim."""

    perspective_id: str
    causal_claim: str

    identification_status: Literal["identified", "partial", "unidentified"]

    robustness_score: float = Field(..., ge=0.0, le=1.0, description="FACET counterfactual robustness")
    robustness_analysis: RobustnessDetailsV1

    confidence_interval: ConfidenceIntervalV1

    sensitivity_factors: List[SensitivityFactorV1] = Field(default_factory=list)
