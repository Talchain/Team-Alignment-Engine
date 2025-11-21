# TAE PLoT Integration - Architectural Questions

**Date**: 2025-11-21
**Status**: Awaiting PLoT Team Review
**Related Doc**: [docs/architecture/PLOT_INTEGRATION_ARCHITECTURE.md](architecture/PLOT_INTEGRATION_ARCHITECTURE.md)

---

## Critical Questions for PLoT Team

### Q1: WebSocket Handling for Real-Time Collaboration (Phase D D2)

**Context**: TAE Phase D D2 implements real-time collaboration via WebSocket with <100ms broadcast latency. Current implementation allows direct UI → TAE WebSocket connections.

**Question**: How should WebSocket connections be handled in PLoT-orchestrated architecture?

**Options**:
- **A) Remove WebSocket, use HTTP polling**
  - UI polls PLoT every 2-5 seconds for session state
  - Simpler integration, stateless HTTP only
  - Higher latency (~2-5s vs <100ms), more PLoT load

- **B) PLoT WebSocket Proxy**
  - UI → PLoT WebSocket → TAE WebSocket
  - Maintains <100ms broadcast latency
  - More complex integration, stateful connections

- **C) Hybrid with feature flag**
  - Core deliberation uses HTTP polling (Option A)
  - Optional real-time mode uses WebSocket proxy (Option B)
  - Feature flag: `FEATURE_REALTIME_COLLABORATION_ENABLED`

**Recommendation**: **Option A** for POC v02 MVP (simpler), evaluate Option C if pilot feedback demands real-time updates.

**Impact**: Affects Phase D D2 implementation timeline and pilot user experience.

---

### Q2: Payload Size Optimization and Capability Filtering

**Context**: Full Phase D context (D1-D6 capabilities) could produce 10-50KB JSON payloads. Not all capabilities needed for every PLoT request.

**Question**: Should TAE include all Phase D data in every response, or support capability filtering?

**Options**:
- **A) Include everything, cache aggressively**
  - Every PLoT request gets full D1-D6 data
  - Rely on caching to minimize computation
  - Simple implementation, potentially wasteful

- **B) Request-specific capabilities** ✅ RECOMMENDED
  - PLoT request includes `capabilities: ["d4_patterns", "d6_conflicts"]`
  - TAE only computes requested capabilities
  - Flexible, optimized for each use case

- **C) Lazy loading with IDs**
  - Initial response includes capability IDs only
  - UI requests full details via separate calls
  - Most complex, lowest latency for initial load

**Proposed Request Schema (Option B)**:
```json
{
  "session_id": "session-123",
  "organization_id": "org-456",
  "capabilities": [
    "core_alignment",
    "d4_organizational_patterns",
    "d3_dependencies"
  ],
  "context": {
    "request_id": "plot-run-abc123"
  }
}
```

**Impact**: Affects PLoT → TAE contract design and performance.

---

### Q3: Caching Strategy Across PLoT ↔ TAE Boundary

**Context**: TAE currently caches analytics results in Redis (TTL: 5min - 4hr based on data volatility). PLoT may also want to cache TAE responses.

**Question**: Who is responsible for caching, and at what level?

**Options**:
- **A) TAE caches internally, PLoT always calls TAE** ✅ RECOMMENDED
  - TAE maintains Redis cache as currently implemented
  - PLoT makes fresh call to TAE each time
  - TAE knows data volatility best (e.g., portfolio: 5min, patterns: 1hr)

- **B) PLoT caches TAE responses, bypasses TAE cache**
  - PLoT caches entire `TaeTeamAlignmentPayload`
  - TAE becomes stateless, no Redis caching
  - Simpler TAE, but PLoT must understand data volatility

- **C) Two-level cache**
  - PLoT: Short TTL (1min) for very hot paths
  - TAE: Longer TTL (5min-4hr) for expensive queries
  - Most flexible, most complex to reason about

**Cache Invalidation Concern**: If session state changes (e.g., new vote cast), how does cache invalidate?
- TAE publishes Redis pub/sub event on state change?
- PLoT subscribes to invalidation events?
- Or rely on short TTL and eventual consistency?

**Impact**: Affects performance characteristics and consistency guarantees.

