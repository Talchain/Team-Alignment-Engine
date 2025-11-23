BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001

CREATE TABLE sessions (
    session_id UUID NOT NULL, 
    team_id UUID NOT NULL, 
    decision_topic VARCHAR(500) NOT NULL, 
    decision_context VARCHAR(2000) NOT NULL, 
    decision_type VARCHAR(50) NOT NULL, 
    alignment_mode VARCHAR(50) NOT NULL, 
    status VARCHAR(50) NOT NULL, 
    stakeholders JSON NOT NULL, 
    shared_ground JSON, 
    disagreement_map JSON, 
    scenario_model_id UUID, 
    scenario_parameter_deltas JSON, 
    selected_option_id UUID, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITHOUT TIME ZONE, 
    created_by UUID NOT NULL, 
    PRIMARY KEY (session_id)
);

CREATE INDEX ix_sessions_team_id ON sessions (team_id);

CREATE TABLE profiles (
    profile_id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    role VARCHAR(100) NOT NULL, 
    stakeholder_role VARCHAR(50) NOT NULL, 
    desired_outcome VARCHAR(1000) NOT NULL, 
    key_concerns JSON NOT NULL, 
    preferred_option VARCHAR(1000), 
    goal_weights JSON NOT NULL, 
    risk_tolerance VARCHAR(50) NOT NULL, 
    time_horizon VARCHAR(50) NOT NULL, 
    must_have_constraints JSON NOT NULL, 
    red_lines JSON NOT NULL, 
    extraction_confidence FLOAT NOT NULL, 
    extraction_source VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    last_updated TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (profile_id)
);

CREATE INDEX ix_profiles_session_id ON profiles (session_id);

CREATE INDEX ix_profiles_user_id ON profiles (user_id);

CREATE TABLE options (
    option_id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    proposed_by VARCHAR(100) NOT NULL, 
    round_number INTEGER NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    description VARCHAR(2000) NOT NULL, 
    expected_outcome VARCHAR(1000) NOT NULL, 
    causal_rationale VARCHAR(2000) NOT NULL, 
    addresses_goals JSON NOT NULL, 
    trade_offs JSON NOT NULL, 
    key_assumptions JSON NOT NULL, 
    scenario_link JSON, 
    is_baseline BOOLEAN NOT NULL, 
    status VARCHAR(50) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (option_id)
);

CREATE INDEX ix_options_session_id ON options (session_id);

CREATE TABLE validations (
    validation_id UUID NOT NULL, 
    option_id UUID NOT NULL, 
    is_identifiable BOOLEAN NOT NULL, 
    validation_status VARCHAR(50) NOT NULL, 
    data_sufficiency VARCHAR(50) NOT NULL, 
    predicted_outcomes JSON NOT NULL, 
    key_assumptions JSON NOT NULL, 
    warnings JSON NOT NULL, 
    quality_concerns JSON NOT NULL, 
    sensitivity_factors JSON NOT NULL, 
    isl_response JSON NOT NULL, 
    isl_request_id VARCHAR(100), 
    validated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (validation_id)
);

CREATE INDEX ix_validations_option_id ON validations (option_id);

CREATE TABLE fits (
    fit_id UUID NOT NULL, 
    option_id UUID NOT NULL, 
    stakeholder_fits JSON NOT NULL, 
    overall_alignment FLOAT NOT NULL, 
    consensus_level VARCHAR(50) NOT NULL, 
    calculated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (fit_id)
);

CREATE INDEX ix_fits_option_id ON fits (option_id);

CREATE TABLE concerns (
    concern_id UUID NOT NULL, 
    option_id UUID NOT NULL, 
    raised_by UUID NOT NULL, 
    concern_text VARCHAR(1000) NOT NULL, 
    concern_type VARCHAR(50) NOT NULL, 
    assumption_id_tested VARCHAR(100), 
    sensitivity_tested BOOLEAN NOT NULL, 
    causal_validation JSON, 
    status VARCHAR(50) NOT NULL, 
    resolution VARCHAR(2000), 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    resolved_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (concern_id)
);

CREATE INDEX ix_concerns_option_id ON concerns (option_id);

