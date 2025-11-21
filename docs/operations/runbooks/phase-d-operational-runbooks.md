# Phase D Operational Runbooks

**Team Alignment Engine - Phase D Operations Guide**

Version: 2.0.0
Last Updated: 2025-01-31

---

## Table of Contents

1. [Scaling WebSocket Connections](#1-scaling-websocket-connections)
2. [Redis Cache Eviction & Tuning](#2-redis-cache-eviction--tuning)
3. [Portfolio Query Performance](#3-portfolio-query-performance)
4. [Dependency Graph Optimization](#4-dependency-graph-optimization)
5. [Backup & Restore Procedures](#5-backup--restore-procedures)
6. [Disaster Recovery](#6-disaster-recovery)
7. [CEE Integration Troubleshooting](#7-cee-integration-troubleshooting)
8. [Database Migration Rollback](#8-database-migration-rollback)

---

## 1. Scaling WebSocket Connections

### Problem: WebSocket Connection Limits Reached

**Symptoms**:
- New WebSocket connections fail with "max connections exceeded"
- Grafana shows `tae_websocket_connections` approaching limit (50/session)
- Alerts: `WebSocketConnectionsHigh`

**Diagnosis**:

```bash
# Check current WebSocket connections
redis-cli --scan --pattern "session:*:users" | wc -l

# Check connections per session
for key in $(redis-cli --scan --pattern "session:*:users"); do
    echo "$key: $(redis-cli SCARD $key)"
done | sort -t: -k3 -nr | head -10

# Check server metrics
curl -s http://localhost:8000/metrics | grep tae_websocket
```

**Resolution Steps**:

### Step 1: Increase Per-Session Limit (Quick Fix)

```bash
# Update environment variable
export WEBSOCKET_MAX_CONNECTIONS_PER_SESSION=100

# Restart application
kubectl rollout restart deployment/tae-api
```

### Step 2: Enable Redis Cluster for Horizontal Scaling

```yaml
# redis-cluster-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-cluster-config
data:
  redis.conf: |
    cluster-enabled yes
    cluster-config-file nodes.conf
    cluster-node-timeout 5000
    appendonly yes
```

```bash
# Deploy Redis Cluster
kubectl apply -f redis-cluster-config.yaml
helm install redis-cluster bitnami/redis-cluster --set cluster.nodes=6

# Update TAE configuration
export REDIS_URL="redis://redis-cluster:6379/0?cluster=true"
```

### Step 3: Enable Connection Pooling

```python
# Update src/storage/cache.py
from redis.asyncio import ConnectionPool

pool = ConnectionPool(
    host=settings.redis_host,
    port=settings.redis_port,
    max_connections=50,  # Increase from 20
    decode_responses=True
)
```

### Step 4: Implement Connection Shedding

```python
# src/api/routes/collaboration.py
MAX_CONNECTIONS_PER_SESSION = 50

async def collaboration_websocket(...):
    current_connections = await redis.scard(f"session:{session_id}:users")

    if current_connections >= MAX_CONNECTIONS_PER_SESSION:
        await websocket.close(code=1008, reason="Session at capacity")
        raise HTTPException(status_code=429, detail="Session at max capacity")
```

**Verification**:

```bash
# Verify connection limits increased
curl -s http://localhost:8000/health | jq '.phase_d_capabilities.d2_realtime_collaboration'

# Load test with increased connections
k6 run --vus 100 tests/load/websocket_stress_test.js
```

**Prevention**:
- Set up Grafana alerts for WebSocket connections >80% capacity
- Implement auto-scaling based on connection count
- Document connection limits in pilot onboarding

---

## 2. Redis Cache Eviction & Tuning

### Problem: High Cache Miss Rate

**Symptoms**:
- Grafana shows `tae_cache_miss_rate` >50%
- Portfolio analytics queries slow (>5s)
- Redis memory usage approaching limit
- Alerts: `CacheMissRateHigh`

**Diagnosis**:

```bash
# Check Redis memory usage
redis-cli INFO memory | grep used_memory_human

# Check cache hit rate
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses

# Check eviction policy
redis-cli CONFIG GET maxmemory-policy

# List largest keys
redis-cli --bigkeys

# Check TTLs
redis-cli --scan --pattern "portfolio:*" | head -10 | xargs -I {} redis-cli TTL {}
```

**Resolution Steps**:

### Step 1: Increase Redis Memory Limit

```bash
# Check current limit
redis-cli CONFIG GET maxmemory

# Increase to 4GB (from 2GB)
redis-cli CONFIG SET maxmemory 4gb

# Make permanent
echo "maxmemory 4gb" >> /etc/redis/redis.conf
```

### Step 2: Optimize Eviction Policy

```bash
# Set LRU eviction for volatile keys
redis-cli CONFIG SET maxmemory-policy volatile-lru

# Alternative: Allkeys LRU (evicts any key)
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Step 3: Tune Cache TTLs

```python
# src/services/portfolio_analyzer.py
# Increase TTL for stable data
PORTFOLIO_CACHE_TTL = 600  # 10 minutes (was 5)
PATTERNS_CACHE_TTL = 3600  # 1 hour
BENCHMARKS_CACHE_TTL = 14400  # 4 hours
```

### Step 4: Implement Cache Warming

```python
# src/tasks/cache_warming.py
async def warm_portfolio_cache():
    """Pre-populate cache for active organizations."""
    orgs = await db.execute(select(Organization).where(Organization.status == "active"))

    for org in orgs:
        filters = PortfolioFilters(
            organization_id=org.id,
            date_range=DateRange(
                start=datetime.utcnow() - timedelta(days=30),
                end=datetime.utcnow()
            )
        )
        # This will cache the result
        await portfolio_analyzer.generate_portfolio_view(org.id, filters)
```

```bash
# Schedule with cron
0 */6 * * * /usr/local/bin/python -m src.tasks.cache_warming
```

### Step 5: Enable Redis Persistence

```bash
# Enable RDB snapshots
redis-cli CONFIG SET save "900 1 300 10 60 10000"

# Enable AOF
redis-cli CONFIG SET appendonly yes
redis-cli CONFIG SET appendfsync everysec
```

**Verification**:

```bash
# Check improved hit rate
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses

# Calculate hit rate
echo "scale=2; $(redis-cli INFO stats | grep keyspace_hits | cut -d: -f2) / ($(redis-cli INFO stats | grep keyspace_hits | cut -d: -f2) + $(redis-cli INFO stats | grep keyspace_misses | cut -d: -f2)) * 100" | bc
```

**Prevention**:
- Monitor cache hit rate (target: >80%)
- Set up alerts for memory usage >80%
- Review cache TTLs quarterly

---

## 3. Portfolio Query Performance

### Problem: Portfolio Analytics Slow (>10s)

**Symptoms**:
- `/api/v1/portfolio/analytics` exceeds 10s p95 latency
- Database CPU usage >80%
- Alerts: `PortfolioQueryLatencyHigh`
- User complaints about slow dashboard

**Diagnosis**:

```bash
# Check current latency
curl -w "@curl-format.txt" "http://localhost:8000/api/v1/portfolio/analytics?organization_id=..."

# Check database query performance
psql -U tae_user -d tae_production -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%sessions%'
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Check index usage
psql -U tae_user -d tae_production -c "
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE tablename = 'sessions'
ORDER BY idx_scan ASC;
"

# Check slow queries
tail -f /var/log/postgresql/postgresql-15-main.log | grep "duration:"
```

**Resolution Steps**:

### Step 1: Add Missing Indexes

```sql
-- Create indexes for portfolio queries
CREATE INDEX CONCURRENTLY idx_sessions_org_date_status
ON sessions(organization_id, created_at, status);

CREATE INDEX CONCURRENTLY idx_options_session
ON options(session_id);

CREATE INDEX CONCURRENTLY idx_votes_option
ON votes(option_id);

-- Covering index for quick counts
CREATE INDEX CONCURRENTLY idx_sessions_portfolio_covering
ON sessions(organization_id, status, created_at)
INCLUDE (id, title, decision_type);
```

### Step 2: Optimize Query with CTEs

```python
# src/services/portfolio_analyzer.py
async def generate_portfolio_view(self, organization_id: UUID, filters: PortfolioFilters):
    # Use CTE for efficient aggregation
    query = text("""
        WITH session_metrics AS (
            SELECT
                s.id,
                s.title,
                s.decision_type,
                s.status,
                EXTRACT(EPOCH FROM (s.updated_at - s.created_at))/86400 AS decision_time_days,
                COUNT(DISTINCT o.id) AS option_count,
                COUNT(DISTINCT v.id) AS vote_count
            FROM sessions s
            LEFT JOIN options o ON o.session_id = s.id
            LEFT JOIN votes v ON v.option_id = o.id
            WHERE s.organization_id = :org_id
              AND s.created_at BETWEEN :start_date AND :end_date
            GROUP BY s.id
        )
        SELECT * FROM session_metrics;
    """)

    result = await self.db.execute(
        query,
        {"org_id": organization_id, "start_date": filters.date_range.start, "end_date": filters.date_range.end}
    )
```

### Step 3: Implement Pagination

```python
# src/api/routes/portfolio.py
@router.get("/analytics")
async def get_portfolio_analytics(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, le=500),
    ...
):
    # Limit query result set
    offset = (page - 1) * page_size
    # Apply LIMIT and OFFSET in SQL query
```

### Step 4: Enable Query Result Caching

```python
# Cache at service layer
cache_key = f"portfolio:{organization_id}:{start_date.isoformat()}:{end_date.isoformat()}"
cached = await redis.get(cache_key)

if cached:
    return PortfolioAnalysis.model_validate_json(cached)

# ... perform query ...

await redis.setex(cache_key, 300, result.model_dump_json())  # 5 min TTL
```

### Step 5: Scale Database with Read Replicas

```yaml
# kubernetes/postgres-replica.yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-read-replica
spec:
  selector:
    app: postgres
    role: replica
  ports:
    - port: 5432
```

```python
# Route read-only queries to replica
DATABASE_READ_URL = os.getenv("DATABASE_READ_URL", DATABASE_URL)

# Use read replica for analytics
async with AsyncSession(read_engine) as session:
    result = await session.execute(query)
```

**Verification**:

```bash
# Test improved performance
time curl "http://localhost:8000/api/v1/portfolio/analytics?organization_id=..."

# Check index usage improved
psql -c "SELECT idx_scan FROM pg_stat_user_indexes WHERE indexname = 'idx_sessions_org_date_status';"

# Load test
k6 run tests/load/portfolio_load_test.js
```

**Prevention**:
- Monitor query latency with Prometheus
- Set up query performance alerts (>5s warning, >10s critical)
- Review EXPLAIN ANALYZE quarterly
- Index unused indexes periodically

---

## 4. Dependency Graph Optimization

### Problem: Dependency Graph Construction Slow

**Symptoms**:
- `/api/v1/dependencies/graph` exceeds 5s for large organizations
- Memory usage spikes during graph construction
- Alerts: `DependencyGraphTimeout`

**Diagnosis**:

```bash
# Check graph complexity
curl "http://localhost:8000/api/v1/dependencies/graph?organization_id=..." | jq '.graph_metrics'

# Monitor memory during graph build
while true; do
    ps aux | grep uvicorn | awk '{print $6}'
    sleep 1
done

# Check database query time
psql -c "EXPLAIN ANALYZE SELECT * FROM decision_dependencies WHERE source_session_id IN (SELECT id FROM sessions WHERE organization_id = '...');"
```

**Resolution Steps**:

### Step 1: Add Dependency Indexes

```sql
CREATE INDEX CONCURRENTLY idx_deps_source_target
ON decision_dependencies(source_session_id, target_session_id);

CREATE INDEX CONCURRENTLY idx_deps_org
ON decision_dependencies(source_session_id)
WHERE resolved_at IS NULL;
```

### Step 2: Implement Graph Caching

```python
# src/services/dependency_manager.py
async def build_dependency_graph(self, organization_id: UUID):
    cache_key = f"depgraph:{organization_id}"

    # Check cache first
    cached = await redis.get(cache_key)
    if cached:
        return DependencyGraph.model_validate_json(cached)

    # Build graph
    graph = await self._construct_graph(organization_id)

    # Cache for 5 minutes
    await redis.setex(cache_key, 300, graph.model_dump_json())

    return graph
```

### Step 3: Optimize Graph Algorithms

```python
import networkx as nx

def _find_critical_path(self, graph: nx.DiGraph) -> List[UUID]:
    """Optimized critical path using DAG longest path."""
    if not nx.is_directed_acyclic_graph(graph):
        # Handle cycles separately
        return []

    # Use NetworkX optimized algorithm
    try:
        path = nx.dag_longest_path(graph, weight='weight')
        return path
    except nx.NetworkXError:
        return []
```

### Step 4: Implement Lazy Loading

```python
# Don't compute expensive metrics unless requested
@router.get("/graph")
async def get_dependency_graph(
    include_critical_path: bool = Query(False),
    include_bottlenecks: bool = Query(False),
    ...
):
    graph = await manager.build_dependency_graph(organization_id)

    if include_critical_path:
        graph.critical_path = manager.find_critical_path(graph)

    if include_bottlenecks:
        graph.bottlenecks = manager.find_bottlenecks(graph)

    return graph
```

### Step 5: Limit Graph Size

```python
# Implement pagination for large graphs
MAX_NODES = 500

if len(nodes) > MAX_NODES:
    raise HTTPException(
        status_code=400,
        detail=f"Dependency graph too large ({len(nodes)} nodes). Use date filters to reduce scope."
    )
```

**Verification**:

```bash
# Test improved performance
time curl "http://localhost:8000/api/v1/dependencies/graph?organization_id=..."

# Verify cache working
redis-cli KEYS "depgraph:*"
redis-cli TTL "depgraph:550e8400-e29b-41d4-a716-446655440000"
```

**Prevention**:
- Monitor graph complexity metrics
- Alert on graph size >500 nodes
- Educate users on dependency best practices

---

## 5. Backup & Restore Procedures

### Database Backup

**Schedule**: Daily at 02:00 UTC

```bash
#!/bin/bash
# /usr/local/bin/tae-db-backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/tae"
RETENTION_DAYS=30

# Backup database
pg_dump -h postgres -U tae_user -d tae_production -F c -f "$BACKUP_DIR/tae_$DATE.dump"

# Backup Redis (if persistence enabled)
redis-cli --rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Compress
gzip "$BACKUP_DIR/tae_$DATE.dump"

# Upload to S3
aws s3 cp "$BACKUP_DIR/tae_$DATE.dump.gz" "s3://tae-backups/postgres/"
aws s3 cp "$BACKUP_DIR/redis_$DATE.rdb" "s3://tae-backups/redis/"

# Clean old backups
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.rdb" -mtime +$RETENTION_DAYS -delete
```

```bash
# Add to crontab
0 2 * * * /usr/local/bin/tae-db-backup.sh
```

### Database Restore

```bash
#!/bin/bash
# Restore from backup

# 1. Stop application
kubectl scale deployment/tae-api --replicas=0

# 2. Download backup from S3
aws s3 cp "s3://tae-backups/postgres/tae_20250131_020000.dump.gz" /tmp/

# 3. Decompress
gunzip /tmp/tae_20250131_020000.dump.gz

# 4. Restore database
pg_restore -h postgres -U tae_user -d tae_production -c /tmp/tae_20250131_020000.dump

# 5. Restore Redis (if needed)
aws s3 cp "s3://tae-backups/redis/redis_20250131_020000.rdb" /var/lib/redis/dump.rdb
systemctl restart redis

# 6. Verify data integrity
psql -h postgres -U tae_user -d tae_production -c "SELECT COUNT(*) FROM sessions;"
redis-cli DBSIZE

# 7. Restart application
kubectl scale deployment/tae-api --replicas=3
```

### Verification

```bash
# Test restore in non-production
pg_restore -h staging-postgres -U tae_user -d tae_staging -c /tmp/tae_backup.dump

# Verify record counts match
psql -c "SELECT 'sessions', COUNT(*) FROM sessions UNION ALL SELECT 'dependencies', COUNT(*) FROM decision_dependencies;"
```

---

## 6. Disaster Recovery

### Scenario: Complete Database Loss

**RTO (Recovery Time Objective)**: 4 hours
**RPO (Recovery Point Objective)**: 24 hours (daily backups)

### Recovery Steps:

**Phase 1: Assessment (15 minutes)**

```bash
# Confirm database is unrecoverable
psql -h postgres -U tae_user -d tae_production -c "SELECT 1;"

# Check backup availability
aws s3 ls s3://tae-backups/postgres/ | tail -5

# Notify stakeholders
curl -X POST "$SLACK_WEBHOOK" -d '{"text": "🚨 TAE Database DR initiated. ETA: 4 hours"}'
```

**Phase 2: Infrastructure Provisioning (30 minutes)**

```bash
# Provision new database instance
terraform apply -target=module.postgres

# Verify connectivity
pg_isready -h new-postgres -U tae_user
```

**Phase 3: Data Restoration (2 hours)**

```bash
# Restore from latest backup
aws s3 cp s3://tae-backups/postgres/$(aws s3 ls s3://tae-backups/postgres/ | tail -1 | awk '{print $4}') /tmp/latest_backup.dump.gz

gunzip /tmp/latest_backup.dump.gz

# Restore to new database
createdb -h new-postgres -U tae_user tae_production
pg_restore -h new-postgres -U tae_user -d tae_production /tmp/latest_backup.dump

# Run migrations to bring to current schema
alembic upgrade head
```

**Phase 4: Verification (30 minutes)**

```bash
# Verify data integrity
psql -h new-postgres -U tae_user -d tae_production <<EOF
SELECT 'sessions' AS table_name, COUNT(*) AS count FROM sessions
UNION ALL SELECT 'dependencies', COUNT(*) FROM decision_dependencies
UNION ALL SELECT 'coordination_groups', COUNT(*) FROM coordination_groups;
EOF

# Smoke test API
export DATABASE_URL="postgresql://tae_user:password@new-postgres/tae_production"
python -m pytest tests/integration/test_phase_d.py

# Test portfolio analytics
curl "http://localhost:8000/api/v1/portfolio/analytics?organization_id=..."
```

**Phase 5: Cutover (1 hour)**

```bash
# Update DNS/load balancer to point to new database
kubectl set env deployment/tae-api DATABASE_URL="postgresql://tae_user:password@new-postgres/tae_production"

# Rolling restart
kubectl rollout restart deployment/tae-api

# Monitor for errors
kubectl logs -f deployment/tae-api | grep ERROR
```

**Phase 6: Post-Recovery (30 minutes)**

```bash
# Notify stakeholders
curl -X POST "$SLACK_WEBHOOK" -d '{"text": "✅ TAE Database DR complete. Service restored."}'

# Document incident
# Create post-mortem document with timeline, root cause, prevention measures
```

---

## 7. CEE Integration Troubleshooting

### Problem: CEE Service Unavailable

**Symptoms**:
- Portfolio analytics return generic insights
- Logs show "CEE connection timeout"
- Metrics show `tae_cee_errors_total` increasing

**Resolution**:

```bash
# Check CEE service status
curl -f "$CEE_BASE_URL/health" || echo "CEE down"

# Enable mock mode temporarily
kubectl set env deployment/tae-api CEE_USE_MOCK=true

# Restart to pick up mock mode
kubectl rollout restart deployment/tae-api

# Verify mock mode active
curl "http://localhost:8000/api/v1/portfolio/analytics?organization_id=..." | jq '.analysis.strategic_insights'
```

---

## 8. Database Migration Rollback

### Problem: Migration Caused Issues

**Symptoms**:
- Application fails to start after migration
- Data integrity issues
- Performance degradation

**Resolution**:

```bash
# Check current migration
alembic current

# View migration history
alembic history

# Rollback to previous version
alembic downgrade -1

# Or rollback to specific version
alembic downgrade 3cb72b9

# Verify application starts
python -m src.main

# If rollback fails, restore from backup
# See "Database Restore" section above
```

---

## Emergency Contacts

- **On-Call Engineer**: +1-555-0100 (PagerDuty)
- **Database Team**: db-team@olumi.com
- **Platform Engineering**: platform@olumi.com
- **Slack**: #tae-incidents

## Escalation Matrix

| Severity | Response Time | Escalation |
|----------|--------------|------------|
| Critical (P0) | 15 minutes | VP Engineering |
| High (P1) | 1 hour | Engineering Manager |
| Medium (P2) | 4 hours | Team Lead |
| Low (P3) | Next business day | On-Call Engineer |

---

**Document Maintained By**: Platform Engineering Team
**Last Review Date**: 2025-01-31
**Next Review Date**: 2025-04-30
