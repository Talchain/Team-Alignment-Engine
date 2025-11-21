# Load Testing for TAE Phase D

## Overview

These load tests simulate expected pilot deployment load:
- **Users:** 15-40 concurrent users
- **Teams:** 3-5 active teams
- **Decisions:** 10-20 decisions per week
- **WebSocket Messages:** 50-100 per hour

## Prerequisites

Install k6 load testing tool:

```bash
# macOS
brew install k6

# Ubuntu/Debian
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Windows
choco install k6

# Docker
docker pull grafana/k6
```

## Running Load Tests

### Pilot Load Test

Simulates expected pilot load (15-40 users):

```bash
# Run against local development
k6 run pilot_load_test.js

# Run against staging
BASE_URL=https://tae-staging.olumi.com k6 run pilot_load_test.js

# Run with custom duration
k6 run --duration 30m pilot_load_test.js

# Run with custom VUs
k6 run --vus 50 --duration 10m pilot_load_test.js
```

### Docker-based Testing

```bash
# Run with Docker
docker run --rm -i \
  -e BASE_URL=http://host.docker.internal:8000 \
  grafana/k6 run - <pilot_load_test.js

# Run with results output
docker run --rm -i \
  -v $(pwd)/results:/results \
  -e BASE_URL=http://host.docker.internal:8000 \
  grafana/k6 run --out json=/results/load_test_results.json - <pilot_load_test.js
```

## Test Scenarios

### Phase D1: Portfolio Analytics

Tests:
- `/api/v1/portfolio/analytics` - Full portfolio view
- `/api/v1/portfolio/health-score` - Lightweight health check

**Targets:**
- Portfolio analytics: p95 < 5s
- Health score: p95 < 1s
- Success rate: >99%

### Phase D2: Real-time Collaboration

*Note: WebSocket testing requires specialized tools. Use manual testing for pilot.*

**Manual WebSocket Test:**
```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c "ws://localhost:8000/api/v1/collaboration/ws/{session_id}?user_id=test-user"

# Send heartbeat
{"type": "heartbeat", "metadata": {}}

# Send action
{"type": "action", "action": {"action_type": "vote_cast", "target_id": "...", "data": {"value": "strong"}, "persist": true}}
```

### Phase D3: Decision Dependencies

Tests:
- `/api/v1/dependencies/graph` - Dependency graph retrieval

**Targets:**
- Graph query: p95 < 2s
- Success rate: >99%

### Phase D4: Organizational Patterns

Tests:
- `/api/v1/patterns` - Pattern extraction

**Targets:**
- Pattern analysis: p95 < 3s (may return 404 if insufficient data)

### Phase D5: Advanced Analytics

Tests:
- `/api/v1/advanced-analytics/trends` - Trend analysis

**Targets:**
- Trend analysis: p95 < 2s

### Phase D6: Cross-Team Coordination

Tests:
- `/api/v1/coordination/conflicts/detect` - Conflict detection

**Targets:**
- Conflict detection: p95 < 1s

## Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Portfolio Analytics p95 | <5s | >10s |
| Health Score p95 | <1s | >2s |
| Dependency Graph p95 | <2s | >5s |
| WebSocket Broadcast p95 | <100ms | >500ms |
| Pattern Analysis p95 | <3s | >10s |
| Trend Analysis p95 | <2s | >5s |
| Conflict Detection p95 | <1s | >3s |
| Error Rate | <1% | >5% |

## Interpreting Results

### Successful Test

```
✓ All checks passed!
✓ Portfolio Analytics p95: 2300ms (target < 5000ms)
✓ Dependency Graph p95: 1100ms (target < 2000ms)
✓ Error Rate: 0.2% (target < 1%)
```

**Action:** Proceed with pilot launch

### Degraded Performance

```
✗ Portfolio Analytics p95: 7200ms (target < 5000ms)
✓ Dependency Graph p95: 1100ms (target < 2000ms)
✓ Error Rate: 0.5% (target < 1%)
```

**Action:** Investigate portfolio query performance
- Check database indexes
- Review slow query logs
- Consider caching improvements

### High Error Rate

```
✓ Portfolio Analytics p95: 2300ms (target < 5000ms)
✓ Dependency Graph p95: 1100ms (target < 2000ms)
✗ Error Rate: 3.5% (target < 1%)
```

**Action:** Investigate errors
- Check application logs
- Verify database connectivity
- Check Redis connectivity
- Review error types in results JSON

## Continuous Load Testing

Run load tests:
- **Before deployment** - Ensure performance targets met
- **After deployment** - Validate staging performance
- **Weekly during pilot** - Monitor performance over time
- **After infrastructure changes** - Verify no regressions

## CI/CD Integration

Add to deployment pipeline:

```yaml
# .github/workflows/load-test.yml
name: Load Test

on:
  push:
    branches: [main, staging]

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run k6 load test
        uses: grafana/k6-action@v0.3.0
        with:
          filename: tests/load/pilot_load_test.js
        env:
          BASE_URL: ${{ secrets.STAGING_URL }}
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: pilot_load_test_results.json
```

## Troubleshooting

### Connection Refused

```
ERRO[0001] connection refused
```

**Solution:**
- Verify service is running: `curl http://localhost:8000/health`
- Check BASE_URL is correct
- Verify firewall rules

### High Error Rate

```
WARN[0030] error rate: 25%
```

**Solution:**
- Check application logs for errors
- Verify database pool size adequate
- Check Redis connection pool
- Review timeout settings

### Memory Issues

```
ERRO[0120] out of memory
```

**Solution:**
- Reduce concurrent VUs
- Increase service memory limit
- Check for memory leaks in application

## Next Steps

After successful load testing:
1. Document results in deployment log
2. Compare against previous test runs
3. Monitor Grafana dashboards during tests
4. Review Prometheus alerts triggered
5. Update performance baselines if needed

---

**Questions?** See DEPLOYMENT.md or tag Paul in GitHub issues.
