"""SQLAlchemy database models."""

from sqlalchemy import Column, String, DateTime, JSON, Float, Boolean, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from src.storage.database import Base
from src.models.enums import (
    SessionStatus,
    AlignmentMode,
    DecisionType,
    StakeholderRole,
    RiskLevel,
    TimeHorizon,
    ValidationStatus,
    ConcernStatus,
)


class SessionDB(Base):
    """Database model for alignment sessions."""

    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    decision_topic = Column(String(500), nullable=False)
    decision_context = Column(String(2000), nullable=False)
    decision_type = Column(SQLEnum(DecisionType), nullable=False)
    alignment_mode = Column(SQLEnum(AlignmentMode), nullable=False)
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.COLLECTING)

    stakeholders = Column(JSON, nullable=False)
    shared_ground = Column(JSON, nullable=True)
    disagreement_map = Column(JSON, nullable=True)

    scenario_model_id = Column(UUID(as_uuid=True), nullable=True)
    scenario_parameter_deltas = Column(JSON, nullable=True)

    selected_option_id = Column(UUID(as_uuid=True), nullable=True)

    # Phase C: Multi-round deliberation support
    parent_session_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    reopened_from_id = Column(UUID(as_uuid=True), nullable=True)
    chain_depth = Column(Integer, nullable=False, default=0)

    # Phase D: Organizational intelligence
    organization_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)


class ProfileDB(Base):
    """Database model for stakeholder profiles."""

    __tablename__ = "profiles"

    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String(100), nullable=False)
    stakeholder_role = Column(SQLEnum(StakeholderRole), nullable=False)

    desired_outcome = Column(String(1000), nullable=False)
    key_concerns = Column(JSON, nullable=False)
    preferred_option = Column(String(1000), nullable=True)

    goal_weights = Column(JSON, nullable=False)
    risk_tolerance = Column(SQLEnum(RiskLevel), nullable=False)
    time_horizon = Column(SQLEnum(TimeHorizon), nullable=False)
    must_have_constraints = Column(JSON, nullable=False)
    red_lines = Column(JSON, nullable=False)

    extraction_confidence = Column(Float, nullable=False, default=1.0)
    extraction_source = Column(String(50), nullable=False, default="cee")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class OptionDB(Base):
    """Database model for proposed options."""

    __tablename__ = "options"

    option_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    proposed_by = Column(String(100), nullable=False)
    round_number = Column(Integer, nullable=False, default=1)

    title = Column(String(200), nullable=False)
    description = Column(String(2000), nullable=False)
    expected_outcome = Column(String(1000), nullable=False)
    causal_rationale = Column(String(2000), nullable=False)

    addresses_goals = Column(JSON, nullable=False)
    trade_offs = Column(JSON, nullable=False)
    key_assumptions = Column(JSON, nullable=False)

    scenario_link = Column(JSON, nullable=True)
    is_baseline = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default="proposed")

    # Phase C: AI-powered option creation metadata
    ai_generation_metadata = Column(JSON, nullable=True)
    synthesis_metadata = Column(JSON, nullable=True)
    tuning_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ValidationDB(Base):
    """Database model for causal validations."""

    __tablename__ = "validations"

    validation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    option_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    is_identifiable = Column(Boolean, nullable=False)
    validation_status = Column(SQLEnum(ValidationStatus), nullable=False)
    data_sufficiency = Column(String(50), nullable=False)

    predicted_outcomes = Column(JSON, nullable=False)
    key_assumptions = Column(JSON, nullable=False)

    warnings = Column(JSON, nullable=False)
    quality_concerns = Column(JSON, nullable=False)
    sensitivity_factors = Column(JSON, nullable=False)

    isl_response = Column(JSON, nullable=False)
    isl_request_id = Column(String(100), nullable=True)

    validated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FitDB(Base):
    """Database model for option fit analysis."""

    __tablename__ = "fits"

    fit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    option_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    stakeholder_fits = Column(JSON, nullable=False)
    overall_alignment = Column(Float, nullable=False)
    consensus_level = Column(String(50), nullable=False)

    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ConcernDB(Base):
    """Database model for minority concerns."""

    __tablename__ = "concerns"

    concern_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    option_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    raised_by = Column(UUID(as_uuid=True), nullable=False)

    concern_text = Column(String(1000), nullable=False)
    concern_type = Column(String(50), nullable=False)
    assumption_id_tested = Column(String(100), nullable=True)

    sensitivity_tested = Column(Boolean, nullable=False, default=False)
    causal_validation = Column(JSON, nullable=True)

    status = Column(SQLEnum(ConcernStatus), nullable=False, default=ConcernStatus.RAISED)
    resolution = Column(String(2000), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)


