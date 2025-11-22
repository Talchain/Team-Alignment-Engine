-- Add performance indexes for TAE database
-- Run this migration in production to improve query performance

-- Sessions table indexes for portfolio analytics (D1)
CREATE INDEX IF NOT EXISTS idx_sessions_org_created
    ON sessions(organization_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_team_status
    ON sessions(team_id, status);

CREATE INDEX IF NOT EXISTS idx_sessions_status_completed
    ON sessions(status, completed_at DESC)
    WHERE status = 'complete';

-- Profiles table indexes
CREATE INDEX IF NOT EXISTS idx_profiles_session_created
    ON profiles(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_profiles_user
    ON profiles(user_id);

-- Options table indexes
CREATE INDEX IF NOT EXISTS idx_options_session_round
    ON options(session_id, round_number);

-- Validations table indexes
CREATE INDEX IF NOT EXISTS idx_validations_option
    ON validations(option_id);

CREATE INDEX IF NOT EXISTS idx_validations_status
    ON validations(validation_status);

-- Decision briefs table indexes
CREATE INDEX IF NOT EXISTS idx_briefs_session
    ON decision_briefs(session_id);

CREATE INDEX IF NOT EXISTS idx_briefs_quality
    ON decision_briefs(decision_quality_rating)
    WHERE decision_quality_rating IS NOT NULL;

-- Phase D: Decision dependencies indexes (D3)
CREATE INDEX IF NOT EXISTS idx_deps_source
    ON decision_dependencies(source_session_id);

CREATE INDEX IF NOT EXISTS idx_deps_target
    ON decision_dependencies(target_session_id);

CREATE INDEX IF NOT EXISTS idx_deps_resolved
    ON decision_dependencies(resolved_at)
    WHERE resolved_at IS NOT NULL;

-- Phase D: Analytics cache indexes (D5)
CREATE INDEX IF NOT EXISTS idx_analytics_cache_org_type
    ON analytics_cache(organization_id, analysis_type, expires_at);

-- Phase D: Pattern cache indexes (D4)
CREATE INDEX IF NOT EXISTS idx_pattern_cache_org_type
    ON pattern_analysis_cache(organization_id, decision_type, expires_at);

-- Phase D: Conflicts indexes (D6)
CREATE INDEX IF NOT EXISTS idx_conflicts_severity
    ON detected_conflicts(severity, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_conflicts_resolved
    ON detected_conflicts(resolved_at)
    WHERE resolved_at IS NOT NULL;

-- Retrospectives indexes
CREATE INDEX IF NOT EXISTS idx_retrospectives_session
    ON decision_retrospectives(session_id);

CREATE INDEX IF NOT EXISTS idx_retrospectives_quality
    ON decision_retrospectives(quality_rating DESC)
    WHERE quality_rating IS NOT NULL;

-- Concerns indexes
CREATE INDEX IF NOT EXISTS idx_concerns_option_status
    ON concerns(option_id, status);

-- ANALYZE tables to update statistics
ANALYZE sessions;
ANALYZE profiles;
ANALYZE options;
ANALYZE validations;
ANALYZE decision_briefs;
ANALYZE decision_dependencies;
ANALYZE analytics_cache;
ANALYZE pattern_analysis_cache;
ANALYZE detected_conflicts;
ANALYZE decision_retrospectives;
ANALYZE concerns;
