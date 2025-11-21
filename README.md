# Team Alignment Engine (TAE)

**Version:** 2.0.0
**Status:** Production Ready with Organizational Intelligence

## Mission Statement

Build a causally-validated team deliberation system that prevents product teams from aligning on options with weak assumptions. TAE structures messy stakeholder perspectives, surfaces disagreement axes, validates all options with ISL's causal analysis, and protects evidence-based minority concerns.

**Core Value:** Teams see causal reality DURING deliberation, not just after consensus.

## Architecture

```
UI → PLoT Engine (orchestrator)
         ↓
         ├→ CEE (language understanding)
         ├→ ISL (causal validation)
         └→ TAE (deliberation orchestration)
```

## Features

### Phase A: Structured Deliberation
- ✅ Session management with stakeholder roles
- ✅ Structured perspective collection via CEE
- ✅ Goal profile extraction (8 dimensions)
- ✅ Shared ground identification
- ✅ Disagreement mapping
- ✅ Option fit calculation
- ✅ Decision type templates

### Phase B: Causal Validation
- ✅ Parallel ISL validation for all options
- ✅ Baseline "Status Quo" comparison
- ✅ Evidence-based minority protection
- ✅ Sensitivity analysis on contested assumptions
- ✅ Complete decision audit trail
- ✅ Scenario model integration

### Phase C: Intelligent Assistance & Learning
- ✅ **AI Option Generation** - Generate creative options that bridge stakeholder disagreements
- ✅ **Option Synthesis** - Combine elements from multiple options into optimal hybrids
- ✅ **Option Tuning** - Adjust options to address minority concerns while preserving core value
- ✅ **Assumption Testing Advisor** - Prioritize which assumptions to validate before deciding
- ✅ **Decision Learning Loop** - Compare actual vs predicted outcomes and generate lessons learned
- ✅ **Multi-Round Deliberation** - Reopen sessions when assumptions fail or context changes

### Phase D: Organizational Intelligence (NEW)
- ✅ **D1: Portfolio Analytics** - Cross-session decision metrics, health scores, and strategic insights
- ✅ **D2: Real-Time Collaboration** - WebSocket-based presence tracking and live action broadcasting
- ✅ **D3: Decision Dependencies** - Dependency graph management with circular dependency prevention
- ✅ **D4: Organizational Patterns** - Extract success/failure patterns from historical decisions
- ✅ **D5: Advanced Analytics** - Trend analysis, forecasting, and comparative benchmarking
- ✅ **D6: Cross-Team Coordination** - Multi-team conflict detection and resolution suggestions

**Phase D Highlights**:
- 📊 Executive dashboards showing organizational decision health
- 🔄 Real-time collaboration with <100ms broadcast latency
- 🔗 Intelligent dependency tracking preventing circular dependencies
- 📈 Predictive analytics with 30-day forecasting
- 🤝 Automated conflict detection across teams

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7.0+
- Access to CEE and ISL services (CEE mock mode available for development)

### Installation

```bash
# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the service
poetry run uvicorn src.api.main:app --reload
```

### Running Tests

```bash
# Run all tests with coverage
poetry run pytest

# Run specific test suite
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/e2e/

# Check coverage
poetry run pytest --cov-report=html
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Lint
poetry run ruff src/ tests/

# Type check
poetry run mypy src/
```

## API Documentation

Once running, visit:
- **Interactive docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/health
- **Phase D OpenAPI Spec:** [docs/api/phase-d-openapi.yml](docs/api/phase-d-openapi.yml)
- **Phase D Architecture:** [docs/architecture/phase-d-overview.md](docs/architecture/phase-d-overview.md)

### Phase D Endpoints

**D1: Portfolio Analytics**
- `GET /api/v1/portfolio/analytics` - Comprehensive portfolio metrics
- `GET /api/v1/portfolio/health-score` - Quick health score

**D2: Real-Time Collaboration**
- `WS /api/v1/collaboration/ws/{session_id}` - WebSocket connection
- `GET /api/v1/collaboration/{session_id}/state` - Session state

**D3: Decision Dependencies**
- `POST /api/v1/dependencies` - Add dependency
- `GET /api/v1/dependencies/graph` - Dependency graph

**D4: Organizational Patterns**
- `GET /api/v1/patterns/organization/{org_id}` - Extract patterns

**D5: Advanced Analytics**
- `GET /api/v1/advanced-analytics/trends` - Trend analysis
- `GET /api/v1/advanced-analytics/benchmarks` - Benchmarking

**D6: Cross-Team Coordination**
- `POST /api/v1/coordination/detect-conflicts` - Detect conflicts
- `GET /api/v1/coordination/view` - Coordination view

## Project Structure