---

### Q4: Request ID Propagation and End-to-End Tracing

**Context**: TAE currently generates request IDs like `tae-validate-{option_id}`. For debugging, we need end-to-end tracing through UI → PLoT → TAE → CEE/ISL chain.

**Question**: What request ID format and propagation strategy should we use?

**Proposed Hierarchical Format**:
```
UI Request ID:    plot-run-abc123
├─ PLoT → TAE:    plot-run-abc123/tae-session-456
├─ TAE → CEE:     plot-run-abc123/tae-session-456/cee-profile-789
└─ TAE → ISL:     plot-run-abc123/tae-session-456/isl-validate-012
```

**Implementation**:
- PLoT sends `X-Request-ID: plot-run-abc123` header
- TAE appends `/tae-session-{session_id}` for its operations
- TAE propagates full chain to CEE/ISL in their `X-Request-ID` headers

**Benefits**:
- Easy to grep logs for entire request chain
- Clear hierarchy in distributed tracing (Jaeger, DataDog)
- Debugging cross-service issues becomes trivial

**Question**: Does PLoT have existing request ID format we should follow?

**Impact**: Affects logging, monitoring, and debugging across all services.

---

### Q5: Authentication Between Services (PLoT ↔ TAE)

**Context**: TAE currently uses API key auth via `X-API-Key` header (matches CEE/ISL pattern). For internal services, we could use stronger auth.

**Question**: Is API key authentication sufficient, or should we use mutual TLS?

**Options**:
- **A) API key only** (simplest)
  - PLoT sends `X-API-Key: {TAE_INTERNAL_API_KEY}` header
  - Matches existing CEE/ISL integration pattern
  - Vulnerable if internal network compromised

- **B) Mutual TLS** (most secure)
  - PLoT and TAE exchange certificates
  - Encrypted + authenticated at transport layer
  - More complex infrastructure setup

- **C) JWT with service accounts** (middle ground)
  - PLoT has service account JWT for TAE
  - Allows fine-grained permissions (e.g., read-only vs write)
  - Standard OAuth2 pattern

**Security Consideration**: Since TAE is internal-only (not internet-facing), is mutual TLS overkill for POC v02?

**Recommendation**: **Option A** for POC v02 (matches existing pattern), evaluate Option B for production.

**Impact**: Affects deployment infrastructure and security posture.

---

### Q6: Phase D Capability Prioritization for POC v02 MVP

**Context**: Phase D includes 6 major capabilities (D1-D6). Not all may be necessary for POC v02 MVP.

**Question**: Which Phase D capabilities are MUST-HAVE vs NICE-TO-HAVE for POC v02?

**Proposed Prioritization**:

**MUST HAVE** (Core TAE value):
- ✅ Session state (perspectives, options, consensus) - CORE
- ✅ Shared ground and disagreements - CORE
- ✅ Decision quality metrics (health score, risk flags) - CORE

**SHOULD HAVE** (Organizational context):
- ✅ **D4: Organizational Patterns** - Similar decisions, lessons learned
  - High value: "Teams who faced similar decisions learned..."
  - Moderate complexity: Pattern extraction from historical data
- ✅ **D3: Decision Dependencies** - Blocking/blocked sessions
  - High value: Prevent teams from making conflicting decisions
  - Low complexity: Dependency graph already implemented

**COULD HAVE** (Advanced features):
- ⚠️ **D1: Portfolio Analytics** - Executive dashboard
  - High value for leadership, but might be separate UI view
  - Question: Does Scenario Sandbox UI show portfolio view?
- ⚠️ **D5: Advanced Analytics** - Trend forecasting
  - Lower priority: Complex analytics, less immediate value
- ⚠️ **D6: Cross-Team Coordination** - Multi-team conflict detection
  - Lower priority: Requires multiple teams using system

**DEFER** (Complex integration):
- ⏸️ **D2: Real-Time Collaboration** - WebSocket (see Q1)
  - Defer to post-POC unless pilot feedback demands it

**Question**: Does PLoT/Scenario Sandbox team have prioritization preferences based on POC v02 goals?

**Impact**: Affects POC v02 scope and implementation timeline.

---

