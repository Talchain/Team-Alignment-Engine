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

    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    recorded_by = Column(UUID(as_uuid=True), nullable=False)
