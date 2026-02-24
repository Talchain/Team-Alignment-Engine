# Changelog

All notable changes to the Team Alignment Engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-31

### Added

#### Phase C: Intelligent Assistance
- AI option generation (C1) - Generate creative options bridging stakeholder disagreements
- Option synthesis (C2) - Combine elements from multiple options into optimal hybrids
- Option tuning (C3) - Adjust options to address minority concerns while preserving core value
- Assumption testing advisor (C4) - Prioritize which assumptions to validate before deciding
- Decision retrospective (C5) - Compare actual vs predicted outcomes, generate lessons learned
- Multi-round deliberation (C6) - Reopen sessions when assumptions fail or context changes

#### Phase D: Organizational Intelligence
- **D1: Portfolio Analytics** - Cross-session decision metrics, health scores, strategic insights
- **D2: Real-Time Collaboration** - WebSocket-based presence tracking, live action broadcasting (<100ms latency)
- **D3: Decision Dependencies** - Dependency graph management with circular dependency prevention
- **D4: Organizational Patterns** - Extract success/failure patterns from historical decisions
- **D5: Advanced Analytics** - Trend analysis, 30-day forecasting, comparative benchmarking
- **D6: Cross-Team Coordination** - Multi-team conflict detection, resolution suggestions

#### Phase 5: Autonomous Learning
- Outcome tracking service - Track decision outcomes with predictions and measurement schedules
- Pattern learning - Identify reliable causal paths (>70% accuracy), detect unreliable assumptions (>30% violation rate)
- Causal modelling agent - Generate graph refinement suggestions, validate with ISL, apply approved changes
- Decision accuracy analysis - Compare predicted vs actual outcomes, generate accuracy grades
- Learning insights API - Extract patterns by decision archetype with success factors

#### New Services (31 total)
- `AIOptionGenerator`, `OptionSynthesizer`, `OptionTuner` (Phase C)
- `AssumptionTestingAdvisor`, `DecisionRetrospectiveService`, `SessionReopener` (Phase C)
- `DeliberationService` - Multi-round deliberation with anonymous voting (Phases 1A/1B)
- `PreferenceElicitationService` - ActiVA counterfactual scenarios (Phase 2A)
- `OnboardingService` - Bayesian teaching questions (Phase 2B)
- `AggregationIntelligenceService` - Navajas aggregation with confidence calibration (Phase 3)
- `ConsensusBuilder` - Habermas Machine consensus synthesis
- `PortfolioAnalyzer`, `AdvancedAnalyticsEngine`, `PatternAnalyzer` (Phase D)
- `CollaborationManager`, `CrossTeamCoordinator`, `DecisionDependencyManager` (Phase D)
- `OutcomeTrackingService`, `DecisionPatternLearner`, `CausalModellingAgent` (Phase 5)

#### New API Endpoints (45 additional, 60+ total)
- Phase C: `/sessions/{id}/generate-options`, `/synthesize-options`, `/tune-option`, `/test-recommendations`, `/retrospective`, `/reopen`
- Deliberation: `/deliberation/start`, `/{id}/submit`, `/{id}/vote`, `/{id}/advance`, `/{id}/status`, `/{id}/history`
- Preferences: `/preferences/start`, `/{id}/respond`, `/{id}/model`
- Onboarding: `/onboarding/start`, `/{id}/respond`, `/{id}/profile`
- Aggregation: `/aggregation/analyze`, `/aggregation/synthesize`
- Consensus: `/consensus/consensus-builder`, `/consensus-builder/health`
- Portfolio: `/portfolio/analytics`, `/portfolio/health-score`
- Collaboration: `/collaboration/ws/{id}` (WebSocket), `/{id}/state`, `/{id}/presence`, `/{id}/broadcast`, `/{id}/active-users`
- Dependencies: `/dependencies` (POST), `/{id}` (DELETE), `/{id}/resolve`, `/session/{id}`, `/session/{id}/blocking`, `/session/{id}/dependents`, `/graph`
- Patterns: `/patterns/organization/{id}`
- Analytics: `/advanced-analytics/trends`, `/advanced-analytics/benchmarks`
- Coordination: `/coordination/groups`, `/detect-conflicts`, `/view`, `/conflicts/{id}/resolve`
- Outcomes: `/outcomes/track`, `/outcomes/record`, `/outcomes/{id}/analyze`, `/outcomes/session/{id}`, `/learning/insights`
- Graph Analysis: `/graph-analysis/analyze`, `/graph-analysis/apply-suggestions`
- PLoT Orchestration: `/plot-orchestration/alignment-session` (internal, API key required)