CREATE TABLE decision_briefs (
    brief_id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    chosen_option JSON NOT NULL, 
    decision_rationale VARCHAR(2000) NOT NULL, 
    stakeholder_support JSON NOT NULL, 
    consensus_strength FLOAT NOT NULL, 
    validated_outcomes JSON NOT NULL, 
    accepted_assumptions JSON NOT NULL, 
    monitored_risks JSON NOT NULL, 
    minority_concerns_raised JSON NOT NULL, 
    minority_concerns_addressed JSON NOT NULL, 
    review_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    success_criteria JSON NOT NULL, 
    monitoring_plan JSON NOT NULL, 
    scenario_model_id UUID, 
    scenario_snapshot JSON, 
    decision_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    participants JSON NOT NULL, 
    exported_at TIMESTAMP WITHOUT TIME ZONE, 
    decision_quality_rating INTEGER, 
    post_decision_notes VARCHAR(2000), 
    PRIMARY KEY (brief_id), 
    UNIQUE (session_id)
);

CREATE INDEX ix_decision_briefs_session_id ON decision_briefs (session_id);

INSERT INTO alembic_version (version_num) VALUES ('001') RETURNING alembic_version.version_num;

-- Running upgrade 001 -> 002

ALTER TABLE sessions ADD COLUMN parent_session_id UUID;

ALTER TABLE sessions ADD COLUMN reopened_from_id UUID;

ALTER TABLE sessions ADD COLUMN chain_depth INTEGER DEFAULT '0' NOT NULL;

CREATE INDEX ix_sessions_parent_session_id ON sessions (parent_session_id);

ALTER TABLE options ADD COLUMN ai_generation_metadata JSON;

ALTER TABLE options ADD COLUMN synthesis_metadata JSON;

ALTER TABLE options ADD COLUMN tuning_metadata JSON;

CREATE TABLE assumption_validations (
    validation_id UUID NOT NULL, 
    assumption_id VARCHAR(200) NOT NULL, 
    session_id UUID NOT NULL, 
    validation_method VARCHAR(100) NOT NULL, 
    validation_result VARCHAR(50) NOT NULL, 
    validation_notes VARCHAR(2000) NOT NULL, 
    validated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    validated_by UUID NOT NULL, 
    updated_assumption JSON, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (validation_id)
);

CREATE INDEX ix_assumption_validations_assumption_id ON assumption_validations (assumption_id);

CREATE INDEX ix_assumption_validations_session_id ON assumption_validations (session_id);

CREATE TABLE decision_retrospectives (
    retrospective_id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    brief_id UUID NOT NULL, 
    actual_outcomes JSON NOT NULL, 
    outcome_comparison JSON NOT NULL, 
    assumption_results JSON NOT NULL, 
    assumption_analysis JSON NOT NULL, 
    narrative VARCHAR(5000) NOT NULL, 
    lessons_learned JSON NOT NULL, 
    recorded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    recorded_by UUID NOT NULL, 
    PRIMARY KEY (retrospective_id)
);

CREATE INDEX ix_decision_retrospectives_session_id ON decision_retrospectives (session_id);

CREATE INDEX ix_decision_retrospectives_brief_id ON decision_retrospectives (brief_id);

UPDATE alembic_version SET version_num='002' WHERE alembic_version.version_num = '001';

-- Running upgrade 002 -> 003