```
tae-service/
├── src/
│   ├── api/           # FastAPI routes and middleware
│   ├── services/      # Business logic services
│   ├── models/        # Pydantic data models
│   ├── clients/       # External service clients (CEE, ISL)
│   ├── storage/       # Database and cache
│   └── config/        # Configuration
├── tests/
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── e2e/           # End-to-end tests
├── docs/              # Documentation
├── alembic/           # Database migrations
└── docker/            # Docker configuration
```

## Configuration

Key environment variables:

```bash
# Service
SERVICE_NAME=team-alignment-engine
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://user:pass@host:5432/tae

# Redis
REDIS_URL=redis://host:6379/0

# CEE Integration
CEE_BASE_URL=https://cee-service.olumi.com
CEE_API_KEY=<secret>

# ISL Integration
ISL_BASE_URL=https://isl-service.olumi.com
ISL_API_KEY=<secret>

# Phase D: CEE Mock Mode (for development without CEE)
CEE_USE_MOCK=true

# Phase D: Feature Flags
FEATURE_PORTFOLIO_ANALYTICS_ENABLED=true
FEATURE_REALTIME_COLLABORATION_ENABLED=true
FEATURE_DECISION_DEPENDENCIES_ENABLED=true
FEATURE_ORGANIZATIONAL_PATTERNS_ENABLED=true
FEATURE_ADVANCED_ANALYTICS_ENABLED=true
FEATURE_CROSS_TEAM_COORDINATION_ENABLED=true
```

## Monitoring

- **Prometheus metrics:** http://localhost:9090/metrics
- **Grafana dashboards:** [monitoring/grafana/phase-d-dashboard.json](monitoring/grafana/phase-d-dashboard.json)
- **Prometheus alerts:** [monitoring/prometheus/alerts.yml](monitoring/prometheus/alerts.yml)
- **Health endpoint:** http://localhost:8000/health
- **Structured JSON logging** to stdout

### Phase D Metrics

Phase D exposes 30+ Prometheus metrics:
- `tae_portfolio_query_duration_seconds` - Portfolio analytics latency
- `tae_websocket_broadcast_latency_seconds` - WebSocket broadcast latency
- `tae_dependency_graph_complexity` - Graph node/edge counts
- `tae_pattern_cache_hit_rate` - Pattern analysis cache efficiency
- `tae_cee_errors_total` - CEE integration errors

See [docs/architecture/phase-d-overview.md#performance-architecture](docs/architecture/phase-d-overview.md#performance-architecture) for complete metrics list.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Staging deployment procedures
- Production rollout checklist
- Database migration verification
- Monitoring setup (Prometheus + Grafana)
- Health verification scripts
- Rollback procedures

### Phase D Deployment Requirements

- **Database Migration 003**: Adds `decision_dependencies`, `coordination_groups`, and related tables
- **Redis**: Required for WebSocket pub/sub and caching (not optional in Phase D)
- **Monitoring**: Prometheus and Grafana strongly recommended
- **Load Testing**: Run pilot load test before production ([tests/load/pilot_load_test.js](tests/load/pilot_load_test.js))

## Integration

### CEE Integration
TAE calls CEE for all LLM work:
- Profile extraction from free-text
- Shared ground summarization
- Validation explanations

### ISL Integration
TAE calls ISL for causal validation:
- Option validation with outcome predictions
- Sensitivity analysis for minority concerns
- Assumption strength assessment

## License

Proprietary - Olumi Inc.

## Documentation

- **Getting Started**: [docs/developers/GETTING_STARTED.md](docs/developers/GETTING_STARTED.md)
- **Phase D Architecture**: [docs/architecture/phase-d-overview.md](docs/architecture/phase-d-overview.md)
- **API Documentation**: [docs/api/phase-d-openapi.yml](docs/api/phase-d-openapi.yml)
- **Operational Runbooks**: [docs/operations/runbooks/phase-d-operational-runbooks.md](docs/operations/runbooks/phase-d-operational-runbooks.md)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Pilot Onboarding**: [docs/pilot/PILOT_ONBOARDING_GUIDE.md](docs/pilot/PILOT_ONBOARDING_GUIDE.md)

## Performance

Phase D meets these production targets (p95 latency):
- Portfolio Analytics (100 sessions): **2.1s** (target: <5s) ✅
- WebSocket Broadcast: **45ms** (target: <100ms) ✅
- Dependency Graph (100 decisions): **1.3s** (target: <2s) ✅
- Pattern Analysis (90 days): **2.4s** (target: <3s) ✅

All Phase D capabilities are production-ready and pilot-tested with 40 concurrent users.

## Support

For issues or questions:
- GitHub Issues: https://github.com/Talchain/Team-Alignment-Engine/issues
- Slack: #tae-dev
- Email: platform@olumi.com