#### New Database Tables (14 additional, 23 total)
- `deliberation_sessions`, `deliberation_rounds`, `deliberation_submissions`, `deliberation_votes`, `deliberation_conflicts` (Phase 1)
- `user_accuracy_history`, `user_domain_expertise` (Phase 3)
- `decision_dependencies`, `pattern_analysis_cache`, `coordination_groups`, `detected_conflicts`, `analytics_cache` (Phase D)
- `decision_outcomes`, `outcome_measurements` (Phase 5)

#### Security & Performance Improvements
- Fixed 4 critical security vulnerabilities (hardcoded secrets, CORS wildcards, WebSocket auth, sensitive logging)
- Fixed N+1 query problem in deliberation (40+ queries → 3 queries, 13x speedup)
- Fixed HTTP client resource leaks (CEE, ISL, FACET clients - added async context managers)
- Added 11 performance indexes for common query patterns
- Rate limiting enhanced with per-user JWT extraction (falls back to IP)
- Disabled database echo logging to prevent sensitive data leakage
- AES-256-GCM encryption for anonymous voting

#### Testing
- Added 35+ tests for Phase 5 (outcome tracking, encryption service)
- Added tests for deliberation service, preference elicitation, onboarding
- Total coverage: 88.8% (164+ tests)

#### Documentation
- **Documentation Consolidation** - Reorganized from 41 files into 3 core documents
  - `README.md` - Streamlined entry point (~100 lines)
  - `GETTING_STARTED.md` - Complete developer onboarding guide (~500 lines)
  - `TECHNICAL_SPECIFICATION.md` - Authoritative technical reference (~1000 lines, all 60+ endpoints)
- Archived historical phase reports and duplicates to `docs/archive/`
- Moved external specs (CEE, ISL) to `docs/external/`
- Comprehensive codebase review report (CODEBASE_REVIEW_2025.md - archived)

### Changed
- Upgraded to version 2.0.0 reflecting major feature additions
- Updated all documentation links to point to new consolidated structure

### Fixed
- Critical security issues (secrets exposure, authentication bypasses)
- Performance bottlenecks (N+1 queries, resource leaks)
- Version numbering inconsistencies across documentation

---

## [1.0.0] - 2025-01-15

### Added

#### Phase A: Structured Deliberation
- Session management with stakeholder roles (owner, facilitator, stakeholder, observer)
- Structured perspective collection via CEE integration
- Goal profile extraction across 8 dimensions
- Heuristic fallback when CEE unavailable
- Shared ground identification (common goals and concerns)
- Disagreement mapping (tension detection between conflicting priorities)
- Option fit calculation with multi-stakeholder scoring
- Constraint violation detection
- Decision type templates (Pricing, Features, GTM, Resources, Custom)
- Baseline "Status Quo" option support

#### Phase B: Causal Validation
- ISL integration for parallel option validation
- Outcome range predictions (p10, p50, p90)
- Evidence-based minority protection
- Sensitivity analysis for contested assumptions
- Stable assumption_id wiring for traceability
- Assumption strength assessment (evidence level + impact)
- Complete decision documentation
- Decision audit trail generation
- Scenario model integration support
- Graceful degradation when ISL unavailable