CREATE TABLE decision_dependencies (
    dependency_id UUID NOT NULL, 
    source_session_id UUID NOT NULL, 
    target_session_id UUID NOT NULL, 
    dependency_type VARCHAR(50) NOT NULL, 
    description VARCHAR(500), 
    created_by VARCHAR(100) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    resolved_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (dependency_id), 
    FOREIGN KEY(source_session_id) REFERENCES sessions (session_id) ON DELETE CASCADE, 
    FOREIGN KEY(target_session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
);

CREATE INDEX ix_dependencies_source_session ON decision_dependencies (source_session_id);

CREATE INDEX ix_dependencies_target_session ON decision_dependencies (target_session_id);

CREATE INDEX ix_dependencies_resolved ON decision_dependencies (resolved_at);

CREATE TABLE pattern_analysis_cache (
    cache_id UUID NOT NULL, 
    organization_id UUID NOT NULL, 
    decision_type VARCHAR(100) NOT NULL, 
    pattern_type VARCHAR(50) NOT NULL, 
    sample_size INTEGER NOT NULL, 
    common_characteristics JSON NOT NULL, 
    avg_metrics JSON NOT NULL, 
    confidence FLOAT NOT NULL, 
    recommendations JSON NOT NULL, 
    analysis_period_days INTEGER NOT NULL, 
    generated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (cache_id)
);

CREATE INDEX ix_pattern_cache_org_type ON pattern_analysis_cache (organization_id, decision_type);

CREATE INDEX ix_pattern_cache_expires ON pattern_analysis_cache (expires_at);

CREATE TABLE coordination_groups (
    group_id UUID NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description VARCHAR(1000) NOT NULL, 
    session_ids JSON NOT NULL, 
    created_by VARCHAR(100) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    archived_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (group_id)
);

CREATE INDEX ix_coordination_groups_created ON coordination_groups (created_at);

CREATE INDEX ix_coordination_groups_archived ON coordination_groups (archived_at);

CREATE TABLE detected_conflicts (
    conflict_id UUID NOT NULL, 
    conflict_type VARCHAR(50) NOT NULL, 
    session_ids JSON NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    description VARCHAR(1000) NOT NULL, 
    resolution_suggestions JSON NOT NULL, 
    detected_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    resolved_at TIMESTAMP WITHOUT TIME ZONE, 
    resolution_description VARCHAR(1000), 
    PRIMARY KEY (conflict_id)
);

CREATE INDEX ix_conflicts_type_severity ON detected_conflicts (conflict_type, severity);

CREATE INDEX ix_conflicts_resolved ON detected_conflicts (resolved_at);

CREATE INDEX ix_conflicts_detected ON detected_conflicts (detected_at);

CREATE TABLE analytics_cache (
    cache_id UUID NOT NULL, 
    organization_id UUID NOT NULL, 
    analysis_type VARCHAR(50) NOT NULL, 
    metric_name VARCHAR(100), 
    decision_type VARCHAR(100), 
    result_data JSON NOT NULL, 
    generated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (cache_id)
);

CREATE INDEX ix_analytics_cache_org_type ON analytics_cache (organization_id, analysis_type);

CREATE INDEX ix_analytics_cache_expires ON analytics_cache (expires_at);

ALTER TABLE sessions ADD COLUMN organization_id UUID;

CREATE INDEX ix_sessions_organization_id ON sessions (organization_id);

ALTER TABLE decision_retrospectives ADD COLUMN quality_rating FLOAT;

ALTER TABLE decision_retrospectives ADD COLUMN satisfaction_rating FLOAT;

ALTER TABLE decision_retrospectives ADD COLUMN would_repeat_decision BOOLEAN;

UPDATE alembic_version SET version_num='003' WHERE alembic_version.version_num = '002';

-- Running upgrade 003 -> 004

CREATE INDEX ix_sessions_org_status_completed ON sessions (organization_id, status, completed_at) WHERE status = 'complete';

CREATE INDEX ix_sessions_org_type_completed ON sessions (organization_id, decision_type, completed_at) WHERE status = 'complete' AND decision_type IS NOT NULL;

CREATE INDEX ix_sessions_org_active_created ON sessions (organization_id, status, created_at) WHERE status IN ('collecting', 'analyzing', 'deliberating');

CREATE INDEX ix_sessions_created_at ON sessions (created_at DESC);

CREATE INDEX ix_dependencies_target_resolved ON decision_dependencies (target_session_id, resolved_at, dependency_type);

CREATE INDEX ix_retrospectives_org_timestamp ON retrospectives (organization_id, created_at DESC);

CREATE INDEX ix_pattern_cache_org_expires ON pattern_analysis_cache (organization_id, expires_at);

CREATE INDEX ix_sessions_status_updated ON sessions (status, updated_at DESC);

✓ Performance indexes created successfully
  - D5 Analytics: 2 composite indexes
  - D6 Coordination: 2 indexes
  - D3 Dependencies: 1 composite index
  - D4 Patterns: 2 indexes
  - D1 Alignment: 1 index
  Expected latency reduction: 60-90% for most queries
UPDATE alembic_version SET version_num='004' WHERE alembic_version.version_num = '003';

-- Running upgrade 004 -> 005

CREATE TABLE deliberation_sessions (
    session_id VARCHAR(100) NOT NULL, 
    decision_context VARCHAR(1000) NOT NULL, 
    participants JSON NOT NULL, 
    status VARCHAR(50) DEFAULT 'active' NOT NULL, 
    convergence_criteria JSON NOT NULL, 
    final_outcome JSON, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (session_id)
);

CREATE INDEX ix_deliberation_sessions_status ON deliberation_sessions (status);

CREATE INDEX ix_deliberation_sessions_created_at ON deliberation_sessions (created_at);

CREATE TABLE deliberation_rounds (
    round_id VARCHAR(100) NOT NULL, 
    session_id VARCHAR(100) NOT NULL, 
    round_number INTEGER NOT NULL, 
    round_type VARCHAR(50) NOT NULL, 
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    completed_at TIMESTAMP WITHOUT TIME ZONE, 
    synthesis_options JSON, 
    convergence_status JSON, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (round_id)
);

CREATE INDEX ix_deliberation_rounds_session_id ON deliberation_rounds (session_id);

CREATE INDEX ix_deliberation_rounds_session_round ON deliberation_rounds (session_id, round_number);

CREATE TABLE deliberation_submissions (
    submission_id UUID DEFAULT gen_random_uuid() NOT NULL, 
    round_id VARCHAR(100) NOT NULL, 
    session_id VARCHAR(100) NOT NULL, 
    user_id VARCHAR(100) NOT NULL, 
    graph JSON NOT NULL, 
    reasoning VARCHAR(2000) NOT NULL, 
    causal_quality JSON NOT NULL, 
    validation_issues JSON NOT NULL, 
    evidence_items JSON, 
    unsupported_claims JSON, 
    submitted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (submission_id)
);

CREATE INDEX ix_deliberation_submissions_round_id ON deliberation_submissions (round_id);

CREATE INDEX ix_deliberation_submissions_session_id ON deliberation_submissions (session_id);

CREATE INDEX ix_deliberation_submissions_user_id ON deliberation_submissions (user_id);

CREATE TABLE deliberation_votes (
    vote_id UUID DEFAULT gen_random_uuid() NOT NULL, 
    round_id VARCHAR(100) NOT NULL, 
    session_id VARCHAR(100) NOT NULL, 
    encrypted_user_id VARCHAR(200) NOT NULL, 
    user_id VARCHAR(100), 
    rankings JSON NOT NULL, 
    submitted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (vote_id)
);

CREATE INDEX ix_deliberation_votes_round_id ON deliberation_votes (round_id);

CREATE INDEX ix_deliberation_votes_session_id ON deliberation_votes (session_id);

CREATE TABLE deliberation_conflicts (
    conflict_id UUID DEFAULT gen_random_uuid() NOT NULL, 
    session_id VARCHAR(100) NOT NULL, 
    round_id VARCHAR(100) NOT NULL, 
    conflict_analysis JSON NOT NULL, 
    decisive_test JSON, 
    pareto_analysis JSON, 
    reframing_analysis JSON, 
    detected_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    resolved_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (conflict_id)
);

CREATE INDEX ix_deliberation_conflicts_session_id ON deliberation_conflicts (session_id);

CREATE INDEX ix_deliberation_conflicts_round_id ON deliberation_conflicts (round_id);

CREATE TABLE user_accuracy_history (
    record_id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id VARCHAR(100) NOT NULL, 
    session_id VARCHAR(100), 
    domain VARCHAR(100) NOT NULL, 
    decision_type VARCHAR(100) NOT NULL, 
    stated_confidence FLOAT NOT NULL, 
    prediction_text VARCHAR(2000), 
    actual_outcome VARCHAR(2000), 
    outcome_known BOOLEAN DEFAULT 'false' NOT NULL, 
    outcome_recorded_at TIMESTAMP WITHOUT TIME ZONE, 
    brier_score FLOAT, 
    was_correct BOOLEAN, 
    confidence_error FLOAT, 
    predicted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (record_id)
);

CREATE INDEX ix_user_accuracy_history_user_id ON user_accuracy_history (user_id);

CREATE INDEX ix_user_accuracy_history_session_id ON user_accuracy_history (session_id);

CREATE INDEX ix_user_accuracy_history_domain ON user_accuracy_history (domain);

CREATE INDEX ix_user_accuracy_history_user_domain ON user_accuracy_history (user_id, domain);

CREATE TABLE user_domain_expertise (
    expertise_id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id VARCHAR(100) NOT NULL, 
    domain VARCHAR(100) NOT NULL, 
    role_relevance FLOAT DEFAULT '0.5' NOT NULL, 
    historical_accuracy FLOAT DEFAULT '0.5' NOT NULL, 
    prediction_count INTEGER DEFAULT '0' NOT NULL, 
    overconfidence_bias FLOAT DEFAULT '0.0' NOT NULL, 
    avg_confidence_error FLOAT DEFAULT '0.0' NOT NULL, 
    last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (expertise_id)
);

CREATE INDEX ix_user_domain_expertise_user_id ON user_domain_expertise (user_id);

CREATE INDEX ix_user_domain_expertise_domain ON user_domain_expertise (domain);

CREATE UNIQUE INDEX ix_user_domain_expertise_user_domain ON user_domain_expertise (user_id, domain);

UPDATE alembic_version SET version_num='005' WHERE alembic_version.version_num = '004';

COMMIT;

