# PLoT Integration Guide (POC v02)

**Version:** 2.0.0
**Date:** 2025-11-21
**Status:** Ready for Integration Testing

This guide details how to integrate TAE (Team Alignment Engine) with PLoT Engine for POC v02, covering deployment, configuration, and testing.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Environment Configuration](#environment-configuration)
3. [Deployment](#deployment)
4. [Integration Testing](#integration-testing)
5. [Health Checks & Monitoring](#health-checks--monitoring)
6. [Troubleshooting](#troubleshooting)
7. [API Reference](#api-reference)

---

## 1. Architecture Overview

### Communication Flow

```
User → PLoT UI → PLoT Engine → TAE (internal) → PLoT Engine → PLoT UI
                      │                │
                      │                └─► (D1/D3/D4 capabilities)
                      │
                      └─► (X-API-Key auth, X-Request-Id tracing)
```

**Key Decisions (from Q1-Q8):**
- **Q1**: HTTP polling only (no WebSocket for POC v02)
- **Q2**: Capability-based filtering required
- **Q3**: TAE caches internally with Redis
- **Q4**: Echo PLoT's `X-Request-Id` header for tracing
- **Q5**: API key authentication (service-to-service)
- **Q6**: POC v02 priorities = D1/D3/D4 (MUST), D2/D5/D6 (DEFERRED)
- **Q7**: Graceful degradation with availability metadata
- **Q8**: Hybrid testing (contract + integration)

### Capability Matrix

| Capability | POC v02 Status | Description |
|------------|----------------|-------------|
| `core_alignment` (D1) | ✅ MUST HAVE | Session state, shared ground, disagreements |
| `d3_dependencies` | ✅ MUST HAVE | Decision dependency graph |
| `d4_patterns` | ✅ MUST HAVE | Organizational patterns from retrospectives |
| `d2_collaboration` | ❌ DEFERRED | Real-time collaboration (use HTTP polling) |
| `d5_analytics` | ❌ DEFERRED | Advanced analytics & trend forecasting |
| `d6_coordination` | ❌ DEFERRED | Cross-team coordination |

---

## 2. Environment Configuration

### Required Environment Variables

```bash
# ============================================================================
# PLOT INTEGRATION (POC v02)
# ============================================================================

# Enable PLoT deployment mode
PLOT_DEPLOYMENT_MODE=true

# Internal API key for PLoT → TAE authentication
# CRITICAL: This must match the key configured in PLoT Engine
PLOT_INTERNAL_API_KEY=<generate-secure-key>

# Orchestration timeout (seconds)
PLOT_ORCHESTRATION_TIMEOUT=10

# Enable capability-based filtering
PLOT_CAPABILITY_FILTERING=true

# ============================================================================
# TAE CORE CONFIGURATION
# ============================================================================

# Service
SERVICE_NAME=team-alignment-engine
SERVICE_VERSION=2.0.0
ENVIRONMENT=staging  # or production
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/tae_db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis (for internal caching)
REDIS_URL=redis://host:6379/0
REDIS_POOL_SIZE=10
REDIS_CACHE_TTL=3600  # 1 hour

# External Services
CEE_BASE_URL=https://cee-service.example.com
CEE_API_KEY=<cee-api-key>
CEE_TIMEOUT=30

ISL_BASE_URL=https://isl-service.example.com
ISL_API_KEY=<isl-api-key>
ISL_TIMEOUT=60

# Security
JWT_SECRET=<generate-secure-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Feature Flags (Phase D capabilities)
FEATURE_PORTFOLIO_ANALYTICS_ENABLED=true       # D1
FEATURE_DECISION_DEPENDENCIES_ENABLED=true     # D3
FEATURE_ORGANIZATIONAL_PATTERNS_ENABLED=true   # D4
FEATURE_COLLABORATION_ENABLED=false            # D2 (deferred)
FEATURE_ANALYTICS_ENGINE_ENABLED=false         # D5 (deferred)
FEATURE_COORDINATION_ENABLED=false             # D6 (deferred)
```

### Generating API Keys

```bash
# Generate secure API key for PLoT integration
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**IMPORTANT**: Store API keys in secure secret management (e.g., AWS Secrets Manager, HashiCorp Vault, Azure Key Vault).

### Configuration Validation

```bash
# Verify configuration loads correctly
poetry run python -c "from src.config import settings; \
  print(f'PLoT mode: {settings.plot_deployment_mode}'); \
  print(f'API key configured: {bool(settings.plot_internal_api_key)}'); \
  print(f'D1/D3/D4 enabled: {settings.feature_portfolio_analytics_enabled}/{settings.feature_decision_dependencies_enabled}/{settings.feature_organizational_patterns_enabled}')"
```

Expected output:
```
PLoT mode: True
API key configured: True
D1/D3/D4 enabled: True/True/True
```

---

## 3. Deployment

### Deployment Checklist

- [ ] PostgreSQL database provisioned and migrations run
- [ ] Redis cache provisioned
- [ ] CEE and ISL services accessible
- [ ] Environment variables configured (see Section 2)
- [ ] `PLOT_INTERNAL_API_KEY` matches key in PLoT Engine
- [ ] Health checks passing (see Section 5)
- [ ] Contract tests passing (see Section 4)

### Docker Deployment

```dockerfile
# Example Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

# Copy application
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Run migrations and start server
CMD ["sh", "-c", "poetry run alembic upgrade head && poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000"]
```

### Database Migrations

```bash
# Run Alembic migrations
poetry run alembic upgrade head

# Verify migrations
poetry run alembic current
```

### Starting the Service

```bash
# Development
poetry run uvicorn src.api.main:app --reload --port 8000

# Production
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 4. Integration Testing

### 4.1 Contract Tests (Cross-Team Testing)

Contract tests validate API schema stability using golden fixtures.

```bash
# Run contract tests
poetry run pytest tests/contract/test_plot_orchestration_contract.py -v

# Expected: 23 passing tests
```

**Golden Fixtures** (in `tests/contract/fixtures/`):
- `golden_full_response.json` - All D1/D3/D4 capabilities succeed
- `golden_partial_d1d3.json` - Subset request (D1+D3 only)
- `golden_partial_failure.json` - D4 fails, D1/D3 succeed
- `golden_error_response.json` - Complete failure

**PLoT Team Usage:**
PLoT team can use golden fixtures to:
1. Verify response parsing logic
2. Test error handling scenarios
3. Validate UI rendering of TAE data

### 4.2 Integration Tests (PLoT ↔ TAE)

```bash
# Step 1: Start TAE service
poetry run uvicorn src.api.main:app --port 8000

# Step 2: Test authentication
curl -X POST http://localhost:8000/api/v1/plot/alignment-session \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <PLOT_INTERNAL_API_KEY>" \
  -H "X-Request-Id: test-request-123" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "organization_id": "org-123",
    "capabilities": ["core_alignment", "d3_dependencies", "d4_patterns"]
  }'

# Expected: 200 OK with TaeTeamAlignmentPayload
```

### 4.3 End-to-End Test Scenarios

#### Scenario 1: Full Success (All Capabilities)

```bash
curl -X POST http://localhost:8000/api/v1/plot/alignment-session \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $PLOT_API_KEY" \
  -H "X-Request-Id: e2e-test-001" \
  -d '{
    "session_id": "<valid-session-uuid>",
    "organization_id": "<valid-org-uuid>",
    "capabilities": ["core_alignment", "d3_dependencies", "d4_patterns"],
    "context": {}
  }'
```

Expected response:
```json
{
  "session_id": "<session-uuid>",
  "organization_id": "<org-uuid>",
  "timestamp": "2025-11-21T12:00:00Z",
  "version": "2.0.0",
  "request_id": "e2e-test-001",
  "alignment": { "session_state": "deliberating", ... },
  "organizational_context": {
    "similar_decisions": [...],
    "dependencies": [...]
  },
  "availability": {
    "tae_available": true,
    "capabilities": {
      "d1_portfolio_analytics": true,
      "d3_decision_dependencies": true,
      "d4_organizational_patterns": true
    },
    "degraded": false
  }
}
```

#### Scenario 2: Partial Failure (D4 Unavailable)

When pattern analyzer times out, TAE returns partial success:

```json
{
  "session_id": "<session-uuid>",
  "alignment": { ... },  // D1 succeeded
  "organizational_context": {
    "similar_decisions": [],  // D4 failed, empty
    "dependencies": [...]     // D3 succeeded
  },
  "availability": {
    "tae_available": true,
    "capabilities": {
      "d1_portfolio_analytics": true,
      "d3_decision_dependencies": true,
      "d4_organizational_patterns": false  // Failed
    },
    "degraded": true,
    "degradation_reason": "Some capabilities unavailable: d4_patterns"
  }
}
```

#### Scenario 3: Complete Failure

When all capabilities fail:

```json
{
  "session_id": "<session-uuid>",
  "alignment": null,
  "decision_quality": null,
  "organizational_context": {
    "similar_decisions": [],
    "dependencies": [],
    "conflicts": []
  },
  "availability": {
    "tae_available": false,
    "capabilities": {
      "d1_portfolio_analytics": false,
      "d3_decision_dependencies": false,
      "d4_organizational_patterns": false
    },
    "degraded": true,
    "degradation_reason": "TAE service error: Database connection timeout"
  }
}
```

### 4.4 Performance Testing

```bash
# Test p95 latency (target: <10s)
for i in {1..20}; do
  time curl -X POST http://localhost:8000/api/v1/plot/alignment-session \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $PLOT_API_KEY" \
    -H "X-Request-Id: perf-test-$i" \
    -d '{...}' > /dev/null 2>&1
done
```

**Performance Targets (POC v02):**
- p50 latency: <5s
- p95 latency: <10s
- Availability: >99% (graceful degradation counts as available)

---

## 5. Health Checks & Monitoring

### 5.1 Health Check Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "version": "2.0.0"}
```

### 5.2 Readiness Check

Verify all dependencies are accessible:

```bash
# Check database connectivity
curl http://localhost:8000/health/db

# Check Redis connectivity
curl http://localhost:8000/health/redis

# Check CEE/ISL connectivity
curl http://localhost:8000/health/dependencies
```

### 5.3 Monitoring Metrics

TAE exposes Prometheus metrics at `/metrics`:

```
# Key metrics for PLoT integration
tae_plot_orchestration_requests_total{status="success|partial|error"}
tae_plot_orchestration_duration_seconds{capability="d1|d3|d4"}
tae_plot_capability_failures_total{capability="d1|d3|d4"}
tae_plot_degraded_responses_total
```

**Alerting Recommendations:**
- Alert if `tae_plot_orchestration_requests_total{status="error"} > 5%`
- Alert if `tae_plot_capability_failures_total{capability="d1"} > 10%` (D1 is critical)
- Alert if p95 latency > 10s for 5 consecutive minutes

### 5.4 Log Correlation

TAE echoes PLoT's `X-Request-Id` header in logs:

```json
{
  "timestamp": "2025-11-21T12:00:00Z",
  "level": "INFO",
  "message": "PLoT orchestration request completed",
  "request_id": "plot-run-abc123",  // Echoed from X-Request-Id
  "session_id": "550e8400-...",
  "duration_ms": 4523,
  "capabilities_returned": 3,
  "degraded": false
}
```

**Log Search Examples:**
```bash
# Find all logs for a specific PLoT request
grep "plot-run-abc123" tae.log

# Find all degraded responses
grep "degraded\":true" tae.log

# Find capability failures
grep "Failed to get" tae.log
```

---

## 6. Troubleshooting

### Common Issues

#### Issue 1: 403 Forbidden

**Symptom:**
```json
{"detail": "Invalid API key"}
```

**Causes:**
1. `X-API-Key` header missing
2. `PLOT_INTERNAL_API_KEY` mismatch between PLoT and TAE
3. API key not configured in TAE

**Resolution:**
```bash
# Verify TAE has API key configured
poetry run python -c "from src.config import settings; print(f'API key: {settings.plot_internal_api_key[:8]}...')"

# Compare with PLoT's configured key
echo "PLoT key: ${PLOT_API_KEY:0:8}..."

# If mismatch, regenerate and update both services
```

#### Issue 2: Partial Failures (degraded=true)

**Symptom:**
```json
{
  "availability": {
    "degraded": true,
    "degradation_reason": "Some capabilities unavailable: d4_patterns"
  }
}
```

**Causes:**
1. PatternAnalyzer timeout
2. Database query slow
3. External service (CEE/ISL) unavailable

**Resolution:**
```bash
# Check TAE logs for specific error
grep "Failed to get patterns" tae.log | tail -20

# Check external service health
curl $CEE_BASE_URL/health
curl $ISL_BASE_URL/health

# Check database performance
psql $DATABASE_URL -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

#### Issue 3: Complete Failure (tae_available=false)

**Symptom:**
```json
{
  "alignment": null,
  "availability": {
    "tae_available": false,
    "degradation_reason": "TAE service error: ..."
  }
}
```

**Causes:**
1. Database connection failure
2. Critical service crash
3. Timeout exceeded

**Resolution:**
```bash
# Check TAE service is running
curl http://localhost:8000/health

# Check database connectivity
poetry run python -c "from src.storage.database import engine; engine.connect()"

# Restart TAE service
systemctl restart tae  # or docker-compose restart tae
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Restart service
poetry run uvicorn src.api.main:app --reload

# Tail logs
tail -f tae.log | grep -E "(DEBUG|ERROR)"
```

---

## 7. API Reference

### Endpoint: `POST /api/v1/plot/alignment-session`

**Description**: Get team alignment session data for PLoT orchestration (internal-only).

**Authentication**: API key via `X-API-Key` header

**Headers:**
- `X-API-Key` (required): Service-to-service API key
- `X-Request-Id` (optional): Request ID for distributed tracing (echoed in response)
- `Content-Type`: `application/json`

**Request Body:**
```json
{
  "session_id": "string (UUID) | null",
  "organization_id": "string (UUID, required)",
  "capabilities": ["string"],  // Default: ["core_alignment"]
  "context": {}  // Optional additional context
}
```

**Response: `TaeTeamAlignmentPayload`**
```json
{
  "session_id": "string | null",
  "organization_id": "string",
  "timestamp": "datetime",
  "version": "string",
  "request_id": "string | null",
  "alignment": {
    "session_state": "collecting_perspectives | proposing_options | deliberating | decided | unknown",
    "stakeholder_count": "integer",
    "perspectives_collected": "integer",
    "options_proposed": "integer",
    "consensus_level": "float (0-1)",
    "shared_ground": {
      "summary": "string",
      "common_goal_weights": {},
      "aligned_priorities": []
    },
    "disagreements": {
      "summary": "string",
      "axes": [
        {
          "dimension": "string",
          "stakeholders_involved": [],
          "severity_score": "float (0-1)",
          "description": "string"
        }
      ]
    }
  },
  "decision_quality": {
    "health_score": "float (0-1)",
    "risk_flags": [],
    "causally_validated": "boolean",
    "assumption_strength": "float (0-1)",
    "minority_concerns": []
  },
  "organizational_context": {
    "similar_decisions": [
      {
        "session_id": "string",
        "outcome": "success | failure | neutral",
        "similarity": "float (0-1)",
        "key_lessons": [],
        "timestamp": "datetime"
      }
    ],
    "dependencies": [
      {
        "dependent_session_id": "string",
        "dependency_type": "blocks | informs | conflicts",
        "team": "string",
        "description": "string | null",
        "status": "pending | resolved | blocked"
      }
    ],
    "trend_insights": null,  // Deferred for POC v02
    "conflicts": []  // Deferred for POC v02
  },
  "collaboration": null,  // Deferred for POC v02
  "availability": {
    "tae_available": "boolean",
    "capabilities": {
      "d1_portfolio_analytics": "boolean",
      "d2_realtime_collaboration": false,  // Deferred
      "d3_decision_dependencies": "boolean",
      "d4_organizational_patterns": "boolean",
      "d5_advanced_analytics": false,  // Deferred
      "d6_cross_team_coordination": false  // Deferred
    },
    "degraded": "boolean",
    "degradation_reason": "string | null"
  }
}
```

**Status Codes:**
- `200 OK`: Success (including partial success with degraded=true)
- `403 Forbidden`: Invalid API key
- `422 Unprocessable Entity`: Invalid request payload
- `500 Internal Server Error`: TAE service error (returns error payload with availability status)

---

## Contact & Support

**TAE Team:**
- GitHub: https://github.com/talchain/team-alignment-engine
- Issues: https://github.com/talchain/team-alignment-engine/issues

**PLoT Integration Questions:**
- Slack: #plot-tae-integration
- Email: tae-support@example.com

**Documentation:**
- Architecture: `/docs/TAE_IMPLEMENTATION_BRIEF_PHASE2.md`
- Contract Tests: `/tests/contract/`
- Golden Fixtures: `/tests/contract/fixtures/`

---

**Last Updated:** 2025-11-21
**Reviewer:** TAE Engineering Team
**Status:** ✅ Ready for POC v02 Integration Testing
