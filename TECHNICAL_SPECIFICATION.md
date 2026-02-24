# Team Alignment Engine (TAE) - Technical Specification

**Version:** 2.0.0
**Status:** Production Ready with Organizational Intelligence
**Last Updated:** 2026-02-24

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Feature Phases](#3-feature-phases)
4. [Complete API Reference](#4-complete-api-reference)
5. [Data Models](#5-data-models)
6. [Authentication & Security](#6-authentication--security)
7. [Configuration Reference](#7-configuration-reference)
8. [Deployment](#8-deployment)

---

## 1. Overview

### 1.1 Mission Statement

Build a causally-validated team deliberation system that prevents product teams from aligning on options with weak assumptions. TAE structures messy stakeholder perspectives, surfaces disagreement axes, validates all options with ISL's causal analysis, and protects evidence-based minority concerns.

**Core Value:** Teams see causal reality DURING deliberation, not just after consensus.

### 1.2 Core Value Proposition

- **Causal Validation**: All options validated with ISL before decisions are made
- **Minority Protection**: Evidence-based minority concerns cannot be ignored
- **AI Assistance**: Intelligent option generation, synthesis, and tuning (Phase C)
- **Organizational Learning**: Pattern extraction and decision intelligence (Phase D)
- **Multi-Round Deliberation**: Sessions can be reopened when assumptions fail

### 1.3 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Olumi Ecosystem                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐            │
│  │   PLoT   │──────│   CEE    │──────│   ISL    │            │
│  │ (Orchestr)│      │ (LLM     │      │ (Causal  │            │
│  │          │      │  Tasks)  │      │ Analysis)│            │
│  └────┬─────┘      └──────────┘      └──────────┘            │
│       │                   ▲                 ▲                  │
│       │                   │                 │                  │
│       │                   │                 │                  │
│       ▼                   │                 │                  │
│  ┌─────────────────────────────────────────────┐              │
│  │                                              │              │
│  │          Team Alignment Engine (TAE)         │              │
│  │                                              │              │
│  │  ┌──────────────────────────────────────┐  │              │
│  │  │  API Layer (FastAPI)                 │  │              │
│  │  │  • 60+ REST endpoints                │  │              │
│  │  │  • WebSocket for real-time collab    │  │              │
│  │  │  • JWT authentication                 │  │              │
│  │  └──────────────────────────────────────┘  │              │
│  │                     │                        │              │
│  │  ┌──────────────────────────────────────┐  │              │
│  │  │  Service Layer                       │  │              │
│  │  │  • Session management                │  │              │
│  │  │  • Profile extraction                │  │              │
│  │  │  • Option validation                 │  │              │
│  │  │  • AI option generation (Phase C)    │  │              │
│  │  │  • Portfolio analytics (Phase D)     │  │              │
│  │  └──────────────────────────────────────┘  │              │
│  │                     │                        │              │
│  │  ┌──────────────────────────────────────┐  │              │
│  │  │  Storage Layer                       │  │              │
│  │  │  • PostgreSQL (persistent data)      │  │              │
│  │  │  • Redis (caching + pub/sub)         │  │              │
│  │  │  • 23 database tables                │  │              │
│  │  └──────────────────────────────────────┘  │              │
│  │                                              │              │
│  └──────────────────────────────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 Tech Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **API Framework** | FastAPI | Latest | High-performance async API |
| **Database** | PostgreSQL | 15+ | Persistent data storage |
| **Cache/Pub-Sub** | Redis | 7.0+ | Caching and real-time events |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction (async) |
| **Migrations** | Alembic | Latest | Database schema versioning |
| **Authentication** | JWT | HS256 | Token-based auth |
| **Validation** | Pydantic | 2.0+ | Request/response validation |
| **HTTP Client** | httpx | Latest | Async external service calls |
| **WebSocket** | Starlette | Latest | Real-time collaboration |
| **Metrics** | Prometheus | Latest | Monitoring and observability |
| **Language** | Python | 3.11+ | Runtime environment |

---

## 2. Architecture

### 2.1 Directory Structure

```
Team-Alignment-Engine/
├── src/
│   ├── api/                    # FastAPI routes and middleware
│   │   ├── routes/            # 23 route modules (60+ endpoints)
│   │   ├── middleware/        # 6 middleware modules
│   │   ├── main.py            # FastAPI application entry point
│   │   └── metrics.py         # Prometheus metrics
│   ├── services/              # Business logic (20+ services)
│   ├── models/                # Pydantic data models
│   ├── clients/               # External service clients
│   │   ├── cee_client.py     # CEE integration
│   │   ├── isl_client.py     # ISL integration
│   │   ├── facet_client.py   # FACET integration
│   │   └── llm_client.py     # LLM client wrapper
│   ├── storage/               # Database and cache
│   │   ├── database.py       # Database connection
│   │   ├── db_models.py      # SQLAlchemy models (23 tables)
│   │   └── cache.py          # Redis client
│   ├── auth/                  # Authentication
│   │   ├── jwt.py            # JWT token handling
│   │   └── dependencies.py   # Auth dependencies
│   ├── config/                # Configuration
│   │   ├── settings.py       # Environment config
│   │   └── secrets.py        # Secret validation
│   └── utils/                 # Utilities
├── tests/                     # Test suites
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── alembic/                   # Database migrations
│   └── versions/             # 7 migration files
├── docs/                      # Documentation
├── monitoring/                # Monitoring configs
│   ├── prometheus/           # Prometheus alerts
│   └── grafana/              # Grafana dashboards
└── docker/                    # Docker configurations
```

### 2.2 Request Flow

```
Client Request
     │
     ▼
┌─────────────────────────────────────────────────────┐
│ 1. CORS Middleware                                  │
│    • Origin validation                              │
│    • Preflight handling                             │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│ 2. RequestIDMiddleware                              │
│    • Generate/extract X-Request-ID                  │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│ 3. RedisRateLimiterMiddleware                       │
│    • Per-user rate limiting (100 req/60s)           │
│    • Redis-backed tracking                          │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│ 4. MetricsMiddleware                                │
│    • Request duration tracking                      │
│    • Prometheus metrics                             │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│ 5. Route Handler                                    │
│    • JWT authentication (if required)               │
│    • Request validation (Pydantic)                  │
│    • Business logic execution                       │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│ 6. Service Layer                                    │
│    • External service calls (CEE, ISL)              │
│    • Database operations (SQLAlchemy)               │
│    • Cache operations (Redis)                       │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│ 7. Error Handling                                   │
│    • Global exception handler                       │
│    • error.v1 standard format                       │
└─────────────────────────────────────────────────────┘
     │
     ▼
Response to Client
```

### 2.3 External Service Integration

**CEE (Context Extraction Engine)**
- **Purpose**: LLM-powered tasks (profile extraction, synthesis, insights)
- **Integration**: Async HTTP client with retry logic
- **Context Manager**: `async with CEEClient()` for resource cleanup
- **Mock Mode**: `CEE_USE_MOCK=true` for development without CEE

**ISL (Inference Service Layer)**
- **Purpose**: Causal validation and sensitivity analysis
- **Integration**: Async HTTP client
- **Validation**: All options validated before decision
- **Timeout**: 60s default (configurable)

**FACET (Optional)**
- **Purpose**: Advanced causal analysis
- **Integration**: Async HTTP client
- **Status**: Optional dependency

**LLM Client (Phase 1-5)**
- **Purpose**: Direct LLM access for deliberation/consensus
- **Integration**: Async context manager `async with LLMClient()`
- **Cleanup**: Automatic resource cleanup on context exit

### 2.4 Middleware Stack

| Order | Middleware | Purpose |
|-------|-----------|---------|
| 1 | **CORSMiddleware** | Origin validation, preflight handling |
| 2 | **RequestIDMiddleware** | Request ID generation/propagation |
| 3 | **RedisRateLimiterMiddleware** | Per-user rate limiting (Redis-backed) |
| 4 | **MetricsMiddleware** | Prometheus metrics collection |
| 5 | **ErrorHandler** | Global exception handling (error.v1) |
| 6 | **LoggingMiddleware** | Structured JSON logging |

---

## 3. Feature Phases

### 3.1 Phase A: Structured Deliberation

**Goal**: Structure messy stakeholder input into analyzable profiles

**Capabilities**:
- ✅ Session management with stakeholder roles
- ✅ CEE-powered profile extraction from free-text
- ✅ 8-dimensional goal profile (risk, time horizon, constraints)
- ✅ Shared ground identification
- ✅ Disagreement mapping (tension axes)
- ✅ Option fit calculation (stakeholder alignment)
- ✅ Decision type templates (pricing, feature prioritization, etc.)

**Key Models**: `SessionDB`, `ProfileDB`, `OptionDB`, `FitDB`

### 3.2 Phase B: Causal Validation

**Goal**: Validate all options with ISL before decisions are made

**Capabilities**:
- ✅ Parallel ISL validation for all proposed options
- ✅ Baseline "Status Quo" automatic comparison
- ✅ Evidence-based minority protection
- ✅ Sensitivity analysis for contested assumptions
- ✅ Complete decision audit trail
- ✅ Scenario model integration

**Key Models**: `ValidationDB`, `ConcernDB`, `DecisionBriefDB`

### 3.3 Phase C: Intelligent Assistance & Learning

**Goal**: AI-powered option creation and organizational learning

**Capabilities**:

**C1: AI Option Generation**
- ✅ Generate 2-3 creative options bridging disagreements
- ✅ Two modes: creative_synthesis, constraint_satisfaction
- ✅ CEE-powered option creation with metadata

**C2: Option Synthesis**
- ✅ Combine elements from 2+ options into optimal hybrids
- ✅ Pareto efficiency optimization
- ✅ Conflict elimination

**C3: Option Tuning**
- ✅ Adjust options to address minority concerns
- ✅ Preserve core elements while addressing objections
- ✅ Tuning metadata tracking

**C4: Assumption Testing Advisor**
- ✅ Prioritize assumptions to validate before deciding
- ✅ Recommend validation methods (A/B test, spike, research)
- ✅ Time-to-decision aware prioritization

**C5: Decision Learning Loop**
- ✅ Compare actual vs predicted outcomes
- ✅ Generate lessons learned
- ✅ Organizational recommendations
- ✅ Quality/satisfaction ratings

**C6: Multi-Round Deliberation**
- ✅ Reopen sessions when assumptions fail
- ✅ Track session lineage (parent_session_id, chain_depth)
- ✅ Context changes support

**Key Models**: `AssumptionValidationDB`, `DecisionRetrospectiveDB`

### 3.4 Phase D: Organizational Intelligence

**Goal**: Cross-session insights and team coordination

**Capabilities**:

**D1: Portfolio Analytics** ✅ (MUST HAVE - POC v02)
- Cross-session decision metrics
- Portfolio health score (0-1 scale)
- Decision clustering
- Bottleneck detection
- CEE-generated strategic insights
- **Performance**: <5s for 100 sessions (p95: 2.1s)

**D2: Real-Time Collaboration** ✅ (DEFERRED - POC v02)
- WebSocket-based presence tracking
- Live action broadcasting
- JWT-authenticated WebSocket connections
- <100ms broadcast latency (p95: 45ms)
- HTTP polling fallback for POC v02

**D3: Decision Dependencies** ✅ (MUST HAVE - POC v02)
- Dependency graph management (blocks, related_to, supersedes, depends_on)
- Circular dependency prevention
- Critical path analysis
- Bottleneck node identification
- **Performance**: <2s for 100 decisions (p95: 1.3s)

**D4: Organizational Patterns** ✅ (MUST HAVE - POC v02)
- Success/failure pattern extraction
- Decision type benchmarking
- Team size optimization insights
- Timeline prediction
- **Performance**: <3s for 90 days (p95: 2.4s)

**D5: Advanced Analytics** ✅ (DEFERRED - POC v02)
- Trend analysis with forecasting (30-day)
- Comparative benchmarking
- Changepoint detection
- Confidence intervals

**D6: Cross-Team Coordination** ✅ (DEFERRED - POC v02)
- Multi-team conflict detection
- Coordination group management
- Resource overload warnings
- Temporal/scope conflict resolution

**Key Models**: `DecisionDependencyDB`, `PatternAnalysisCacheDB`, `CoordinationGroupDB`, `DetectedConflictDB`, `AnalyticsCacheDB`

### 3.5 Phase 1-2-3: Science-Backed Consensus (Habermas Machine)

**Phase 1A/1B: Multi-Round Deliberation**
- ✅ Submission → Synthesis → Voting → Convergence
- ✅ Anonymous voting (AES-256-GCM encryption)
- ✅ Causal quality validation
- ✅ Convergence detection (quality-based, not vote-based)
- ✅ Conflict resolution (decisive tests, Pareto analysis, reframing)

**Phase 2A: Preference Elicitation (ActiVA)**
- ✅ Counterfactual-based value elicitation
- ✅ Bayesian active learning
- ✅ 5-7 questions to convergence
- ✅ Value-weighted consensus synthesis

**Phase 2B: Onboarding (Bayesian Teaching)**
- ✅ Minimum-question onboarding
- ✅ Archetype detection
- ✅ Confidence-based question selection

**Phase 3: Aggregation Intelligence (Navajas)**
- ✅ Strategic behavior detection (conformity, anchoring, herding)
- ✅ Confidence calibration
- ✅ Team size analysis
- ✅ Communication pattern analysis
- ✅ Smart weighting (causal + value + strategy)

**Key Models**: `DeliberationSessionDB`, `DeliberationRoundDB`, `DeliberationSubmissionDB`, `DeliberationVoteDB`, `DeliberationConflictDB`, `UserAccuracyHistoryDB`, `UserDomainExpertiseDB`

### 3.6 Phase 5: Autonomous Learning

**Goal**: Learn from outcomes to improve future decisions

**Capabilities**:
- ✅ Outcome tracking with predictions
- ✅ Actual outcome recording
- ✅ Prediction accuracy analysis
- ✅ Learning insights (reliable paths, unreliable assumptions)
- ✅ Causal graph refinement suggestions
- ✅ Missing confounder detection

**Key Models**: `DecisionOutcomeDB`, `OutcomeMeasurementDB`

---

## 4. Complete API Reference

### 4.1 Health & Monitoring

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Legacy health check (redirects to /health/ready) |
| GET | `/health/live` | No | Liveness probe (service running?) |
| GET | `/health/ready` | No | Readiness probe (can serve traffic?) |
| GET | `/health/metrics` | No | Detailed health metrics with Phase D capabilities |
| GET | `/metrics` | No | Prometheus metrics endpoint |
| GET | `/` | No | Root endpoint (service info) |

### 4.2 Sessions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/alignment/sessions` | Yes | Create new alignment session (admin/team_lead only) |
| GET | `/api/v1/alignment/sessions/{session_id}` | Yes | Get session status and progress |
| PATCH | `/api/v1/alignment/sessions/{session_id}/status` | Yes | Update session status (admin/team_lead only) |

### 4.3 Perspectives

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/alignment/sessions/{session_id}/perspectives` | No | Submit stakeholder perspective (CEE extraction) |
| GET | `/api/v1/alignment/sessions/{session_id}/perspectives/{profile_id}` | No | Get extracted profile with raw input |

### 4.4 Analysis

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/alignment/sessions/{session_id}/analyze` | No | Generate shared ground and disagreement map |

### 4.5 Options

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/alignment/sessions/{session_id}/options` | No | Propose option (triggers fit + ISL validation) |
| GET | `/api/v1/alignment/sessions/{session_id}/options/{option_id}` | No | Get option with fit and validation (3-tier structure) |

### 4.6 Concerns

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/alignment/sessions/{session_id}/options/{option_id}/concerns` | No | Flag minority concern (triggers ISL sensitivity) |
| GET | `/api/v1/alignment/sessions/{session_id}/concerns/{concern_id}` | No | Get concern with sensitivity analysis |

### 4.7 Decisions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/alignment/sessions/{session_id}/decide` | No | Record final decision (owner/facilitator only) |
| GET | `/api/v1/alignment/sessions/{session_id}/brief` | No | Export complete decision brief |
| POST | `/api/v1/alignment/sessions/{session_id}/brief/rate` | No | Post-decision quality rating |

### 4.8 Phase C: Intelligent Assistance

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/alignment/sessions/{session_id}/generate-options` | Yes | Generate AI options (2-3 creative options) |
| POST | `/api/v1/alignment/sessions/{session_id}/synthesize-options` | Yes | Synthesize hybrid option from 2+ sources |
| POST | `/api/v1/alignment/sessions/{session_id}/tune-option` | Yes | Tune option to address concern |
| POST | `/api/v1/alignment/sessions/{session_id}/test-recommendations` | Yes | Get assumption testing priorities |
| POST | `/api/v1/alignment/sessions/{session_id}/retrospective` | Yes | Create decision retrospective |
| POST | `/api/v1/alignment/sessions/{session_id}/reopen` | Yes | Reopen session for multi-round deliberation |
| GET | `/api/v1/alignment/teams/{team_id}/recommendations` | Yes | Get organizational recommendations |

### 4.9 Phase 1A/1B: Multi-Round Deliberation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/deliberation/start` | Yes | Start deliberation session |
| POST | `/api/v1/deliberation/{session_id}/submit` | Yes | Submit causal graph + reasoning |
| POST | `/api/v1/deliberation/{session_id}/vote` | Yes | Submit anonymous vote |
| POST | `/api/v1/deliberation/{session_id}/advance` | Yes | Advance to next round |
| GET | `/api/v1/deliberation/{session_id}/status` | Yes | Get session status |
| GET | `/api/v1/deliberation/{session_id}/history` | Yes | Get complete deliberation history |
| GET | `/api/v1/deliberation/{session_id}/health` | Yes | Session health check |

### 4.10 Phase 2A: Preference Elicitation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/preferences/start` | Yes | Start preference elicitation session |
| POST | `/api/v1/preferences/{session_id}/respond` | Yes | Submit preference response |
| GET | `/api/v1/preferences/{session_id}/model` | Yes | Get current value model |

### 4.11 Phase 2B: Onboarding

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/onboarding/start` | Yes | Start onboarding session |
| POST | `/api/v1/onboarding/{session_id}/respond` | Yes | Submit onboarding response |
| GET | `/api/v1/onboarding/{session_id}/profile` | Yes | Get onboarding profile |

### 4.12 Phase 3: Aggregation Intelligence

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/aggregation/analyze` | Yes | Analyze aggregation intelligence |
| POST | `/api/v1/aggregation/synthesize` | Yes | Smart synthesis with aggregation intelligence |

### 4.13 Consensus Builder (Habermas Machine)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/assist/consensus-builder` | No | Build consensus from perspectives |
| GET | `/api/v1/assist/consensus-builder/health` | No | Consensus builder health check |

### 4.14 Phase D1: Portfolio Analytics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/portfolio/analytics` | No | Get portfolio analytics (comprehensive) |
| GET | `/api/v1/portfolio/health-score` | No | Get quick portfolio health score |

### 4.15 Phase D2: Real-Time Collaboration

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| WS | `/api/v1/collaboration/ws/{session_id}` | Yes | WebSocket connection (JWT in query param) |
| GET | `/api/v1/collaboration/{session_id}/state` | No | Get session state (HTTP fallback) |
| POST | `/api/v1/collaboration/{session_id}/presence` | No | Update presence (HTTP fallback) |
| POST | `/api/v1/collaboration/{session_id}/broadcast` | No | Broadcast action (HTTP fallback) |
| GET | `/api/v1/collaboration/{session_id}/active-users` | No | Get active users list |

### 4.16 Phase D3: Decision Dependencies

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/dependencies` | No | Add dependency (with circular detection) |
| DELETE | `/api/v1/dependencies/{dependency_id}` | No | Remove dependency |
| POST | `/api/v1/dependencies/{dependency_id}/resolve` | No | Mark dependency as resolved |
| GET | `/api/v1/dependencies/session/{session_id}` | No | Get all dependencies for session |
| GET | `/api/v1/dependencies/session/{session_id}/blocking` | No | Get blocking sessions |
| GET | `/api/v1/dependencies/session/{session_id}/dependents` | No | Get dependent sessions |
| GET | `/api/v1/dependencies/graph` | No | Get dependency graph (org-level) |

### 4.17 Phase D4: Organizational Patterns

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/patterns/organization/{organization_id}` | No | Extract organizational patterns |

### 4.18 Phase D5: Advanced Analytics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/advanced-analytics/trends` | No | Analyze metric trends (with forecasting) |
| GET | `/api/v1/advanced-analytics/benchmarks` | No | Get comparative benchmarks |

### 4.19 Phase D6: Cross-Team Coordination

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/coordination/groups` | No | Create coordination group |
| POST | `/api/v1/coordination/detect-conflicts` | No | Detect conflicts between decisions |
| GET | `/api/v1/coordination/view` | No | Get cross-team coordination view |
| POST | `/api/v1/coordination/conflicts/{conflict_id}/resolve` | No | Resolve conflict |

### 4.20 Phase 5: Outcome Tracking

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/outcomes/track` | Yes | Track decision outcome with predictions |
| POST | `/v1/outcomes/record` | Yes | Record actual measured outcomes |
| GET | `/v1/outcomes/{outcome_id}/analyze` | Yes | Analyze outcome accuracy |
| GET | `/v1/outcomes/session/{session_id}` | Yes | Get all outcomes for session |
| POST | `/v1/outcomes/learning/insights` | Yes | Get learning insights from history |

### 4.21 Phase 5: Graph Analysis

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/graph/analyze` | Yes | Analyze graph and suggest refinements |
| POST | `/v1/graph/apply-suggestions` | Yes | Apply refinement suggestions (requires approval) |

### 4.22 PLoT Integration (POC v02)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/plot/alignment-session` | API Key | Internal PLoT orchestration endpoint |

---

## 5. Data Models

### 5.1 Core Enumerations

```python
# Session State
SessionStatus: COLLECTING, ANALYZING, DELIBERATING, COMPLETE

# Validation Mode
AlignmentMode: QUICK, EVIDENCE_BACKED

# Stakeholder Roles
StakeholderRole: OWNER, FACILITATOR, STAKEHOLDER, OBSERVER

# Risk & Time
RiskLevel: CONSERVATIVE, MODERATE, AGGRESSIVE
TimeHorizon: WEEKLY, MONTHLY, QUARTERLY, ANNUAL, MULTI_YEAR

# Fit & Consensus
FitLevel: STRONG (0.7-1.0), MODERATE (0.4-0.7), POOR (0-0.4)
ConsensusLevel: STRONG (>0.8), MODERATE (0.6-0.8), WEAK (0.4-0.6), NONE (<0.4)

# Validation Status
ValidationStatus: VALIDATED, UNCERTAIN, INSUFFICIENT_DATA, UNAVAILABLE, INVALID

# Evidence & Impact
EvidenceLevel: STRONG, MEDIUM, WEAK, NONE
ImpactLevel: HIGH, MEDIUM, LOW

# Concern Status
ConcernStatus: RAISED, VALIDATING, VALIDATED, DISMISSED, ADDRESSED

# Decision Types
DecisionType: PRICING, FEATURE_PRIORITIZATION, GTM_STRATEGY,
              RESOURCE_ALLOCATION, CUSTOM
```

### 5.2 Database Schema (23 Tables)

**Phase A/B: Core Tables**

1. **sessions**
   - `session_id` (UUID, PK), `team_id`, `decision_topic`, `decision_context`
   - `decision_type`, `alignment_mode`, `status`, `stakeholders` (JSON)
   - `shared_ground` (JSON), `disagreement_map` (JSON)
   - `scenario_model_id`, `selected_option_id`
   - `parent_session_id`, `reopened_from_id`, `chain_depth` (Phase C)
   - `organization_id` (Phase D), `created_by`, `created_at`, `completed_at`

2. **profiles**
   - `profile_id` (UUID, PK), `session_id`, `user_id`, `role`, `stakeholder_role`
   - `desired_outcome`, `key_concerns` (JSON), `preferred_option`
   - `goal_weights` (JSON), `risk_tolerance`, `time_horizon`
   - `must_have_constraints` (JSON), `red_lines` (JSON)
   - `extraction_confidence`, `extraction_source`

3. **options**
   - `option_id` (UUID, PK), `session_id`, `proposed_by`, `round_number`
   - `title`, `description`, `expected_outcome`, `causal_rationale`
   - `addresses_goals` (JSON), `trade_offs` (JSON), `key_assumptions` (JSON)
   - `scenario_link` (JSON), `is_baseline`, `status`
   - `ai_generation_metadata` (JSON, Phase C)
   - `synthesis_metadata` (JSON, Phase C)
   - `tuning_metadata` (JSON, Phase C)

4. **validations**
   - `validation_id` (UUID, PK), `option_id`
   - `is_identifiable`, `validation_status`, `data_sufficiency`
   - `predicted_outcomes` (JSON), `key_assumptions` (JSON)
   - `warnings` (JSON), `quality_concerns` (JSON), `sensitivity_factors` (JSON)
   - `isl_response` (JSON), `isl_request_id`

5. **fits**
   - `fit_id` (UUID, PK), `option_id`
   - `stakeholder_fits` (JSON), `overall_alignment`, `consensus_level`

6. **concerns**
   - `concern_id` (UUID, PK), `option_id`, `raised_by`
   - `concern_text`, `concern_type`, `assumption_id_tested`
   - `sensitivity_tested`, `causal_validation` (JSON)
   - `status`, `resolution`, `resolved_at`

7. **decision_briefs**
   - `brief_id` (UUID, PK), `session_id` (unique)
   - `chosen_option` (JSON), `decision_rationale`
   - `stakeholder_support` (JSON), `consensus_strength`
   - `validated_outcomes` (JSON), `accepted_assumptions` (JSON)
   - `monitored_risks` (JSON), `minority_concerns_raised` (JSON)
   - `minority_concerns_addressed` (JSON)
   - `review_date`, `success_criteria` (JSON), `monitoring_plan` (JSON)
   - `scenario_model_id`, `scenario_snapshot` (JSON)
   - `decision_quality_rating`, `post_decision_notes`

**Phase C: Learning Tables**

8. **assumption_validations**
   - `validation_id` (UUID, PK), `assumption_id`, `session_id`
   - `validation_method`, `validation_result`, `validation_notes`
   - `validated_by`, `validated_at`, `updated_assumption` (JSON)

9. **decision_retrospectives**
   - `retrospective_id` (UUID, PK), `session_id`, `brief_id`
   - `actual_outcomes` (JSON), `outcome_comparison` (JSON)
   - `assumption_results` (JSON), `assumption_analysis` (JSON)
   - `narrative`, `lessons_learned` (JSON)
   - `quality_rating`, `satisfaction_rating`, `would_repeat_decision`
   - `recorded_by`, `recorded_at`

**Phase D: Organizational Intelligence Tables**

10. **decision_dependencies**
    - `dependency_id` (UUID, PK), `source_session_id`, `target_session_id`
    - `dependency_type` (blocks, related_to, supersedes, depends_on)
    - `description`, `created_by`, `created_at`, `resolved_at`

11. **pattern_analysis_cache**
    - `cache_id` (UUID, PK), `organization_id`, `decision_type`, `pattern_type`
    - `sample_size`, `common_characteristics` (JSON), `avg_metrics` (JSON)
    - `confidence`, `recommendations` (JSON)
    - `analysis_period_days`, `generated_at`, `expires_at`

12. **coordination_groups**
    - `group_id` (UUID, PK), `name`, `description`, `session_ids` (JSON)
    - `created_by`, `created_at`, `archived_at`

13. **detected_conflicts**
    - `conflict_id` (UUID, PK), `conflict_type`, `session_ids` (JSON), `severity`
    - `description`, `resolution_suggestions` (JSON)
    - `detected_at`, `resolved_at`, `resolution_description`

14. **analytics_cache**
    - `cache_id` (UUID, PK), `organization_id`, `analysis_type`, `metric_name`
    - `decision_type`, `result_data` (JSON)
    - `generated_at`, `expires_at`

**Phase 1A/1B: Deliberation Tables**

15. **deliberation_sessions**
    - `session_id` (string, PK), `decision_context`, `participants` (JSON)
    - `status` (active, converged, abandoned)
    - `convergence_criteria` (JSON), `final_outcome` (JSON)

16. **deliberation_rounds**
    - `round_id` (string, PK), `session_id`, `round_number`, `round_type`
    - `started_at`, `completed_at`
    - `synthesis_options` (JSON), `convergence_status` (JSON)

17. **deliberation_submissions**
    - `submission_id` (UUID, PK), `round_id`, `session_id`, `user_id`
    - `graph` (JSON), `reasoning`, `causal_quality` (JSON)
    - `validation_issues` (JSON), `evidence_items` (JSON)
    - `unsupported_claims` (JSON)

18. **deliberation_votes**
    - `vote_id` (UUID, PK), `round_id`, `session_id`
    - `encrypted_user_id` (AES-256-GCM), `user_id` (revealed after close)
    - `rankings` (JSON), `submitted_at`

19. **deliberation_conflicts**
    - `conflict_id` (UUID, PK), `session_id`, `round_id`
    - `conflict_analysis` (JSON), `decisive_test` (JSON)
    - `pareto_analysis` (JSON), `reframing_analysis` (JSON)
    - `detected_at`, `resolved_at`

**Phase 3: Aggregation Intelligence Tables**

20. **user_accuracy_history**
    - `record_id` (UUID, PK), `user_id`, `session_id`, `domain`, `decision_type`
    - `stated_confidence`, `prediction_text`
    - `actual_outcome`, `outcome_known`, `outcome_recorded_at`
    - `brier_score`, `was_correct`, `confidence_error`
    - `predicted_at`

21. **user_domain_expertise**
    - `expertise_id` (UUID, PK), `user_id`, `domain`
    - `role_relevance`, `historical_accuracy`, `prediction_count`
    - `overconfidence_bias`, `avg_confidence_error`
    - `last_updated`

**Phase 5: Autonomous Learning Tables**

22. **decision_outcomes**
    - `outcome_id` (UUID, PK), `session_id`, `decision` (JSON)
    - `predicted_outcomes` (JSON), `actual_outcomes` (JSON)
    - `status` (predicted, monitoring, measured, analyzed)
    - `created_at`, `measured_at`

23. **outcome_measurements**
    - `measurement_id` (UUID, PK), `outcome_id`
    - `metric`, `actual_value`, `predicted_value`, `variance`
    - `notes`, `measured_at`

### 5.3 Migration History

| Migration | Version | Description |
|-----------|---------|-------------|
| 001 | Initial | Core schema (sessions, profiles, options, validations, fits, concerns, decision_briefs) |
| 002 | Phase C | Learning schema (assumption_validations, decision_retrospectives) |
| 003 | Phase D | Org intelligence (decision_dependencies, pattern_analysis_cache, coordination_groups, detected_conflicts, analytics_cache) |
| 004 | Perf | Performance indexes for Phase D queries |
| 005 | Phase 1-3 | Deliberation, preferences, onboarding, aggregation tables |
| 006 | Phase 5 | Autonomous learning (decision_outcomes, outcome_measurements) |
| 007 | Perf | Additional performance indexes |

---

## 6. Authentication & Security

### 6.1 JWT Authentication

**Token Format**: HS256 algorithm

**Token Claims**:
```json
{
  "sub": "user_id",
  "exp": 1640000000,
  "role": "admin|team_lead|member"
}
```

**Token Lifecycle**:
- **Expiration**: 60 minutes (configurable via `JWT_EXPIRATION_MINUTES`)
- **Secret**: `JWT_SECRET` environment variable (must be strong in production)
- **Algorithm**: HS256

**Endpoints Requiring Auth**:
- All Phase C endpoints (AI generation, synthesis, tuning, retrospectives)
- All Phase 1-5 endpoints (deliberation, preferences, onboarding, aggregation, outcomes)
- Session creation/status updates (admin/team_lead only)

### 6.2 WebSocket Authentication

**Method**: JWT in query parameter

**Connection Flow**:
```
1. Client requests token via standard auth endpoint
2. Client connects to WS: /api/v1/collaboration/ws/{session_id}?token={jwt}
3. Server validates JWT BEFORE accepting WebSocket connection
4. Server extracts user_id from token claims
5. Connection accepted or rejected (HTTP 1008 if invalid)
```

**Error Codes**:
- `1008`: Policy violation (invalid/missing token)

### 6.3 Rate Limiting

**Implementation**: Redis-backed per-user rate limiting

**Default Limits**:
- **Requests**: 100 requests
- **Window**: 60 seconds
- **Scope**: Per user (identified by JWT user_id or IP if unauthenticated)

**Response Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

**Error Response** (429 Too Many Requests):
```json
{
  "schema": "error.v1",
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Try again in 30 seconds.",
  "request_id": "req-123",
  "suggested_action": "retry_with_backoff"
}
```

### 6.4 Encryption

**Anonymous Voting** (Phase 1A/1B):
- **Algorithm**: AES-256-GCM
- **Purpose**: Encrypt user_id during active voting rounds
- **Storage**: `encrypted_user_id` in `deliberation_votes` table
- **Decryption**: Only after voting round closes
- **Key Management**: Stored securely (not in database)

### 6.5 CORS Configuration

**Allowed Origins**: Configurable via `CORS_ORIGINS` environment variable

**Default**: `http://localhost:3000` (development)

**Production Validation**:
- Wildcards (`*`) are rejected in production
- Explicit origin list required
- Preflight requests cached for 1 hour

**Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS, PATCH

**Allowed Headers**: Content-Type, Authorization, X-Request-ID, X-API-Key, Accept, Origin

**Exposed Headers**: X-Request-ID

### 6.6 API Key Authentication (PLoT Integration)

**Method**: `X-API-Key` header

**Scope**: Internal service-to-service only (PLoT → TAE)

**Configuration**: `PLOT_INTERNAL_API_KEY` environment variable

**Validation**:
- API key must match exactly
- Returns 403 if invalid
- Returns 500 if not configured

---

## 7. Configuration Reference

### 7.1 Environment Variables

**Service Configuration**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SERVICE_NAME` | string | `team-alignment-engine` | Service identifier |
| `SERVICE_VERSION` | string | `2.0.0` | Service version |
| `ENVIRONMENT` | string | `development` | Environment (development, staging, production) |
| `LOG_LEVEL` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

**Database Configuration**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | string | **Required** | PostgreSQL connection string |
| `DATABASE_POOL_SIZE` | int | `10` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | int | `20` | Max overflow connections |

**Redis Configuration**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_URL` | string | **Required** | Redis connection string |
| `REDIS_POOL_SIZE` | int | `10` | Connection pool size |
| `REDIS_CACHE_TTL` | int | `3600` | Default cache TTL (seconds) |

**CEE Integration**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CEE_BASE_URL` | string | **Required** | CEE service base URL |
| `CEE_API_KEY` | string | **Required** | CEE API key |
| `CEE_TIMEOUT` | int | `30` | Request timeout (seconds) |
| `CEE_USE_MOCK` | bool | `true` | Use mock CEE (development mode) |

**ISL Integration**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ISL_BASE_URL` | string | **Required** | ISL service base URL |
| `ISL_API_KEY` | string | **Required** | ISL API key |
| `ISL_TIMEOUT` | int | `60` | Request timeout (seconds) |

**PLoT Integration (POC v02)**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PLOT_DEPLOYMENT_MODE` | bool | `false` | Enable PLoT orchestration mode |
| `PLOT_INTERNAL_API_KEY` | string | `""` | Internal API key for PLoT → TAE auth |
| `PLOT_ORCHESTRATION_TIMEOUT` | int | `10` | Orchestration endpoint timeout (seconds) |
| `PLOT_CAPABILITY_FILTERING` | bool | `true` | Enable capability-based filtering |

**Security**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `JWT_SECRET` | string | **Required** | JWT signing secret (must be strong) |
| `JWT_ALGORITHM` | string | `HS256` | JWT signing algorithm |
| `JWT_EXPIRATION_MINUTES` | int | `60` | Token expiration time |
| `RATE_LIMIT_REQUESTS` | int | `100` | Rate limit requests per window |
| `RATE_LIMIT_WINDOW` | int | `60` | Rate limit window (seconds) |

**Monitoring**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PROMETHEUS_PORT` | int | `9090` | Prometheus metrics port |
| `ENABLE_METRICS` | bool | `true` | Enable Prometheus metrics |

**CORS**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CORS_ORIGINS` | string/list | `http://localhost:3000` | Allowed CORS origins (comma-separated) |

**Phase D: WebSocket Configuration**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WEBSOCKET_HEARTBEAT_INTERVAL` | int | `30` | Heartbeat interval (seconds) |
| `WEBSOCKET_MAX_CONNECTIONS_PER_SESSION` | int | `50` | Max concurrent connections per session |
| `WEBSOCKET_IDLE_TIMEOUT` | int | `300` | Idle timeout (5 minutes) |
| `WEBSOCKET_MESSAGE_MAX_SIZE` | int | `1048576` | Max message size (1MB) |

**Phase D: Analytics Configuration**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ANALYTICS_CACHE_TTL` | int | `300` | Analytics cache TTL (5 minutes) |
| `PATTERNS_CACHE_TTL` | int | `604800` | Patterns cache TTL (7 days) |
| `PORTFOLIO_MAX_SESSIONS` | int | `500` | Max sessions for portfolio analysis |

**Phase D: Performance Configuration**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REQUEST_TIMEOUT` | int | `30` | Default request timeout (seconds) |
| `DEPENDENCY_GRAPH_TIMEOUT` | int | `5` | Dependency graph timeout (seconds) |
| `PORTFOLIO_QUERY_TIMEOUT` | int | `10` | Portfolio query timeout (seconds) |

**Phase D: Feature Flags (POC v02 Priorities)**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FEATURE_PORTFOLIO_ANALYTICS_ENABLED` | bool | `true` | D1 - Portfolio Analytics (MUST HAVE) |
| `FEATURE_REALTIME_COLLABORATION_ENABLED` | bool | `false` | D2 - Real-time Collaboration (DEFERRED) |
| `FEATURE_DECISION_DEPENDENCIES_ENABLED` | bool | `true` | D3 - Decision Dependencies (MUST HAVE) |
| `FEATURE_ORGANIZATIONAL_PATTERNS_ENABLED` | bool | `true` | D4 - Organizational Patterns (MUST HAVE) |
| `FEATURE_ADVANCED_ANALYTICS_ENABLED` | bool | `false` | D5 - Advanced Analytics (DEFERRED) |
| `FEATURE_CROSS_TEAM_COORDINATION_ENABLED` | bool | `false` | D6 - Cross-Team Coordination (DEFERRED) |

### 7.2 Production Checklist

**Required for Production**:
- [ ] `ENVIRONMENT=production`
- [ ] Strong `JWT_SECRET` (min 32 characters)
- [ ] `CEE_USE_MOCK=false` (use real CEE)
- [ ] Valid `DATABASE_URL` (PostgreSQL 15+)
- [ ] Valid `REDIS_URL` (Redis 7.0+)
- [ ] Valid CEE credentials (`CEE_BASE_URL`, `CEE_API_KEY`)
- [ ] Valid ISL credentials (`ISL_BASE_URL`, `ISL_API_KEY`)
- [ ] Explicit `CORS_ORIGINS` (no wildcards)
- [ ] TLS/HTTPS enabled (via reverse proxy)
- [ ] Monitoring configured (Prometheus + Grafana)
- [ ] Database migrations applied (`alembic upgrade head`)

---

## 8. Deployment

### 8.1 Production Deployment Checklist

**Pre-Deployment**:
1. ✅ All tests passing (`pytest --cov`)
2. ✅ Code quality checks pass (`black`, `ruff`, `mypy`)
3. ✅ Database migrations generated and reviewed
4. ✅ Environment variables configured
5. ✅ Secrets validated (production mode)
6. ✅ CORS origins validated (no wildcards)
7. ✅ Load testing completed (Phase D pilot load test)

**Deployment Steps**:
1. **Staging Deployment**
   ```bash
   # Apply migrations (staging)
   alembic upgrade head

   # Deploy to staging
   docker build -t tae:staging .
   docker run -d --name tae-staging --env-file .env.staging tae:staging

   # Health check
   curl https://tae-staging.olumi.com/health/ready
   ```

2. **Database Migration Verification**
   ```bash
   # Verify migration status
   alembic current

   # Check for pending migrations
   alembic show current

   # Dry-run migration (if available)
   alembic upgrade head --sql
   ```

3. **Production Deployment**
   ```bash
   # Apply migrations (production)
   alembic upgrade head

   # Deploy to production
   docker build -t tae:2.0.0 .
   docker tag tae:2.0.0 tae:latest
   docker run -d --name tae-prod --env-file .env.production tae:2.0.0

   # Health check
   curl https://tae.olumi.com/health/ready
   ```

4. **Monitoring Setup**
   - Configure Prometheus scraping (`/metrics` endpoint)
   - Import Grafana dashboards (`monitoring/grafana/phase-d-dashboard.json`)
   - Configure alerts (`monitoring/prometheus/alerts.yml`)

5. **Health Verification**
   ```bash
   # Liveness probe
   curl https://tae.olumi.com/health/live

   # Readiness probe
   curl https://tae.olumi.com/health/ready

   # Detailed health metrics
   curl https://tae.olumi.com/health/metrics
   ```

### 8.2 Render Deployment (Consolidated from DEPLOYMENT.md and RENDER_DEPLOYMENT_GUIDE.md)

**Prerequisites**:
- Render account
- GitHub repository connected to Render
- PostgreSQL and Redis instances provisioned

**Service Configuration**:
1. Create new Web Service in Render
2. Connect GitHub repository
3. Configure build command: `pip install -r requirements.txt`
4. Configure start command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (see Section 7.1)

**Database Setup**:
1. Provision PostgreSQL instance in Render
2. Copy `DATABASE_URL` from Render dashboard
3. Run migrations: `alembic upgrade head`

**Redis Setup**:
1. Provision Redis instance in Render
2. Copy `REDIS_URL` from Render dashboard

**Health Checks**:
- Path: `/health/ready`
- Interval: 30s
- Timeout: 3s
- Failure threshold: 3

### 8.3 Rollback Procedures

**Database Rollback**:
```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Rollback all migrations (DANGER)
alembic downgrade base
```

**Service Rollback**:
```bash
# Docker rollback
docker stop tae-prod
docker rm tae-prod
docker run -d --name tae-prod --env-file .env.production tae:1.9.0

# Kubernetes rollback
kubectl rollout undo deployment/tae
kubectl rollout status deployment/tae
```

**Verification After Rollback**:
```bash
# Check service version
curl https://tae.olumi.com/ | jq .version

# Check database migration status
alembic current

# Run health checks
curl https://tae.olumi.com/health/ready
```

### 8.4 Health Check Endpoints

**Liveness Probe** (`/health/live`):
- Purpose: Is service running?
- Response time: <100ms
- Returns: 200 OK if alive

**Readiness Probe** (`/health/ready`):
- Purpose: Can service handle traffic?
- Checks: PostgreSQL, Redis, CEE, ISL
- Response time: <500ms
- Returns:
  - 200 OK: All dependencies healthy
  - 503 Service Unavailable: Critical dependency down
  - Header: `X-Olumi-Degraded` (if degraded mode)

**Detailed Metrics** (`/health/metrics`):
- Purpose: Comprehensive health info
- Includes:
  - Dependency statuses + latencies
  - Health score (0.0-1.0)
  - Database pool metrics
  - Phase D capability flags
  - Degraded mode indicators

### 8.5 Performance Targets (Phase D)

| Capability | Target Latency (p95) | Actual (Pilot) | Status |
|------------|---------------------|----------------|--------|
| Portfolio Analytics (100 sessions) | <5s | 2.1s | ✅ |
| WebSocket Broadcast | <100ms | 45ms | ✅ |
| Dependency Graph (100 decisions) | <2s | 1.3s | ✅ |
| Pattern Analysis (90 days) | <3s | 2.4s | ✅ |

**Concurrent User Support**: 40 concurrent users (pilot-tested)

---

## Appendix A: Quick Reference

### A.1 Key Metrics

```prometheus
# Request metrics
tae_request_duration_seconds{endpoint, method, status}
tae_requests_total{endpoint, method, status}

# Session metrics
tae_sessions_created_total{decision_type}
tae_sessions_completed_total{decision_type}

# Validation metrics
tae_validations_requested_total{validation_status}
tae_isl_errors_total{error_type}

# Phase D metrics
tae_portfolio_query_duration_seconds
tae_websocket_broadcast_latency_seconds
tae_dependency_graph_complexity{metric}
tae_pattern_cache_hit_rate
tae_cee_errors_total
```

### A.2 Common Commands

```bash
# Start service
poetry run uvicorn src.api.main:app --reload

# Run tests
poetry run pytest --cov

# Database migrations
poetry run alembic upgrade head
poetry run alembic downgrade -1

# Code quality
poetry run black src/ tests/
poetry run ruff src/ tests/
poetry run mypy src/

# Health checks
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/metrics
curl http://localhost:8000/metrics  # Prometheus
```

### A.3 External Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **CEE** | `https://cee-service.olumi.com` | LLM tasks (profile extraction, synthesis) |
| **ISL** | `https://isl-service.olumi.com` | Causal validation and sensitivity analysis |
| **PLoT** | `https://plot-service.olumi.com` | Orchestration layer |

---

## Appendix B: Glossary

**Alignment Mode**: Validation depth (QUICK = Phase A only, EVIDENCE_BACKED = Phase A + B)

**Causal Validation**: ISL-based verification that an option's rationale is causally sound

**CEE**: Context Extraction Engine - LLM service for profile extraction and synthesis

**Consensus Level**: Degree of stakeholder alignment (STRONG >0.8, MODERATE 0.6-0.8, WEAK 0.4-0.6, NONE <0.4)

**Decision Brief**: Comprehensive audit trail of a finalized decision

**Disagreement Map**: Structured representation of stakeholder tension axes

**Fit Analysis**: Calculation of how well an option aligns with each stakeholder's profile

**ISL**: Inference Service Layer - Causal analysis service

**Minority Concern**: Objection flagged by non-majority stakeholder (protected if evidence-backed)

**PLoT**: Product Language Orchestration Tool - Orchestration layer

**Profile**: 8-dimensional stakeholder preference model (extracted from free-text)

**Scenario Model**: External scenario planning model (optional integration)

**Sensitivity Analysis**: ISL test of how outcome changes if assumption varies

**Session**: Single decision-making instance with defined stakeholders

**Shared Ground**: Areas of stakeholder agreement (goals, beliefs, constraints)

**Stakeholder Role**: Permission level (OWNER, FACILITATOR, STAKEHOLDER, OBSERVER)

---

**Document Maintained By**: Platform Team, Olumi Inc.
**Contact**: platform@olumi.com
**Repository**: https://github.com/Talchain/Team-Alignment-Engine
