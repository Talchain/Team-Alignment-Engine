# Team Alignment Engine - Action Plan Summary

**Quick Reference Guide for Implementation**

---

## 🔴 WEEK 1: CRITICAL FIXES (36.5 hours)

### Security (Priority 0)
- [ ] **AUTH-001:** Implement JWT authentication middleware (6h)
  - File: `src/api/middleware/auth.py`
  - Apply to all routes in `src/api/main.py`

- [ ] **AUTH-002:** Add authorization checks (7h)
  - File: `src/services/authorization.py`
  - Update all route handlers

- [ ] **AUTH-003:** Secure WebSocket endpoint (2h)
  - File: `src/api/routes/collaboration.py:37`
  - Validate JWT token before connection

- [ ] **SEC-001:** Rotate all credentials (1h)
  - Generate new DATABASE_URL password
  - Generate new CEE_API_KEY, ISL_API_KEY
  - Generate new JWT_SECRET: `openssl rand -hex 32`
  - Remove .env from git history

### Performance (Priority 0)
- [ ] **PERF-001:** Fix sequential API calls to parallel (1h)
  - File: `src/services/validation_orchestrator.py:45-58`
  - Use `asyncio.gather()` for parallel ISL validation
  - Expected: 300s → 60s (80% improvement)

- [ ] **PERF-002:** Add database indexes (1h)
  - Create migration: `alembic revision -m "add_indexes"`
  - Indexes: sessions.team_id, profiles.user_id, options.session_id

- [ ] **PERF-003:** Fix N+1 profile lookups (2h)
  - File: `src/services/fit_calculator.py:89-102`
  - Fetch all profiles in single query
  - Expected: 10,000 queries → 2 queries

### Dependencies (Priority 0)
- [ ] **DEP-001:** Update httpx (15min)
  ```bash
  poetry add httpx@^0.27.2
  ```

- [ ] **DEP-002:** Update setuptools (15min)
  ```bash
  poetry add setuptools@^78.1.1
  ```

### Testing (Priority 0)
- [ ] **TEST-001:** Fix 42 failing tests (16h)
  - Update Pydantic validation tests
  - Fix E2E flow KeyError issues
  - Fix WebSocket async tests

**WEEK 1 GOAL:** Production-ready security + 80% performance improvement

---

## 🟡 WEEK 2: HIGH PRIORITY (37 hours)

### Testing
- [ ] Add database model tests (8h)
  - File: `tests/unit/test_db_models.py`
  - Target: 0% → 80% coverage on `src/storage/db_models.py`

- [ ] Add CEE/ISL integration tests (6h)
  - File: `tests/integration/test_external_clients.py`
  - Test real API calls with credentials

### API Design
- [ ] Implement pagination (8h)
  - Add `PaginationParams` dependency
  - Update all list endpoints
  - Create `PaginatedResponse` model

- [ ] Fix CORS configuration (15min)
  - File: `src/api/main.py:49-55`
  - Replace wildcards with specific values

### Dependencies
- [ ] Update pydantic to 2.10.3 (2h)
  ```bash
  poetry add pydantic@^2.10.3
  ```
  - Test model compatibility

- [ ] Update python-multipart (15min)
  ```bash
  poetry add python-multipart@^0.0.18
  ```

### Performance
- [ ] Implement query-level caching (6h)
  - Cache CEE profile extraction results
  - Cache ISL validation responses
  - Use Redis with 1-hour TTL

- [ ] Move rate limiting to Redis (4h)
  - File: `src/api/middleware/rate_limiter.py`
  - Replace in-memory dict with Redis

### Documentation
- [ ] Create API versioning policy (2h)
  - File: `docs/API_VERSIONING_POLICY.md`
  - Define deprecation timeline (12 months)
  - Document migration process

**WEEK 2 GOAL:** Robust testing + Professional API design

---

## 🟢 WEEKS 3-4: MEDIUM PRIORITY (71 hours)

### CI/CD (16h)
- [ ] Set up GitHub Actions workflow
  - File: `.github/workflows/ci.yml`
  - Run tests on every PR
  - Generate coverage reports
  - Block merge if tests fail

### Security (8h)
- [ ] Implement secrets management
  - Integrate HashiCorp Vault or AWS Secrets Manager
  - Remove all secrets from .env
  - Update deployment documentation

