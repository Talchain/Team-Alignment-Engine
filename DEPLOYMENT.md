# TAE Phase D - Deployment Guide

**Version:** 2.0.0
**Phase:** D (Organizational Intelligence)
**Status:** Production-Ready
**Last Updated:** November 2025

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Staging Deployment](#staging-deployment)
3. [Database Migration](#database-migration)
4. [Monitoring Setup](#monitoring-setup)
5. [Health Verification](#health-verification)
6. [Rollback Procedures](#rollback-procedures)
7. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Required Infrastructure

- [x] PostgreSQL 13+ database (staging instance)
- [x] Redis 6+ instance (for WebSocket pub/sub and caching)
- [x] Python 3.11+ runtime environment
- [x] Docker (optional, for containerized deployment)
- [x] Prometheus + Grafana (for monitoring)

### Configuration Requirements

Before deploying, ensure you have:

1. **Database Credentials**
   ```bash
   DATABASE_URL=postgresql://user:pass@host:port/db
   ```

2. **Redis Credentials**
   ```bash
   REDIS_URL=redis://host:port/0
   ```

3. **JWT Secret** (generate new for staging)
   ```bash
   openssl rand -hex 32
   ```

4. **CEE API Key** (if using real CEE, otherwise mock=true)
5. **ISL API Key** (for causal validation)
6. **CORS Origins** (staging UI domains)

### Environment File Setup

1. Copy `.env.staging` template:
   ```bash
   cp .env.staging .env
   ```

2. Replace all `CHANGEME` values:
   - `DATABASE_URL`
   - `REDIS_URL`
   - `JWT_SECRET`
   - `CEE_API_KEY`
   - `ISL_API_KEY`
   - `CORS_ORIGINS`

3. Verify configuration:
   ```bash
   grep CHANGEME .env  # Should return nothing
   ```

---

## Staging Deployment

### Option 1: Docker Deployment (Recommended)

1. **Build Docker image:**
   ```bash
   docker build -t tae-phase-d:2.0.0 .
   ```

2. **Run database migration:**
   ```bash
   docker run --rm --env-file .env tae-phase-d:2.0.0 \
     poetry run alembic upgrade head
   ```

3. **Start the service:**
   ```bash
   docker run -d \
     --name tae-staging \
     --env-file .env \
     -p 8000:8000 \
     -p 9090:9090 \
     tae-phase-d:2.0.0
   ```

4. **Verify health:**
   ```bash
   curl http://localhost:8000/health
   ```

### Option 2: Direct Deployment

1. **Install dependencies:**
   ```bash
   poetry install --only main
   ```

2. **Run database migration:**
   ```bash
   poetry run alembic upgrade head
   ```

3. **Start the service:**
   ```bash
   poetry run uvicorn src.api.main:app \
     --host 0.0.0.0 \
     --port 8000 \
     --workers 4
   ```

### Deployment Verification

Check that all services are healthy:

```bash
# Health check
curl http://localhost:8000/health | jq .

# Expected response:
{
  "status": "ok",
  "service": "team-alignment-engine",
  "version": "2.0.0",
  "environment": "staging",
  "dependencies": {
    "database": {"status": "connected"},
    "redis": {"status": "connected"},
    ...
  },
  "phase_d_capabilities": {
    "d1_portfolio_analytics": true,
    "d2_realtime_collaboration": true,
    ...
  }
}
```

---

## Database Migration

### Migration 003: Phase D Schema

Phase D adds 5 new tables and modifies existing tables:

**New Tables:**
- `decision_dependencies` - Dependency graph
- `pattern_analysis_cache` - Pattern learning cache
- `coordination_groups` - Cross-team coordination
- `detected_conflicts` - Conflict detection results
- `analytics_cache` - Analytics results cache

**Modified Tables:**
- `sessions` - Added `organization_id`
- `decision_retrospectives` - Added quality ratings

### Running Migrations

1. **Check current version:**
   ```bash
   poetry run alembic current
   ```

2. **Apply Phase D migration:**
   ```bash
   poetry run alembic upgrade head
   ```

3. **Verify migration:**
   ```bash
   poetry run alembic history --verbose
   ```

4. **Check for migration errors:**
   ```bash
   # Query new tables
   psql $DATABASE_URL -c "\dt decision_dependencies"
   ```

### Rollback Migration

If migration fails or Phase D needs to be rolled back:

```bash
# Rollback to Phase C
poetry run alembic downgrade 002

# Verify rollback
poetry run alembic current
```

**Warning:** Rolling back will **delete all Phase D data**. Backup first!

```bash
# Backup before rollback
pg_dump $DATABASE_URL > backup_before_rollback_$(date +%Y%m%d).sql
```

---

## Monitoring Setup

### Prometheus Configuration

1. **Start Prometheus:**
   ```bash
   cd monitoring/prometheus
   prometheus --config.file=prometheus.yml
   ```

2. **Verify scraping:**
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

3. **Load alert rules:**
   Alert rules are automatically loaded from `alerts.yml`

### Grafana Dashboard Import

1. **Access Grafana:** `http://localhost:3000`

2. **Import Phase D dashboard:**
   - Navigate to Dashboards → Import
   - Upload `monitoring/grafana/phase-d-dashboard.json`
   - Select Prometheus datasource
   - Click Import

3. **Verify panels:**
   - D1: Portfolio Analytics
   - D2: WebSocket Collaboration
   - D3: Dependency Graphs
   - D4: Pattern Analysis
   - D5: Advanced Analytics
   - D6: Cross-Team Coordination

### Key Metrics to Monitor

**Critical Metrics:**
- `tae_portfolio_query_duration_seconds` - Portfolio query latency (target <5s)
- `tae_websocket_broadcast_duration_seconds` - WebSocket broadcast (target <100ms)
- `tae_dependency_graph_timeout_errors_total` - Graph timeouts
- `tae_portfolio_health_score` - Overall organization health

**Capacity Metrics:**
- `tae_database_pool_available` - Database connections
- `tae_redis_pool_available` - Redis connections
- `tae_websocket_connections_active` - Active WebSocket connections

### Alert Configuration

Alerts are pre-configured for:
- **Critical:** Database/Redis failures, high latency
- **Warning:** Performance degradation, capacity warnings
- **Info:** Health score changes, feature usage

Configure Alertmanager for notifications (Slack, email, PagerDuty).

---

## Health Verification

### Comprehensive Health Check

Run this script after deployment:

```bash
#!/bin/bash
# health_check.sh

BASE_URL="http://localhost:8000"

echo "=== TAE Phase D Health Check ==="

# 1. Service health
echo "1. Checking service health..."
curl -s $BASE_URL/health | jq .status

# 2. Database connectivity
echo "2. Checking database..."
curl -s $BASE_URL/health | jq .dependencies.database

# 3. Redis connectivity
echo "3. Checking Redis..."
curl -s $BASE_URL/health | jq .dependencies.redis

# 4. Phase D capabilities
echo "4. Checking Phase D features..."
curl -s $BASE_URL/health | jq .phase_d_capabilities

# 5. Prometheus metrics
echo "5. Checking Prometheus metrics..."
curl -s http://localhost:9090/metrics | grep tae_portfolio

echo "=== Health Check Complete ==="
```

### Load Test (Pilot Scale)

Test with expected pilot load (15-40 users, 3-5 teams):

```bash
# Install k6 load testing tool
# brew install k6  # macOS
# apt-get install k6  # Ubuntu

# Run load test
k6 run tests/load/pilot_load_test.js
```

Expected results:
- Portfolio queries: p95 < 5s ✓
- WebSocket broadcast: p95 < 100ms ✓
- Dependency graphs: p95 < 2s ✓
- Error rate: < 1% ✓

---

## Rollback Procedures

### When to Rollback

Rollback if any of these conditions occur:
- Critical health checks failing for >5 minutes
- Database migration fails
- Performance targets not met (p95 >2x targets)
- Data corruption detected
- Pilot teams unable to access service

### Rollback Steps

1. **Stop Phase D service:**
   ```bash
   # Docker
   docker stop tae-staging

   # Direct
   pkill -f "uvicorn src.api.main"
   ```

2. **Rollback database migration:**
   ```bash
   # Backup current state first!
   pg_dump $DATABASE_URL > rollback_backup_$(date +%Y%m%d_%H%M%S).sql

   # Rollback to Phase C
   poetry run alembic downgrade 002
   ```

3. **Deploy Phase C version:**
   ```bash
   git checkout <phase-c-commit-hash>
   docker build -t tae-phase-c:1.1.0 .
   docker run -d --name tae-staging \
     --env-file .env.phase-c \
     -p 8000:8000 \
     tae-phase-c:1.1.0
   ```

4. **Verify Phase C health:**
   ```bash
   curl http://localhost:8000/health
   # Should show version 1.1.0, Phase C features
   ```

5. **Notify pilot teams:**
   - Service rolled back to Phase C
   - Phase D features temporarily unavailable
   - Timeline for re-deployment

### Post-Rollback Analysis

After rollback, investigate:
1. What triggered the rollback?
2. What were the error logs?
3. What metrics showed degradation?
4. Can the issue be fixed quickly?
5. When can Phase D be re-deployed?

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Symptom:** `failed to connect to database` in logs

**Solutions:**
```bash
# Check database is accessible
psql $DATABASE_URL -c "SELECT 1"

# Check connection pool settings
# Increase DATABASE_POOL_SIZE if exhausted
DATABASE_POOL_SIZE=30

# Check for long-running queries
psql $DATABASE_URL -c "SELECT * FROM pg_stat_activity WHERE state = 'active'"
```

#### 2. Redis Connection Errors

**Symptom:** `Redis connection failed` or WebSocket errors

**Solutions:**
```bash
# Check Redis is accessible
redis-cli -u $REDIS_URL ping

# Check Redis memory
redis-cli -u $REDIS_URL INFO memory

# Clear cache if corrupted
redis-cli -u $REDIS_URL FLUSHDB
```

#### 3. High Portfolio Query Latency

**Symptom:** `tae_portfolio_query_duration_seconds` p95 >10s

**Solutions:**
```bash
# Check database query performance
psql $DATABASE_URL -c "EXPLAIN ANALYZE SELECT * FROM sessions WHERE organization_id = 'xxx'"

# Add missing indexes
psql $DATABASE_URL -c "CREATE INDEX idx_sessions_org_id ON sessions(organization_id)"

# Increase analytics cache TTL
ANALYTICS_CACHE_TTL=600  # 10 minutes
```

#### 4. WebSocket Broadcast Failures

**Symptom:** Users not receiving real-time updates

**Solutions:**
```bash
# Check Redis pub/sub
redis-cli -u $REDIS_URL PUBSUB CHANNELS

# Check WebSocket connections
curl http://localhost:8000/health | jq .dependencies.redis

# Restart Redis
# (or increase REDIS_POOL_SIZE)
```

#### 5. Circular Dependency Detection Errors

**Symptom:** `CircularDependencyError` when adding dependencies

**Solutions:**
```bash
# This is expected behavior - dependency graphs prevent cycles
# Review dependency chain and remove conflicting dependencies

# Check dependency graph
curl $BASE_URL/api/v1/dependencies/graph?organization_id=xxx
```

### Log Analysis

**Locate logs:**
```bash
# Docker
docker logs tae-staging --tail 100 --follow

# Direct deployment
tail -f logs/tae.log
```

**Common log patterns:**
```bash
# Database errors
grep "database" logs/tae.log | tail -20

# Redis errors
grep "redis" logs/tae.log | tail -20

# Portfolio query errors
grep "portfolio_analytics_error" logs/tae.log | tail -20

# WebSocket errors
grep "websocket" logs/tae.log | tail -20
```

### Performance Profiling

If performance issues occur:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG

# Profile slow endpoints
poetry run py-spy record -o profile.svg -- \
  poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Analyze database queries
psql $DATABASE_URL -c "SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10"
```

### Getting Help

**Internal Support:**
- Tag Paul in GitHub issues
- Review Phase D documentation: `docs/PHASE_D_IMPLEMENTATION.md`
- Check pilot team feedback for common issues

**External Resources:**
- FastAPI docs: https://fastapi.tiangolo.com
- SQLAlchemy docs: https://docs.sqlalchemy.org
- Redis docs: https://redis.io/docs
- Prometheus docs: https://prometheus.io/docs

---

## Success Criteria

✅ **Deployment Successful When:**
- Health endpoint returns `status: "ok"`
- All dependencies show `"connected"`
- Prometheus metrics flowing
- Grafana dashboards displaying data
- Load test passes with p95 < targets
- Zero critical errors in 24-hour soak test

✅ **Ready for Pilot When:**
- Staging deployment successful >24 hours
- Monitoring operational
- Pilot materials complete
- Support procedures in place
- Rollback tested successfully

---

## Next Steps After Deployment

1. **Monitor for 24 hours** - Watch Grafana dashboards and alerts
2. **Review logs** - Check for any warnings or errors
3. **Run load tests** - Verify performance under pilot load
4. **Test rollback** - Ensure rollback procedure works
5. **Onboard pilot teams** - Begin pilot team selection and onboarding

---

**Questions?** Review this guide, check logs, or tag Paul in GitHub issues.

**Deployment Date:** _________________
**Deployed By:** _________________
**Production Go-Live:** _________________
