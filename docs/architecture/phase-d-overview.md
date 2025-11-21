# Phase D Architecture Overview

**Team Alignment Engine - Phase D: Organizational Intelligence**

Version: 2.0.0
Last Updated: 2025-01-31
Status: Production-Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Capability Architecture (D1-D6)](#capability-architecture-d1-d6)
4. [Technology Stack](#technology-stack)
5. [Integration Architecture](#integration-architecture)
6. [Data Flow Patterns](#data-flow-patterns)
7. [Key Design Decisions](#key-design-decisions)
8. [Performance Architecture](#performance-architecture)
9. [Security Architecture](#security-architecture)
10. [Scalability & Resilience](#scalability--resilience)

---

## Executive Summary

Phase D extends TAE from individual decision management to **enterprise-scale organizational intelligence**, enabling:

- **Portfolio-level visibility** across all organizational decisions
- **Real-time collaboration** with WebSocket-based presence and action broadcasting
- **Dependency management** with automatic circular dependency detection
- **Pattern extraction** from historical decision data
- **Predictive analytics** with trend forecasting and benchmarking
- **Cross-team coordination** with conflict detection

### Key Architectural Themes

1. **Event-Driven Architecture**: WebSocket pub/sub for real-time collaboration (D2)
2. **Graph-Based Analysis**: NetworkX-powered dependency graphs (D3)
3. **Caching Strategy**: Redis for analytics results and collaboration state
4. **Async-First Design**: AsyncIO/asyncpg for high-concurrency operations
5. **CEE Integration**: Contextual Empathy Engine for insights generation
6. **Modular Services**: Each capability (D1-D6) is independently deployable

---

## System Architecture

### High-Level Component View

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TAE Phase D - API Layer                      │
│                          (FastAPI Routers)                           │
├─────────────────────────────────────────────────────────────────────┤
│  D1: Portfolio    D2: Collab    D3: Dependencies   D4: Patterns     │
│  D5: Analytics    D6: Coordination                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Service Layer (Business Logic)                  │
├─────────────────────────────────────────────────────────────────────┤
│  PortfolioAnalyzer          CollaborationManager                     │
│  DependencyManager          PatternAnalyzer                          │
│  AdvancedAnalyticsEngine    CrossTeamCoordinator                     │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────┬──────────────────────┬──────────────────┐
│   PostgreSQL              │      Redis           │   CEE Service    │
│   (Primary Data)          │   (Cache + PubSub)   │   (Insights)     │
│   - Sessions              │   - Analytics cache  │   - Strategic    │
│   - Dependencies          │   - Presence state   │   - Patterns     │
│   - Patterns              │   - WebSocket msgs   │   - Forecasts    │
└──────────────────────────┴──────────────────────┴──────────────────┘
```

See [diagrams/phase-d-components.mmd](diagrams/phase-d-components.mmd) for interactive diagram.

### Architecture Layers

| Layer | Responsibility | Technologies |
|-------|---------------|-------------|
| **API** | HTTP/WebSocket endpoints, request validation | FastAPI, Pydantic, WebSockets |
| **Service** | Business logic, orchestration | Python async/await, NetworkX |
| **Data** | Persistence, caching, pub/sub | PostgreSQL, Redis, SQLAlchemy |
| **Integration** | CEE communication, ISL queries | httpx, async clients |
| **Monitoring** | Metrics, logging, tracing | Prometheus, Grafana, structlog |

---

## Capability Architecture (D1-D6)

### D1: Portfolio Analytics

**Purpose**: Aggregated decision metrics and organizational health analysis

**Architecture**:
```
API Layer (portfolio.py)
    ↓
PortfolioAnalyzer Service
    ├── Query Sessions (PostgreSQL)
    ├── Calculate Metrics (in-memory aggregation)
    ├── Cluster Analysis (scikit-learn)
    ├── Bottleneck Detection (rule-based)
    └── CEE Strategic Insights (async HTTP)
    ↓
Cache Results (Redis, TTL: 5 minutes)
```

**Key Components**:
- `PortfolioAnalyzer`: Orchestrates portfolio analysis
- `DateRange` filters: Optimized SQL queries with indexes
- `DecisionCluster`: TF-IDF + K-means clustering
- `DecisionBottleneck`: Heuristic-based detection (stuck >7 days, overloaded >5 sessions)
- Health score formula: `0.4 * velocity + 0.3 * quality + 0.3 * engagement`

**Performance Targets**:
- <5s for 100 sessions
- <10s for 500 sessions
- Cached for 5 minutes

**Database Queries**:
- Single query with filters and JOINs
- Indexes on `organization_id`, `created_at`, `status`
- Uses CTEs for metric calculations

See [diagrams/d1-portfolio-flow.mmd](diagrams/d1-portfolio-flow.mmd) for data flow.

---

### D2: Real-Time Collaboration

**Purpose**: WebSocket-based presence tracking and live action broadcasting

**Architecture**:
```
WebSocket Connection (/ws/{session_id})
    ↓
CollaborationManager
    ├── Track Presence → Redis SET (key: session:{id}:users, TTL: 30s)
    ├── Subscribe to Redis Pub/Sub (channel: session:{id})
    ├── Broadcast Actions → Redis PUBLISH
    └── Listen for Events → Send to WebSocket
```

**Key Components**:
- **WebSocket Protocol**: Bidirectional async communication
- **Presence Tracking**: Redis SET with 30-second expiry, refreshed by heartbeats
- **Pub/Sub Channels**: One channel per session (`session:{uuid}`)
- **Action Broadcasting**: Async message relay to all connected clients
- **Fallback HTTP Endpoints**: `/presence` and `/broadcast` for REST clients

**WebSocket Message Flow**:
1. Client connects with `user_id` query parameter
2. Server adds user to presence SET
3. Server broadcasts `presence_joined` event to channel
4. All connected clients receive event
5. Client sends heartbeat every 10s to maintain presence
6. On disconnect, server removes from SET and broadcasts `presence_left`

**Performance Targets**:
- <100ms p95 broadcast latency
- 50 concurrent connections per session
- <50ms presence update latency

**Redis Data Structures**:
```
session:{uuid}:users → SET (user_id, ...)
session:{uuid}:actions → LIST (recent 100 actions)
session:{uuid}:channel → PUB/SUB
```

**Scaling**:
- Redis Cluster for horizontal scaling
- Connection pooling (max 20 connections)
- Automatic reconnection with exponential backoff

See [diagrams/d2-websocket-flow.mmd](diagrams/d2-websocket-flow.mmd) for protocol flow.

---

### D3: Decision Dependencies

**Purpose**: Dependency graph management with circular dependency prevention

**Architecture**:
```
API Layer (dependencies.py)
    ↓
DecisionDependencyManager
    ├── Add Dependency
    │   ├── Validate Sessions Exist
    │   ├── Check for Circular Dependencies (DFS traversal)
    │   └── Insert to DB (PostgreSQL)
    ├── Build Dependency Graph
    │   ├── Query All Dependencies
    │   ├── Construct NetworkX DiGraph
    │   ├── Calculate Metrics (depth, bottlenecks)
    │   └── Find Critical Paths (longest_path algorithm)
    └── Resolve Dependency (set resolved_at timestamp)
```

**Key Components**:
- **NetworkX DiGraph**: In-memory graph representation
- **Circular Dependency Detection**: Depth-first search to detect cycles before insertion
- **Critical Path Analysis**: Longest path from root to leaf nodes
- **Bottleneck Detection**: Betweenness centrality calculation
- **Graph Metrics**: Total nodes/edges, max depth, blocked count

**Dependency Types**:
- `blocks`: Source blocked by target (hard dependency)
- `depends_on`: Source depends on target outcome (soft dependency)
- `relates_to`: Informational relationship
- `supersedes`: Source replaces target

**Performance Targets**:
- <2s to build graph for 100 decisions
- <50ms to detect circular dependencies
- <1s for critical path calculation

**Database Schema**:
```sql
CREATE TABLE decision_dependencies (
    dependency_id UUID PRIMARY KEY,
    source_session_id UUID REFERENCES sessions(id),
    target_session_id UUID REFERENCES sessions(id),
    dependency_type TEXT,
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    INDEX idx_source (source_session_id),
    INDEX idx_target (target_session_id),
    INDEX idx_resolved (resolved_at)
);
```

**Circular Dependency Algorithm**:
```python
def _has_cycle(graph, start, target):
    """DFS to detect cycle if edge added."""
    visited = set()
    stack = [target]

    while stack:
        node = stack.pop()
        if node == start:
            return True  # Cycle detected
        if node in visited:
            continue
        visited.add(node)
        stack.extend(graph.neighbors(node))

    return False
```

See [diagrams/d3-dependency-graph.mmd](diagrams/d3-dependency-graph.mmd) for graph structure.

---

### D4: Organizational Patterns

**Purpose**: Extract success/failure patterns from historical decision data

**Architecture**:
```
API Layer (patterns.py)
    ↓
PatternAnalyzer
    ├── Query Completed Sessions (last N days)
    ├── Group by Decision Type
    ├── Calculate Pattern Metrics
    │   ├── Avg Time to Decision
    │   ├── Avg Stakeholder Count
    │   ├── Avg Quality Rating
    │   └── Identify Characteristics
    ├── Classify Patterns (success/failure/neutral)
    ├── CEE Best Practices (async HTTP)
    └── Cache Results (Redis, TTL: 1 hour)
```

**Key Components**:
- **Pattern Classification**:
  - **Success**: Quality >7, Time <7 days, Satisfaction >8
  - **Failure**: Quality <6, Time >14 days, Satisfaction <6
  - **Neutral**: Between success and failure thresholds
- **Characteristic Extraction**: Rule-based heuristics
  - Team size: small (<4), medium (4-7), large (>7)
  - Timeline: rapid (<3 days), normal (3-7), extended (>7)
- **Confidence Calculation**: Based on sample size (n)
  - High (>0.8): n ≥ 10
  - Medium (0.5-0.8): 5 ≤ n < 10
  - Low (<0.5): n < 5

**Pattern Characteristics Identified**:
- Team size categories
- Decision timeline buckets
- Stakeholder engagement levels
- Evidence usage patterns
- Alignment mode preferences

**Performance Targets**:
- <3s for 90 days of history
- <5s for 180 days
- Cached for 1 hour

**Minimum Sample Size**: 3 sessions per decision type (configurable)

See [diagrams/d4-pattern-extraction.mmd](diagrams/d4-pattern-extraction.mmd) for extraction flow.

---

### D5: Advanced Analytics

**Purpose**: Trend analysis, forecasting, and comparative benchmarking

**Architecture**:
```
API Layer (analytics.py)
    ↓
AdvancedAnalyticsEngine
    ├── Trend Analysis
    │   ├── Time Series Query (PostgreSQL)
    │   ├── Linear Regression (scipy.stats)
    │   ├── Moving Averages (pandas)
    │   ├── Changepoint Detection (t-test)
    │   └── 30-Day Forecast (simple linear extrapolation)
    ├── Comparative Benchmarks
    │   ├── Group Metrics Calculation
    │   ├── Percentile Rankings
    │   ├── Outlier Detection (z-score >2)
    │   └── Industry Average Comparison
    └── Cache Results (Redis, TTL: 1 hour)
```

**Key Components**:

**Trend Analysis**:
- **Metrics Supported**: decision_time, quality_score, satisfaction_score, stakeholder_count
- **Granularity**: Weekly or monthly aggregation
- **Trend Line**: Linear regression (y = mx + b)
  - Slope: Rate of change
  - R-squared: Fit quality (0-1)
  - Direction: improving/stable/declining
- **Moving Averages**: 3-period and 6-period SMA
- **Changepoint Detection**: T-test between consecutive windows (p < 0.05)
- **Forecasting**: Linear extrapolation with 95% confidence intervals (±1.96 * std)

**Comparative Benchmarks**:
- **Comparison Dimensions**: team, decision_type, time_period
- **Percentile Rankings**: Rank groups by metric performance
- **Outlier Detection**: Z-score > 2 or < -2
- **Industry Averages**: Aggregated across all organizations (anonymized)

**Statistical Methods**:
```python
# Linear regression
slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(x, y)

# Changepoint detection
t_statistic, p_value = scipy.stats.ttest_ind(before, after)

# Confidence interval
ci = 1.96 * np.std(forecast_errors)
```

**Performance Targets**:
- Trend analysis: <2s for 90 days
- Benchmarks: <1s (cached for 4 hours)
- Minimum 30 days of data required

See [diagrams/d5-analytics-pipeline.mmd](diagrams/d5-analytics-pipeline.mmd) for processing pipeline.

---

### D6: Cross-Team Coordination

**Purpose**: Multi-team conflict detection and coordination group management

**Architecture**:
```
API Layer (coordination.py)
    ↓
CrossTeamCoordinator
    ├── Create Coordination Group
    │   ├── Link Session IDs
    │   ├── Set Coordinator
    │   └── Insert to DB
    ├── Detect Conflicts
    │   ├── Query Multiple Sessions
    │   ├── Temporal Conflict Detection (overlapping dates)
    │   ├── Resource Conflict Detection (shared stakeholders >3)
    │   ├── Dependency Conflict Detection (circular dependencies)
    │   └── Scope Conflict Detection (overlapping keywords)
    ├── Get Coordination View
    │   ├── Query Active Sessions
    │   ├── Detect Conflicts
    │   ├── Calculate Coordination Health
    │   └── CEE Recommendations
    └── Cache Results (Redis, TTL: 5 minutes)
```

**Key Components**:

**Conflict Types**:
1. **Temporal**: Overlapping timelines causing resource strain
   - Detection: Start/end date overlap + shared stakeholders
   - Severity: High if >5 overlapping days
2. **Resource**: Same stakeholders overloaded (>3 active decisions)
   - Detection: Count active sessions per stakeholder
   - Severity: High if >5 simultaneous decisions
3. **Dependency**: Circular or excessive dependency chains
   - Detection: Cycle detection + depth analysis
   - Severity: High if circular, medium if depth >3
4. **Scope**: Overlapping decision boundaries
   - Detection: TF-IDF similarity >0.7
   - Severity: Medium if >0.8 similarity

**Coordination Health Score**:
```python
health = 1.0 - (
    0.4 * high_conflicts / total_sessions +
    0.3 * medium_conflicts / total_sessions +
    0.1 * low_conflicts / total_sessions +
    0.2 * overloaded_stakeholders / total_stakeholders
)
```

**Resolution Suggestions**:
- Temporal: Stagger timelines, prioritize critical decisions
- Resource: Delegate stakeholders, reduce parallel decisions
- Dependency: Break circular dependencies, flatten hierarchy
- Scope: Merge related decisions, clarify boundaries

**Performance Targets**:
- Conflict detection: <1s for 10 decisions
- Coordination view: <2s for 50 active decisions
- Cached for 5 minutes

See [diagrams/d6-coordination-flow.mmd](diagrams/d6-coordination-flow.mmd) for coordination workflow.

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Runtime** | Python | 3.11+ | Application runtime |
| **Web Framework** | FastAPI | 0.104+ | HTTP/WebSocket API |
| **Async I/O** | asyncio | stdlib | Concurrent request handling |
| **Database** | PostgreSQL | 15+ | Primary data store |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction |
| **Cache/PubSub** | Redis | 7.0+ | Caching + WebSocket messaging |
| **Validation** | Pydantic | 2.0+ | Request/response validation |
| **Graph Analysis** | NetworkX | 3.0+ | Dependency graph algorithms |
| **Analytics** | NumPy, SciPy | Latest | Statistical analysis |
| **Monitoring** | Prometheus | Latest | Metrics collection |

### Phase D-Specific Libraries

```python
# requirements.txt (Phase D additions)
networkx==3.2          # Dependency graph analysis
scikit-learn==1.3      # Pattern clustering
scipy==1.11            # Statistical analysis
pandas==2.1            # Time series manipulation
redis[hiredis]==5.0    # High-performance Redis client
prometheus-client==0.19 # Metrics exposition
```

### Database Schema

**Phase D Tables**:
```sql
-- D3: Dependencies
CREATE TABLE decision_dependencies (
    dependency_id UUID PRIMARY KEY,
    source_session_id UUID REFERENCES sessions(id),
    target_session_id UUID REFERENCES sessions(id),
    dependency_type TEXT NOT NULL,
    description TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP NULL
);

-- D6: Coordination Groups
CREATE TABLE coordination_groups (
    group_id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    coordinator_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'active'
);

CREATE TABLE coordination_group_sessions (
    group_id UUID REFERENCES coordination_groups(group_id),
    session_id UUID REFERENCES sessions(id),
    PRIMARY KEY (group_id, session_id)
);

-- D6: Conflicts
CREATE TABLE coordination_conflicts (
    conflict_id UUID PRIMARY KEY,
    conflict_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP NULL,
    resolution TEXT NULL
);

CREATE TABLE conflict_sessions (
    conflict_id UUID REFERENCES coordination_conflicts(conflict_id),
    session_id UUID REFERENCES sessions(id),
    PRIMARY KEY (conflict_id, session_id)
);
```

---

## Integration Architecture

### CEE Integration (Phase C)

**Purpose**: Contextual Empathy Engine provides AI-generated insights for Phase D capabilities

**Integration Points**:

| Phase D Capability | CEE Service | Purpose |
|-------------------|-------------|---------|
| D1: Portfolio | Strategic Insights | Generate portfolio-level recommendations |
| D4: Patterns | Best Practices | Extract actionable best practices from patterns |
| D5: Analytics | Changepoint Analysis | Identify likely causes of metric changes |
| D6: Coordination | Resolution Suggestions | Recommend conflict resolution strategies |

**Communication Pattern**:
```python
# Async HTTP client with timeout
async def call_cee_service(prompt: str, context: dict) -> str:
    async with httpx.AsyncClient(timeout=5.0) as client:
        if settings.cee_use_mock:
            return mock_cee_response(prompt, context)

        response = await client.post(
            f"{settings.cee_base_url}/generate",
            json={"prompt": prompt, "context": context},
            headers={"Authorization": f"Bearer {settings.cee_api_key}"}
        )
        return response.json()["insight"]
```

**Mock Mode**: When `CEE_USE_MOCK=true`, Phase D uses rule-based heuristics instead of real CEE

**Error Handling**:
- Timeout: 5 seconds
- Fallback: Return generic insights if CEE unavailable
- Retry: Exponential backoff (2s, 4s, 8s)

### ISL Integration (Phase B)

**Purpose**: Information Structure Layer provides session context for Phase D analytics

**Integration Pattern**:
```python
# Query sessions via SQLAlchemy
async def get_sessions_for_analysis(
    db: AsyncSession,
    filters: PortfolioFilters
) -> List[Session]:
    query = (
        select(Session)
        .where(Session.organization_id == filters.organization_id)
        .where(Session.created_at.between(
            filters.date_range.start,
            filters.date_range.end
        ))
    )
    result = await db.execute(query)
    return result.scalars().all()
```

**Shared Models**: Phase D reuses Phase A/B models (Session, Option, Perspective, etc.)

---

## Data Flow Patterns

### Request-Response Flow (D1, D3, D4, D5, D6)

```
Client Request
    ↓
FastAPI Router (validation, authentication)
    ↓
Service Layer (business logic)
    ↓
┌──────────────┐
│ Cache Check? │ → HIT → Return Cached Result
└──────────────┘
    ↓ MISS
Database Query (PostgreSQL)
    ↓
Data Processing (aggregation, analysis)
    ↓
CEE Integration (if needed)
    ↓
Cache Result (Redis, with TTL)
    ↓
JSON Response to Client
```

### Event-Driven Flow (D2)

```
WebSocket Connection Established
    ↓
Subscribe to Redis Pub/Sub Channel
    ↓
┌─────────────────┐
│ Event Loop:     │
│ 1. Receive from │ ← Client sends message
│    WebSocket    │
│ 2. Publish to   │ → Redis PUBLISH
│    Redis        │
│ 3. Listen for   │ ← Redis subscription
│    Redis events │
│ 4. Send to      │ → Broadcast to WebSocket
│    WebSocket    │
└─────────────────┘
    ↓
Connection Closed → Unsubscribe + Remove Presence
```

### Batch Processing Flow (D4 Pattern Analysis)

```
Scheduled Job (optional) or API Request
    ↓
Query Historical Sessions (90 days)
    ↓
Group by Decision Type
    ↓
For Each Group:
    ├── Calculate Metrics
    ├── Extract Characteristics
    ├── Classify Pattern (success/failure/neutral)
    └── Generate Recommendations
    ↓
CEE Best Practices Generation
    ↓
Cache Results (1 hour TTL)
    ↓
Return to Client or Store
```

---

## Key Design Decisions

### 1. Why Redis for Collaboration State?

**Decision**: Use Redis for WebSocket presence tracking and pub/sub

**Rationale**:
- ✅ Sub-millisecond latency for presence updates
- ✅ Built-in pub/sub for event broadcasting
- ✅ Automatic expiry (SET with TTL 30s)
- ✅ Horizontal scaling with Redis Cluster
- ❌ Alternative (PostgreSQL): Too slow for real-time (<100ms requirement)

**Trade-offs**:
- Data volatility (presence lost on Redis restart) → Acceptable for ephemeral state
- Additional infrastructure → Mitigated by using Redis for caching too

### 2. Why NetworkX for Dependency Graphs?

**Decision**: Use NetworkX for in-memory graph analysis

**Rationale**:
- ✅ Rich graph algorithms (DFS, longest path, centrality)
- ✅ Optimized for < 1000 nodes (typical org size)
- ✅ Pythonic API, integrates with numpy/scipy
- ❌ Alternative (Neo4j): Overkill for current scale, adds complexity

**Trade-offs**:
- In-memory construction on each request → Mitigated by caching graph for 5 minutes
- Limited to single-server processing → Sufficient for target scale (<1000 decisions)

### 3. Why Async SQLAlchemy?

**Decision**: Use async SQLAlchemy (asyncpg) for database access

**Rationale**:
- ✅ Non-blocking I/O for high concurrency
- ✅ Connection pooling (20 connections)
- ✅ Integrates with FastAPI async views
- ❌ Alternative (sync SQLAlchemy): Blocks event loop, reduces throughput

**Performance**:
- Async: 1000 req/s with 20 connections
- Sync: 200 req/s (5x slower)

### 4. Why Cache Analytics Results?

**Decision**: Cache portfolio analytics for 5 minutes, patterns for 1 hour

**Rationale**:
- ✅ Reduces database load (expensive aggregations)
- ✅ Improves response time (<200ms cached vs 2-5s uncached)
- ✅ Acceptable staleness for analytics use cases
- ❌ Alternative (no caching): Database bottleneck under load

**Cache Strategy**:
- **Portfolio Analytics**: 5 minutes (frequently changing)
- **Patterns**: 1 hour (stable over time)
- **Benchmarks**: 4 hours (industry data changes slowly)
- **Dependency Graph**: 5 minutes (moderate change frequency)

### 5. Why Mock CEE Mode?

**Decision**: Provide `CEE_USE_MOCK` flag for development/testing

**Rationale**:
- ✅ Phase D can operate independently of CEE availability
- ✅ Faster development iteration (no CEE dependency)
- ✅ Predictable test results (no AI variability)
- ✅ Production readiness (graceful CEE degradation)

**Mock Behavior**:
- Returns generic insights based on data patterns
- Uses rule-based heuristics (e.g., "Health score >0.8 indicates strong performance")

---

## Performance Architecture

### Performance Targets (p95 latency)

| Endpoint | Target | Current | Achieved |
|----------|--------|---------|----------|
| Portfolio Analytics (100 sessions) | <5s | 2.1s | ✅ |
| Health Score | <1s | 0.4s | ✅ |
| WebSocket Broadcast | <100ms | 45ms | ✅ |
| Dependency Graph (100 decisions) | <2s | 1.3s | ✅ |
| Pattern Analysis (90 days) | <3s | 2.4s | ✅ |
| Trend Analysis (90 days) | <2s | 1.6s | ✅ |
| Benchmarks | <1s | 0.3s | ✅ |
| Coordination View (50 sessions) | <2s | 1.5s | ✅ |

### Performance Optimizations

**1. Database Query Optimization**:
```sql
-- Indexes for portfolio queries
CREATE INDEX idx_sessions_org_date ON sessions(organization_id, created_at);
CREATE INDEX idx_sessions_status ON sessions(status);

-- Covering index for quick counts
CREATE INDEX idx_sessions_org_status ON sessions(organization_id, status);

-- Index for dependency graph queries
CREATE INDEX idx_deps_resolved ON decision_dependencies(resolved_at);
```

**2. Connection Pooling**:
```python
# PostgreSQL pool
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

# Redis pool
REDIS_POOL_SIZE=20
REDIS_POOL_MAX_OVERFLOW=10
```

**3. Caching Strategy**:
```python
# Cache keys with TTL
cache_key = f"portfolio:{org_id}:{start_date}:{end_date}"
await redis.setex(cache_key, 300, json.dumps(result))  # 5 min TTL
```

**4. Async Concurrency**:
```python
# Parallel CEE calls
insights = await asyncio.gather(
    call_cee_service("strategic", context),
    call_cee_service("patterns", context),
    call_cee_service("recommendations", context),
    return_exceptions=True  # Don't fail if one call fails
)
```

### Load Testing Results (Pilot Scale: 40 users)

```
Scenario: 40 concurrent users, 15-minute test
- Portfolio Analytics: 95th percentile = 2.8s ✅
- WebSocket Connections: 40 concurrent ✅
- Broadcast Latency: 95th percentile = 62ms ✅
- Error Rate: 0.03% ✅
- Throughput: 450 req/min ✅
```

See [load testing documentation](../pilot/LOAD_TESTING.md) for details.

---

## Security Architecture

### Authentication & Authorization

**Authentication**: JWT Bearer tokens (inherited from Phases A-C)

```python
from fastapi import Depends, HTTPException
from src.auth import get_current_user

@router.get("/api/v1/portfolio/analytics")
async def get_analytics(
    current_user: User = Depends(get_current_user)
):
    if not current_user.has_permission("view_portfolio"):
        raise HTTPException(status_code=403, detail="Forbidden")
```

**Authorization Levels**:
- `view_portfolio`: Read portfolio analytics
- `manage_dependencies`: Create/modify dependencies
- `coordinate_teams`: Create coordination groups
- `admin`: Full access to all Phase D features

### Data Security

**1. SQL Injection Prevention**: Parameterized queries via SQLAlchemy
```python
# Safe (parameterized)
query = select(Session).where(Session.organization_id == org_id)

# NEVER do this:
# query = f"SELECT * FROM sessions WHERE org_id = '{org_id}'"
```

**2. WebSocket Authentication**: User ID validated before connection
```python
@router.websocket("/ws/{session_id}")
async def websocket(user_id: str = Query(...)):
    user = await validate_user(user_id)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
```

**3. Rate Limiting**: Prometheus-based rate limiting (1000 req/hour per org)

**4. Input Validation**: Pydantic models validate all inputs
```python
class AddDependencyRequest(BaseModel):
    source_session_id: UUID  # Automatically validates UUID format
    dependency_type: Literal["blocks", "depends_on", "relates_to"]  # Enum validation
```

### Secrets Management

```bash
# Environment variables (never committed)
DATABASE_URL=postgresql://user:password@localhost/tae
REDIS_URL=redis://localhost:6379/0
CEE_API_KEY=<secret>
JWT_SECRET_KEY=<secret>
```

---

## Scalability & Resilience

### Horizontal Scaling

**Stateless API Servers**: Multiple FastAPI instances behind load balancer
```
       Load Balancer
            ↓
    ┌───────┼───────┐
    ↓       ↓       ↓
  API-1   API-2   API-3  (Kubernetes pods)
    └───────┼───────┘
            ↓
      PostgreSQL / Redis
```

**Redis Cluster**: For WebSocket scaling beyond 1000 concurrent connections

**Database Read Replicas**: For analytics queries (future optimization)

### Resilience Patterns

**1. Circuit Breaker (CEE Integration)**:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_cee_service(prompt: str):
    # Automatically stops calling CEE after 5 failures
    # Resumes after 60 seconds
    pass
```

**2. Graceful Degradation**:
- CEE unavailable → Return generic insights
- Redis unavailable → Fall back to database (slower)
- WebSocket unavailable → Use HTTP polling

**3. Retry with Exponential Backoff**:
```python
for attempt in range(3):
    try:
        result = await call_external_service()
        break
    except Exception:
        await asyncio.sleep(2 ** attempt)  # 2s, 4s, 8s
```

**4. Database Connection Pooling**: Prevents connection exhaustion

**5. Request Timeouts**: All external calls timeout after 5-10 seconds

### Monitoring & Alerting

**Prometheus Metrics**:
- `tae_portfolio_query_duration_seconds` (histogram)
- `tae_websocket_broadcast_latency_seconds` (histogram)
- `tae_dependency_graph_complexity` (gauge)
- `tae_pattern_cache_hit_rate` (counter)

**Grafana Dashboards**: 17 panels covering all Phase D capabilities

**Alerts** (see [monitoring/prometheus/alerts.yml](../../monitoring/prometheus/alerts.yml)):
- Critical: Portfolio latency >10s, database down, Redis failures
- Warning: WebSocket latency >500ms, circular dependencies detected
- Capacity: Pool exhaustion, high memory usage

---

## Diagrams

All diagrams are located in [diagrams/](diagrams/) directory:

- [`phase-d-components.mmd`](diagrams/phase-d-components.mmd) - High-level component architecture
- [`d1-portfolio-flow.mmd`](diagrams/d1-portfolio-flow.mmd) - Portfolio analytics data flow
- [`d2-websocket-flow.mmd`](diagrams/d2-websocket-flow.mmd) - WebSocket protocol flow
- [`d3-dependency-graph.mmd`](diagrams/d3-dependency-graph.mmd) - Dependency graph structure
- [`d4-pattern-extraction.mmd`](diagrams/d4-pattern-extraction.mmd) - Pattern extraction flow
- [`d5-analytics-pipeline.mmd`](diagrams/d5-analytics-pipeline.mmd) - Analytics processing pipeline
- [`d6-coordination-flow.mmd`](diagrams/d6-coordination-flow.mmd) - Cross-team coordination workflow
- [`cee-integration.mmd`](diagrams/cee-integration.mmd) - CEE integration architecture

---

## References

- [Phase D API Documentation](../api/phase-d-openapi.yml) - Complete OpenAPI 3.1 specification
- [Deployment Guide](../../DEPLOYMENT.md) - Staging and production deployment procedures
- [Pilot Onboarding Guide](../pilot/PILOT_ONBOARDING_GUIDE.md) - End-user documentation
- [Monitoring Setup](../../monitoring/README.md) - Prometheus and Grafana configuration
- [Load Testing](../../tests/load/README.md) - Performance testing procedures

---

**Document Maintained By**: Platform Engineering Team
**Last Review Date**: 2025-01-31
**Next Review Date**: 2025-04-30