class DecisionBriefDB(Base):
    """Database model for decision briefs."""

    __tablename__ = "decision_briefs"

    brief_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True, unique=True)

    chosen_option = Column(JSON, nullable=False)
    decision_rationale = Column(String(2000), nullable=False)

    stakeholder_support = Column(JSON, nullable=False)
    consensus_strength = Column(Float, nullable=False)

    validated_outcomes = Column(JSON, nullable=False)
    accepted_assumptions = Column(JSON, nullable=False)
    monitored_risks = Column(JSON, nullable=False)

    minority_concerns_raised = Column(JSON, nullable=False)
    minority_concerns_addressed = Column(JSON, nullable=False)

    review_date = Column(DateTime, nullable=False)
    success_criteria = Column(JSON, nullable=False)
    monitoring_plan = Column(JSON, nullable=False)

    scenario_model_id = Column(UUID(as_uuid=True), nullable=True)
    scenario_snapshot = Column(JSON, nullable=True)

    decision_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    participants = Column(JSON, nullable=False)
    exported_at = Column(DateTime, nullable=True)

    decision_quality_rating = Column(Integer, nullable=True)
    post_decision_notes = Column(String(2000), nullable=True)


class AssumptionValidationDB(Base):
    """Database model for assumption validation records (Phase C)."""

    __tablename__ = "assumption_validations"

    validation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assumption_id = Column(String(200), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    validation_method = Column(String(100), nullable=False)  # a_b_test, technical_spike, user_research
    validation_result = Column(String(50), nullable=False)  # confirmed, rejected, modified
    validation_notes = Column(String(2000), nullable=False)

    validated_at = Column(DateTime, nullable=False)
    validated_by = Column(UUID(as_uuid=True), nullable=False)

    updated_assumption = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DecisionRetrospectiveDB(Base):
    """Database model for decision retrospectives (Phase C)."""

    __tablename__ = "decision_retrospectives"

    retrospective_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    brief_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    actual_outcomes = Column(JSON, nullable=False)  # Dict[str, float]
    outcome_comparison = Column(JSON, nullable=False)  # OutcomeComparison data
    assumption_results = Column(JSON, nullable=False)  # List of assumption validation results
    assumption_analysis = Column(JSON, nullable=False)  # Analysis of which assumptions held

    narrative = Column(String(5000), nullable=False)  # Human-readable summary
    lessons_learned = Column(JSON, nullable=False)  # List of lessons

    # Phase D: Analytics ratings
    quality_rating = Column(Float, nullable=True)  # 1-10 scale
    satisfaction_rating = Column(Float, nullable=True)  # 1-10 scale
    would_repeat_decision = Column(Boolean, nullable=True)

    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    recorded_by = Column(UUID(as_uuid=True), nullable=False)

# Phase D: Organizational Intelligence Models

class DecisionDependencyDB(Base):
    """Database model for decision dependencies (Phase D3)."""

    __tablename__ = "decision_dependencies"

    dependency_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    target_session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    dependency_type = Column(String(50), nullable=False)  # blocks, related_to, supersedes, depends_on
    description = Column(String(500), nullable=True)
    
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True, index=True)