#### Architecture & Infrastructure
- FastAPI application with async/await
- Pydantic v2 for data validation
- PostgreSQL database models (SQLAlchemy)
- Alembic migrations for schema management
- Redis caching layer
- Error.v1 standard for all errors
- Request ID middleware for distributed tracing
- Rate limiting (100 requests/minute)
- CORS support
- Prometheus metrics for monitoring
- Structured JSON logging
- Docker and Docker Compose configuration
- Health check endpoint

#### Services
- `SessionManager` - Session lifecycle management
- `ProfileExtractor` - CEE-powered profile extraction
- `DisagreementAnalyzer` - Tension mapping and common ground
- `FitCalculator` - Multi-stakeholder fit scoring
- `ValidationOrchestrator` - ISL integration for causal validation
- `ConcernValidator` - Minority concern validation
- `DecisionDocumenter` - Complete decision documentation

#### API Endpoints
- `POST /api/v1/alignment/sessions` - Create alignment session
- `GET /api/v1/alignment/sessions/{id}` - Get session status
- `PATCH /api/v1/alignment/sessions/{id}/status` - Update session status
- `POST /api/v1/alignment/sessions/{id}/perspectives` - Submit stakeholder perspective
- `GET /api/v1/alignment/sessions/{id}/perspectives/{id}` - Get profile
- `POST /api/v1/alignment/sessions/{id}/analyze` - Generate analysis
- `POST /api/v1/alignment/sessions/{id}/options` - Propose option
- `GET /api/v1/alignment/sessions/{id}/options/{id}` - Get option with validation
- `POST /api/v1/alignment/sessions/{id}/options/{id}/concerns` - Flag concern
- `GET /api/v1/alignment/sessions/{id}/concerns/{id}` - Get concern validation
- `POST /api/v1/alignment/sessions/{id}/decide` - Record decision
- `GET /api/v1/alignment/sessions/{id}/brief` - Export decision brief
- `POST /api/v1/alignment/sessions/{id}/brief/rate` - Rate decision quality
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

#### Testing
- Comprehensive unit tests for all services
- Integration tests for API endpoints
- End-to-end tests for full alignment flow
- Mock CEE and ISL clients for testing
- Test fixtures and utilities
- Pytest configuration with async support
- Coverage reporting configured

#### Documentation
- Complete API documentation with examples
- Deployment guide with Docker and Kubernetes
- Contributing guidelines
- Development setup instructions
- Troubleshooting guide
- Changelog

#### Development Tools
- Development helper scripts
- Database migration tools
- Code formatting (Black)
- Linting (Ruff)
- Type checking (MyPy)
- Pre-commit configuration

### Technical Details

#### Dependencies
- Python 3.11+
- FastAPI 0.109+
- Pydantic v2.5+
- SQLAlchemy 2.0+
- PostgreSQL 14+
- Redis 7+
- Alembic 1.13+
- Prometheus Client 0.19+

#### Performance Targets
- Health check: <10ms
- Session creation: <200ms
- Profile extraction: <2s (CEE dependent)
- Fit calculation: <100ms
- ISL validation: <30s (ISL dependent)
- Sensitivity analysis: <10s (ISL dependent)

#### Security Features
- Input validation on all endpoints
- Rate limiting (100 req/min per IP)
- JWT authentication support
- CORS configuration
- Audit logging for all state changes
- No PII in logs

#### Quality Standards
- Error.v1 standard for all errors
- Structured JSON logging
- Type hints throughout
- Comprehensive docstrings
- 80%+ test coverage target
- Deterministic operations with seeds
- Graceful degradation patterns

## [1.1.0] - 2025-01-15

### Added - Phase C: Intelligent Assistance & Learning

#### C1: AI Option Generation
- AI-powered option generation service with CEE integration
- Two generation modes: creative_synthesis and constraint_satisfaction
- Generates 2-3 options that bridge stakeholder disagreements
- Full AIGenerationMetadata tracking for transparency
- POST /api/v1/alignment/sessions/{id}/generate-options endpoint

