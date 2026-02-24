# TAE Debugging Guide

Comprehensive guide to debugging TAE using built-in utilities and best practices.

## Table of Contents

1. [Trace ID Correlation](#trace-id-correlation)
2. [Request/Response Inspection](#requestresponse-inspection)
3. [State Snapshots](#state-snapshots)
4. [Common Error Patterns](#common-error-patterns)
5. [Performance Debugging](#performance-debugging)
6. [External Service Issues](#external-service-issues)

---

## Trace ID Correlation

Trace IDs allow you to correlate logs across distributed calls (TAE → ISL → CEE).

### Setting Trace IDs

```python
from src.utils.debug import set_trace_id, get_trace_id, get_or_create_trace_id

# Set trace ID (usually from X-Request-ID header)
set_trace_id("plot-run-abc123")

# Get current trace ID
current_id = get_trace_id()  # Returns "plot-run-abc123" or None

# Get or create new trace ID
trace_id = get_or_create_trace_id()  # Always returns a valid ID
```

### Using Trace Correlation Decorator

```python
from src.utils.debug import trace_correlation

@trace_correlation
async def validate_option(option_id: str):
    """
    All logs within this function will include trace_id automatically.
    """
    # Your code here
    pass
```

### Searching Logs by Trace ID

```bash
# If using JSON logging
grep '"trace_id":"plot-run-abc123"' app.log | jq .

# Standard format
grep "\\[plot-run-abc123\\]" app.log
```

---

## Request/Response Inspection

The `RequestInspector` class captures HTTP request/response details for debugging.

### Basic Usage

```python
from src.utils.debug import request_inspector

# Inspect outgoing request
await request_inspector.inspect_request(
    method="POST",
    url="https://isl.example.com/api/v1/causal/validate",
    headers={"X-API-Key": "secret", "Content-Type": "application/json"},
    body={"causal_graph": {...}},
    trace_id="plot-run-abc123",
)

# Inspect response
await request_inspector.inspect_response(
    status_code=200,
    headers={"Content-Type": "application/json"},
    body={"is_identifiable": True, ...},
    duration_ms=1250.5,
    trace_id="plot-run-abc123",
)

# Get inspection log for specific trace
log_entries = request_inspector.get_inspection_log(
    trace_id="plot-run-abc123",
    limit=10,
)

# Export full log to file
request_inspector.export_log("/tmp/tae-requests.json")
```

### Automatic Redaction

Sensitive headers are automatically redacted:
- `Authorization`
- `X-API-Key`
- `Cookie`
- `Password`

```python
# Input headers
{"X-API-Key": "secret-key-12345", "User-Agent": "TAE/2.0"}

# Logged as
{"X-API-Key": "***REDACTED***", "User-Agent": "TAE/2.0"}
```

### Body Truncation

Large request/response bodies are truncated to 10KB by default:

```python
inspector = RequestInspector(max_body_length=50000)  # 50KB limit
```

---

## State Snapshots

Capture application state at specific points for reproduction and debugging.

### Capturing Snapshots

```python
from src.utils.debug import state_snapshot

# Capture current state
snapshot = await state_snapshot.capture(
    snapshot_id="before-consensus-calculation",
    session_id="session-abc123",
    include_db=True,
    include_redis=True,
    metadata={"user_action": "trigger_consensus"},
)

# Snapshot structure
{
    "snapshot_id": "before-consensus-calculation",
    "trace_id": "tae-abc123",
    "timestamp": "2025-11-22T10:30:00Z",
    "session_id": "session-abc123",
    "metadata": {"user_action": "trigger_consensus"},
    "context": {"trace_id": "tae-abc123"},
    "database": {...},  # If include_db=True
    "redis": {...},     # If include_redis=True
}
```

### Retrieving Snapshots

```python
# Get specific snapshot
snapshot = state_snapshot.get_snapshot("before-consensus-calculation")

# List all snapshots
all_snapshot_ids = state_snapshot.list_snapshots()

# Export snapshot to file
state_snapshot.export_snapshot(
    "before-consensus-calculation",
    "/tmp/snapshot.json",
)
```

### Snapshot Workflow for Bug Reproduction

1. **Capture state before operation**:
   ```python
   await state_snapshot.capture(
       snapshot_id="before-bug",
       session_id=session_id,
       include_db=True,
   )
   ```

2. **Perform operation** (that triggers bug)

3. **Capture state after operation**:
   ```python
   await state_snapshot.capture(
       snapshot_id="after-bug",
       session_id=session_id,
       include_db=True,
   )
   ```

4. **Export both snapshots**:
   ```python
   state_snapshot.export_snapshot("before-bug", "/tmp/before.json")
   state_snapshot.export_snapshot("after-bug", "/tmp/after.json")
   ```

5. **Compare snapshots** to identify state changes

---

## Common Error Patterns

### 1. ISL Timeout

**Symptom**: Validation requests timeout after 30s

**Debug Steps**:
1. Check ISL service health:
   ```bash
   curl https://isl.example.com/api/v1/health
   ```

2. Enable request inspection:
   ```python
   from src.utils.debug import request_inspector

   # Inspect ISL requests
   log_entries = request_inspector.get_inspection_log(
       trace_id=trace_id,
   )
   # Check duration_ms values
   ```

3. Verify ISL configuration:
   ```bash
   tae validate-config --env production
   ```

**Resolution**:
- Increase `ISL_TIMEOUT` in environment
- Check ISL service logs for backlog
- Enable degraded mode if ISL persistently slow

### 2. Redis Connection Lost

**Symptom**: `redis.exceptions.ConnectionError`

**Debug Steps**:
1. Check Redis health:
   ```bash
   tae health-check --deep
   ```

2. Inspect Redis configuration:
   ```bash
   # Check Redis URL
   echo $REDIS_URL

   # Test connection
   redis-cli -u $REDIS_URL ping
   ```

3. Check connection pool status (if implemented):
   ```python
   from src.storage.cache import redis_client

   pool_info = await redis_client.connection_pool.get_connection_kwargs()
   ```

**Resolution**:
- Restart Redis service
- Check network connectivity
- Verify `REDIS_POOL_SIZE` and `REDIS_MAX_CONNECTIONS`
- Enable degraded mode (TAE continues without cache)

### 3. Consensus Calculation Failure

**Symptom**: Consensus level returns 0.0 or errors

**Debug Steps**:
1. Capture state snapshot:
   ```python
   await state_snapshot.capture(
       session_id=session_id,
       include_db=True,
   )
   ```

2. Check stakeholder profiles:
   ```python
   # Verify all stakeholders have profiles
   # Verify goal_weights sum correctly
   # Check for missing or invalid data
   ```

3. Enable trace correlation:
   ```python
   @trace_correlation
   async def calculate_consensus(...):
       # Function will log entry/exit with trace ID
       pass
   ```

**Resolution**:
- Ensure all stakeholders submitted profiles
- Validate goal_weights (0-1 range, sum > 0)
- Check CEE extraction quality

### 4. PLoT Integration Errors

**Symptom**: PLoT requests return 403 or 500

**Debug Steps**:
1. Verify API key:
   ```bash
   # Check environment
   echo $PLOT_INTERNAL_API_KEY | wc -c  # Should be >= 32 chars
   ```

2. Inspect incoming requests:
   ```python
   await request_inspector.inspect_request(
       method="POST",
       url="/api/v1/plot/alignment-session",
       headers=headers,
       body=request_body,
   )
   ```

3. Check X-Request-ID propagation:
   ```bash
   grep "X-Request-ID" app.log
   ```

**Resolution**:
- Verify `PLOT_INTERNAL_API_KEY` matches PLoT configuration
- Ensure X-Request-ID header is present
- Check capability filtering logic

---

## Performance Debugging

### 1. Slow Endpoints

**Identify slow endpoints**:
```bash
# Run benchmark
tae benchmark --workload standard --duration 60 --output /tmp/bench.json

# Analyze results
jq '.p95_latency_ms' /tmp/bench.json
```

**Profile specific requests**:
```python
import time
from src.utils.debug import log_with_context

start = time.time()

# Your operation
result = await some_operation()

duration_ms = (time.time() - start) * 1000

log_with_context(
    f"Operation completed in {duration_ms}ms",
    level="INFO",
    operation="some_operation",
    duration_ms=duration_ms,
)
```

### 2. Database Query Performance

**Enable SQL query logging**:
```python
# In settings.py
engine = create_async_engine(
    database_url,
    echo=True,  # Enable SQL logging
)
```

**Monitor query duration**:
```bash
# Search logs for slow queries
grep "SELECT" app.log | grep -E "[0-9]{3,}ms"
```

### 3. Memory Leaks

**Check snapshot growth**:
```python
# Clear old snapshots periodically
state_snapshot.clear_snapshots()

# Clear request inspection logs
request_inspector.clear_log()
```

---

## External Service Issues

### ISL Service Degraded

**Symptoms**:
- Timeouts
- Increased error rates
- Slow validation responses

**Debug**:
```python
# Check ISL health
from src.clients.isl_client import ISLClient

isl = ISLClient()
try:
    # Simple health check via validation
    result = await isl.validate_option(
        option=minimal_test_option,
        outcome_metrics=["test_metric"],
        time_horizon="weekly",
    )
    print("ISL Status:", result.get("validation_status"))
except Exception as e:
    print("ISL Error:", e)
```

**Resolution**:
- Switch to degraded mode (skip validation)
- Add `X-Olumi-Degraded: isl_unavailable` header
- Return `validation_status: "unavailable"`

### CEE Service Degraded

**Symptoms**:
- Profile extraction failures
- Heuristic fallback triggered
- Low extraction confidence

**Debug**:
```bash
# Check CEE configuration
tae validate-config --env production

# Look for CEE errors in logs
grep "CEE" app.log | grep -i error
```

**Resolution**:
- Use heuristic extraction as fallback
- Set `extraction_source: "heuristic"`
- Set `extraction_confidence: 0.5`

---

## Best Practices

1. **Always use trace IDs**: Set from X-Request-ID header or generate
2. **Capture snapshots before/after critical operations**
3. **Export inspection logs for incident reports**
4. **Clear debug logs periodically** to avoid memory issues
5. **Use `@trace_correlation` decorator** on key functions
6. **Log with context** instead of plain strings

## Tools Summary

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `set_trace_id()` | Set request trace ID | At request entry point |
| `@trace_correlation` | Auto-log with trace ID | Key functions |
| `request_inspector` | Capture HTTP details | Debugging integrations |
| `state_snapshot` | Capture app state | Bug reproduction |
| `format_exception_for_debugging()` | Detailed exception info | Error handlers |
| `log_with_context()` | Structured logging | Throughout codebase |

---

**Last Updated**: 2025-11-22
**Version**: 2.0.0