class PatternAnalysisCacheDB(Base):
    """Database model for cached pattern analysis (Phase D4)."""

    __tablename__ = "pattern_analysis_cache"

    cache_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    decision_type = Column(String(100), nullable=False)
    pattern_type = Column(String(50), nullable=False)  # success, failure, neutral
    
    sample_size = Column(Integer, nullable=False)
    common_characteristics = Column(JSON, nullable=False)
    avg_metrics = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    recommendations = Column(JSON, nullable=False)
    
    analysis_period_days = Column(Integer, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


class CoordinationGroupDB(Base):
    """Database model for coordination groups (Phase D6)."""

    __tablename__ = "coordination_groups"

    group_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=False)
    session_ids = Column(JSON, nullable=False)  # List of UUIDs as strings
    
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    archived_at = Column(DateTime, nullable=True, index=True)


class DetectedConflictDB(Base):
    """Database model for detected conflicts (Phase D6)."""

    __tablename__ = "detected_conflicts"

    conflict_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conflict_type = Column(String(50), nullable=False, index=True)  # temporal, resource, dependency, scope
    session_ids = Column(JSON, nullable=False)  # List of UUIDs as strings
    severity = Column(String(20), nullable=False, index=True)  # high, medium, low
    
    description = Column(String(1000), nullable=False)
    resolution_suggestions = Column(JSON, nullable=False)
    
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True, index=True)
    resolution_description = Column(String(1000), nullable=True)


class AnalyticsCacheDB(Base):
    """Database model for analytics cache (Phase D5)."""

    __tablename__ = "analytics_cache"

    cache_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False, index=True)  # trend, benchmark
    metric_name = Column(String(100), nullable=True)
    decision_type = Column(String(100), nullable=True)

    result_data = Column(JSON, nullable=False)

    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


# Phase 1A/1B: Multi-Round Deliberation Models

class DeliberationSessionDB(Base):
    """Database model for deliberation sessions (Phase 1A/1B)."""

    __tablename__ = "deliberation_sessions"

    session_id = Column(String(100), primary_key=True)
    decision_context = Column(String(1000), nullable=False)
    participants = Column(JSON, nullable=False)  # List of ParticipantV1 dicts
    status = Column(String(50), nullable=False, default="active")  # active, converged, abandoned

    # Convergence criteria
    convergence_criteria = Column(JSON, nullable=False)

    # Final outcome (when converged)
    final_outcome = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DeliberationRoundDB(Base):
    """Database model for deliberation rounds (Phase 1A/1B)."""

    __tablename__ = "deliberation_rounds"

    round_id = Column(String(100), primary_key=True)
    session_id = Column(String(100), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    round_type = Column(String(50), nullable=False)  # submission, synthesis, voting, refinement

    # Round metadata
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Synthesis options (for synthesis/voting rounds)
    synthesis_options = Column(JSON, nullable=True)

    # Convergence status (computed after voting)
    convergence_status = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DeliberationSubmissionDB(Base):
    """Database model for deliberation submissions (Phase 1A/1B)."""

    __tablename__ = "deliberation_submissions"

    submission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False)

    # Input data
    graph = Column(JSON, nullable=False)  # GraphV1 dict
    reasoning = Column(String(2000), nullable=False)

    # Validation results
    causal_quality = Column(JSON, nullable=False)  # CausalQualityV1 dict
    validation_issues = Column(JSON, nullable=False)  # List of validation issues

    # Evidence items extracted from this submission
    evidence_items = Column(JSON, nullable=True)  # List of EvidenceItemV1 dicts
    unsupported_claims = Column(JSON, nullable=True)  # List of warnings

    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DeliberationVoteDB(Base):
    """Database model for deliberation votes (Phase 1A/1B)."""

    __tablename__ = "deliberation_votes"

    vote_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)

    # Encrypted user ID (for anonymity during active voting)
    encrypted_user_id = Column(String(200), nullable=False)

    # Actual user ID (only revealed after round closes)
    user_id = Column(String(100), nullable=True)

    # Vote data
    rankings = Column(JSON, nullable=False)  # List of RankingV1 dicts

    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DeliberationConflictDB(Base):
    """Database model for deliberation conflicts (Phase 1A/1B)."""

    __tablename__ = "deliberation_conflicts"

    conflict_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), nullable=False, index=True)
    round_id = Column(String(100), nullable=False, index=True)

    # Conflict data
    conflict_analysis = Column(JSON, nullable=False)  # ConflictAnalysisV1 dict

    # Enhanced conflict diagnosis
    decisive_test = Column(JSON, nullable=True)  # DecisiveTestV1 dict
    pareto_analysis = Column(JSON, nullable=True)  # ParetoAnalysisV1 dict
    reframing_analysis = Column(JSON, nullable=True)  # ReframingAnalysisV1 dict

    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)