### Q7: Error Handling and Graceful Degradation

**Context**: TAE aggregates data from multiple Phase D capabilities. If D4 fails but D3 succeeds, how should PLoT handle partial data?

**Question**: What error handling semantics does PLoT expect?

**Proposed Response Schema**:
```json
{
  "requestId": "plot-run-abc123",
  "status": "partial",  // "success" | "partial" | "error"
  "taeTeamAlignment": {
    "alignment": { /* always present if session exists */ },
    "organizationalContext": {
      "similarDecisions": [ /* D4 data */ ],
      "dependencies": null,  // D3 failed
      "conflicts": [ /* D6 data */ ]
    },
    "availability": {
      "taeAvailable": true,
      "capabilities": {
        "d4_organizational_patterns": true,
        "d3_dependencies": false,  // FAILED
        "d6_cross_team_coordination": true
      },
      "degraded": true,
      "degradationReason": "D3 database timeout after 2s"
    }
  }
}
```

**Key Questions**:
- Should `status: "partial"` indicate any TAE degradation, or only if core alignment data unavailable?
- Should UI show "some features unavailable" notice to users?
- Should PLoT retry failed capabilities, or accept partial data?

**Impact**: Affects user experience when TAE has partial outages.

---

### Q8: Testing Strategy for PLoT ↔ TAE Integration

**Context**: Integration testing requires both PLoT and TAE services running. Contract testing can help verify interfaces without full integration.

**Question**: What testing approach should we use?

**Options**:
- **A) Contract testing (Pact/Spring Cloud Contract)**
  - Define PLoT ↔ TAE contract in shared spec
  - PLoT tests against TAE mock, TAE tests against PLoT mock
  - Verify contract compatibility without running both services

- **B) Integration test environment**
  - Staging environment with both PLoT and TAE deployed
  - End-to-end tests run against real services
  - More realistic, but slower and more infrastructure

- **C) Hybrid approach** ✅ RECOMMENDED
  - Contract tests for CI/CD (fast feedback)
  - Integration tests in staging (pre-deployment validation)

**Question**: Does PLoT team have existing contract testing infrastructure we should adopt?

**Impact**: Affects development velocity and deployment confidence.

---

## Non-Critical Questions (Lower Priority)

### Q9: Monitoring and Alerting Across PLoT ↔ TAE

- Should TAE emit metrics for "PLoT requests" separately from standalone requests?
- What SLOs should apply to PLoT → TAE calls? (Current target: <10s p95)
- Should alerts trigger if PLoT → TAE error rate exceeds threshold?

### Q10: Database Connection Pooling

- Does TAE need separate database connection pool for PLoT requests vs background jobs?
- What concurrency levels should we expect from PLoT? (e.g., 100 req/s?)

### Q11: Versioning Strategy

- How should TAE version its PLoT integration endpoint? (`/api/v1/plot/...` vs `/api/v2/plot/...`)
- Should payload include version fingerprint for deterministic results?

---

## Summary of Recommendations

Based on architectural analysis, here are the recommended approaches:

| Question | Recommendation | Confidence |
|----------|----------------|------------|
| Q1: WebSocket | **Option A** - HTTP polling for POC v02 | Medium (depends on pilot feedback) |
| Q2: Payload Size | **Option B** - Capability filtering | High |
| Q3: Caching | **Option A** - TAE caches internally | High |
| Q4: Request ID | Hierarchical propagation format | High |
| Q5: Authentication | **Option A** - API key (POC v02) | Medium (upgrade for production) |
| Q6: Capabilities | MUST: Core + D4 + D3; DEFER: D2 | Medium (needs PLoT team input) |
| Q7: Error Handling | Partial success with availability metadata | High |
| Q8: Testing | **Option C** - Contract + integration tests | High |

---

## Next Steps

1. **Schedule architectural review** with PLoT team
2. **Get answers to Q1-Q8** before implementation
3. **Document decisions** in `PLOT_INTEGRATION_ARCHITECTURE.md`
4. **Update implementation plan** based on decisions

---

**Document Owner**: TAE Team
**Reviewers Needed**: PLoT Team, Platform Engineering
**Target Resolution Date**: Before implementation begins (Week 1 of migration)