#### C2: Option Synthesis
- Option Synthesizer service for creating hybrid options
- Combines elements from multiple source options
- Compatibility scoring between options
- SynthesisMetadata tracking which elements preserved/sacrificed
- POST /api/v1/alignment/sessions/{id}/synthesize-options endpoint

#### C3: Option Tuning
- Option Tuner service for addressing minority concerns
- Adjusts options while preserving core elements
- Tuning feasibility assessment
- TuningMetadata tracking parameter adjustments
- POST /api/v1/alignment/sessions/{id}/tune-option endpoint

#### C4: Assumption Testing Recommendations
- Assumption Testing Advisor service
- Prioritizes assumptions by criticality (impact + evidence)
- Recommends validation methods (A/B test, technical spike, user research)
- Timeline and budget estimation for testing
- POST /api/v1/alignment/sessions/{id}/test-recommendations endpoint

#### C5: Decision Learning Loop
- Decision Retrospective service with outcome tracking
- Compares actual vs predicted outcomes
- Analyzes which assumptions held vs failed
- Generates lessons learned via CEE
- Organizational recommendations from multiple retrospectives
- POST /api/v1/alignment/sessions/{id}/retrospective endpoint
- GET /api/v1/alignment/teams/{team_id}/recommendations endpoint

#### C6: Multi-Round Deliberation
- Session Reopener service for when assumptions fail
- Session chaining with parent_session_id and chain_depth
- Reopen assessment based on outcome accuracy
- SessionChainLink tracking for decision evolution
- POST /api/v1/alignment/sessions/{id}/reopen endpoint

#### Schema Updates
- Added parent_session_id, reopened_from_id, chain_depth to sessions table
- Added ai_generation_metadata, synthesis_metadata, tuning_metadata to options table
- New assumption_validations table for pre-decision testing
- New decision_retrospectives table for learning loop
- Alembic migration 002 for Phase C schema

#### Services
- AIOptionGenerator - AI-powered option creation
- OptionSynthesizer - Hybrid option creation
- OptionTuner - Minority concern resolution
- AssumptionTestingAdvisor - Validation strategy recommendations
- DecisionRetrospectiveService - Learning from outcomes
- SessionReopener - Multi-round deliberation support

#### CEE Integration Enhancements
- generate_options - AI option generation
- synthesize_options - Option combination
- tune_option - Option adjustment
- recommend_test_strategy - Testing recommendations
- generate_lessons_learned - Retrospective insights
- generate_org_recommendations - Cross-decision patterns

#### Metrics
- ai_options_generated_total counter
- options_synthesized_total counter
- options_tuned_total counter
- retrospectives_created_total counter
- sessions_reopened_total counter

#### Testing
- Comprehensive unit tests for all 6 Phase C services
- Updated MockCEEClient with Phase C methods
- Test coverage for AI generation, synthesis, tuning, retrospectives

---

## [Unreleased]

### Planned Features
- GraphQL API support
- Real-time collaboration (WebSockets)
- Advanced analytics dashboard
- Email notifications
- Slack integration
- Export to PDF
- Version history for decisions
- Template library
- Team comparison analytics

---

## Release Notes

### v1.0.0 - Production Ready

This is the first production-ready release of the Team Alignment Engine. It includes:

✅ **Phase A (Structured Deliberation)** - Fully implemented and tested
✅ **Phase B (Causal Validation)** - Fully implemented with ISL integration
✅ **Comprehensive Testing** - Unit, integration, and E2E tests
✅ **Production Deployment** - Docker, monitoring, logging
✅ **Complete Documentation** - API docs, deployment guide, contributing guide

**Ready for pilot deployment** with real teams in both quick mode (Phase A only) and evidence-backed mode (Phase A + B).

### Migration Guide

This is the initial release, no migration needed.

### Breaking Changes

None (initial release).

### Known Issues

None at release time.

### Deprecations

None at release time.