# Phase 3: Aggregation Intelligence Models

class UserAccuracyHistoryDB(Base):
    """Database model for user accuracy history (Phase 3: Navajas)."""

    __tablename__ = "user_accuracy_history"

    record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(100), nullable=True, index=True)

    # Prediction details
    domain = Column(String(100), nullable=False, index=True)
    decision_type = Column(String(100), nullable=False)
    stated_confidence = Column(Float, nullable=False)  # 0.0-1.0
    prediction_text = Column(String(2000), nullable=True)

    # Outcome details
    actual_outcome = Column(String(2000), nullable=True)
    outcome_known = Column(Boolean, nullable=False, default=False)
    outcome_recorded_at = Column(DateTime, nullable=True)

    # Accuracy metrics
    brier_score = Column(Float, nullable=True)  # 0.0 (perfect) to 1.0 (worst)
    was_correct = Column(Boolean, nullable=True)
    confidence_error = Column(Float, nullable=True)  # signed error: stated - actual

    # Metadata
    predicted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserDomainExpertiseDB(Base):
    """Database model for user domain expertise (Phase 3: Navajas)."""

    __tablename__ = "user_domain_expertise"

    expertise_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, index=True)
    domain = Column(String(100), nullable=False, index=True)

    # Expertise metrics
    role_relevance = Column(Float, nullable=False, default=0.5)  # 0.0-1.0
    historical_accuracy = Column(Float, nullable=False, default=0.5)  # avg Brier score
    prediction_count = Column(Integer, nullable=False, default=0)

    # Calibration factors
    overconfidence_bias = Column(Float, nullable=False, default=0.0)  # 0.0 = well calibrated
    avg_confidence_error = Column(Float, nullable=False, default=0.0)

    # Last updated
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Phase 5: Autonomous Learning Models

class DecisionOutcomeDB(Base):
    """Database model for decision outcomes (Phase 5)."""

    __tablename__ = "decision_outcomes"

    outcome_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), nullable=False, index=True)

    # Decision details
    decision = Column(JSON, nullable=False)  # {selected_option, decided_at, decision_graph, key_assumptions}

    # Predictions and actuals
    predicted_outcomes = Column(JSON, nullable=False)  # List of PredictedOutcomeV1 dicts
    actual_outcomes = Column(JSON, nullable=True)  # List of ActualOutcomeV1 dicts

    # Status tracking
    status = Column(String(20), nullable=False, default="predicted", index=True)  # predicted, monitoring, measured, analyzed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    measured_at = Column(DateTime, nullable=True)


class OutcomeMeasurementDB(Base):
    """Database model for outcome measurements (Phase 5)."""

    __tablename__ = "outcome_measurements"

    measurement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outcome_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Measurement details
    metric = Column(String(100), nullable=False, index=True)
    actual_value = Column(Float, nullable=False)
    predicted_value = Column(Float, nullable=False)
    variance = Column(Float, nullable=False)  # Prediction error percentage

    # Metadata
    notes = Column(String(2000), nullable=True)
    measured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