### Performance (11h)
- [ ] Add performance/load tests (8h)
  - Tool: k6 or Locust
  - Test scenarios: 100 concurrent users
  - Measure P50, P95, P99 latencies

- [ ] Optimize WebSocket broadcast (3h)
  - File: `src/services/collaboration_manager.py:145-168`
  - Single pub/sub per session (not per connection)

### API Design (20h)
- [ ] Add filtering and sorting (8h)
  - Query params: `order_by`, `sort_order`, `filter_by`
  - Apply to all list endpoints

- [ ] Enhance API documentation (12h)
  - Add cURL examples for all endpoints
  - Document authentication flow
  - Add code examples (Python, JavaScript)
  - Improve OpenAPI schema

### Monitoring (8h)
- [ ] Create Grafana dashboards
  - Session creation rate
  - Validation latency (P50, P95)
  - Error rate by endpoint
  - Cache hit rate

### Code Quality (8h)
- [ ] Standardize endpoint naming
  - Convert action verbs to resources
  - Example: `/analyze` → `/analysis`

- [ ] Add comprehensive docstrings
  - All endpoints with request/response examples
  - Error scenarios documented

**WEEKS 3-4 GOAL:** Production excellence + monitoring

---

## Quick Command Reference

### Run Security Fixes
```bash
# Update vulnerable dependencies
poetry add httpx@^0.27.2 setuptools@^78.1.1 pydantic@^2.10.3

# Generate new JWT secret
openssl rand -hex 32

# Remove .env from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

### Run Performance Fixes
```bash
# Create migration for indexes
alembic revision -m "add_performance_indexes"

# Test parallel validation
python -m pytest tests/integration/test_validation_orchestrator.py -v
```

### Run Tests
```bash
# Fix failing tests first
python -m pytest tests/unit/test_models.py -v

# Check coverage
python -m pytest --cov=src --cov-report=html
open htmlcov/index.html

# Run only integration tests
python -m pytest tests/integration/ -v
```

### Deploy to Staging
```bash
# Build and deploy
docker build -t tae:latest .
docker-compose -f docker-compose.staging.yml up -d

# Run migrations
docker exec tae-app alembic upgrade head

# Health check
curl http://staging:8000/health
```

---

## Success Checklist

### Week 1 ✅
- [ ] All API endpoints require authentication
- [ ] WebSocket validates JWT tokens
- [ ] All credentials rotated and in vault
- [ ] httpx and setuptools updated
- [ ] Validation completes in <60s (was 300s)
- [ ] Database queries use indexes
- [ ] All 92 tests passing (100% success rate)

### Week 2 ✅
- [ ] Test coverage > 70%
- [ ] Database models tested (80% coverage)
- [ ] All list endpoints paginated
- [ ] API versioning policy documented
- [ ] CEE/ISL integration tests passing
- [ ] Rate limiting works across servers

### Weeks 3-4 ✅
- [ ] CI/CD pipeline active (GitHub Actions)
- [ ] All secrets in vault (not .env)
- [ ] Performance tests passing (P95 < 1s)
- [ ] API documentation complete
- [ ] Grafana dashboards deployed
- [ ] Load testing shows 10x capacity

---

## Emergency Rollback Procedures

### If authentication breaks production:
```bash
# Temporarily disable auth middleware
# File: src/api/main.py - comment out auth middleware
# app.add_middleware(AuthMiddleware)  # DISABLED

# Redeploy
git revert HEAD
docker-compose up -d --build
```

### If database migration fails:
```bash
# Rollback migration
alembic downgrade -1

# Check database state
psql $DATABASE_URL -c "SELECT * FROM alembic_version;"
```

### If performance degrades:
```bash
# Enable query logging
# Check slow queries
docker exec tae-db psql -U tae_user -d tae_db \
  -c "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Disable new caching (if suspect)
# Set REDIS_CACHE_ENABLED=false in .env
```

---

## Contact & Escalation

**Technical Lead:** [Name]
**DevOps Lead:** [Name]
**Security Lead:** [Name]

**Escalation Path:**
1. Try rollback procedures above
2. Check logs: `docker logs tae-app --tail=100`
3. Contact on-call engineer
4. If critical: Page technical lead

---

**Document Version:** 1.0
**Created:** November 22, 2025
**Next Review:** After Week 1 completion
