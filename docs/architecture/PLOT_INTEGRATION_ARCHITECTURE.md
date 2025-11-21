# TAE PLoT Integration Architecture

**Date**: 2025-11-21
**Status**: Architectural Discovery (Action 1)
**Context**: TAE Strategic Pivot - POC v02 Integration

---

## Executive Summary

This document analyzes how TAE integrates into the PLoT (Platform Orchestration Tier) architecture, transitioning from a standalone pilot service to an internal-only component orchestrated by PLoT. This pattern mirrors the existing CEE and ISL integrations.

**Key Architectural Change**:
- **Previous**: UI → TAE (direct API access)
- **New**: UI → PLoT → TAE (orchestrated integration)

**Integration Model**: TAE becomes an internal-only service, never directly exposed to UI. All TAE data flows through PLoT's `/v1/run` response payload.

---

## 1. Integration Pattern Analysis

### 1.1 Current TAE Integration Patterns

Based on analysis of `src/clients/cee_client.py` and `src/clients/isl_client.py`, TAE currently implements robust async HTTP integration patterns:

**CEE Integration Pattern** (`src/clients/cee_client.py:70-96`):
```python
async def call_cee_service(prompt: str, context: dict) -> str:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{settings.cee_base_url}/assist/v1/extract-profile",
            json=request_payload,
            headers={
                "X-API-Key": self.api_key,
                "X-Request-ID": f"tae-profile-{seed}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()
```

**ISL Integration Pattern** (`src/clients/isl_client.py:76-106`):
```python
async def validate_option(option: Dict, outcome_metrics: List[str]) -> Dict:
    response = await self.client.post(
        f"{self.base_url}/api/v1/causal/validate",
        json=request_payload,
        headers={
            "X-API-Key": self.api_key,
            "X-Request-ID": f"tae-validate-{option_id}",
        },
        timeout=self.timeout,
    )
    # Graceful error handling with fallback
    return structured_result
```

**Common Integration Characteristics**:
- ✅ Async HTTP client (httpx)
- ✅ API key authentication via `X-API-Key` header
- ✅ Request ID propagation for tracing (`X-Request-ID`)
- ✅ Timeout configuration (CEE: 5s, ISL: configurable)
- ✅ Graceful error handling with structured fallback responses
- ✅ Comprehensive logging with structured context

### 1.2 PLoT → TAE Integration Pattern (New)

**Proposed Integration**: PLoT acts as orchestrator, making async HTTP calls to TAE endpoints

```python
# In PLoT Engine
async def call_tae_service(
    session_id: str,
    organization_id: str,
    request_context: dict
) -> TaeTeamAlignmentPayload:
    """
    Call TAE service for team alignment capabilities.

    Mirrors CEE/ISL integration pattern.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{settings.tae_base_url}/api/v1/plot/alignment-session",
            json={
                "session_id": session_id,
                "organization_id": organization_id,
                "context": request_context,
            },
            headers={
                "X-API-Key": settings.tae_api_key,
                "X-Request-ID": request_context.get("request_id"),
                "X-PLoT-Version": "v10",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )

        response.raise_for_status()
        tae_result = response.json()

        return TaeTeamAlignmentPayload(**tae_result)
```

**Key Integration Points**:
1. **New TAE Endpoint**: `/api/v1/plot/alignment-session` - PLoT-specific orchestration endpoint
2. **Authentication**: API key-based (internal service-to-service)
3. **Timeout**: 10 seconds (longer than CEE due to complex analytics)
4. **Request ID**: Propagated from PLoT for end-to-end tracing
5. **Graceful Degradation**: TAE unavailability doesn't block core scenario functionality

---

## 2. Response Payload Structure

### 2.1 PLoT `/v1/run` Response Integration

**Current PLoT Response Structure** (inferred from README architecture):
```typescript
interface PlotRunResponse {
  requestId: string;
  status: "success" | "partial" | "error";

  // CEE components (existing)
  ceeReview?: {
    insights: string[];
    concerns: string[];
    recommendations: string[];
  };

  // ISL components (existing)
  islValidation?: {
    isIdentifiable: boolean;
    predictedOutcomes: Record<string, number>;
    assumptions: Assumption[];
  };

  // TAE components (NEW)
  taeTeamAlignment?: TaeTeamAlignmentPayload;
}
```

### 2.2 Proposed `TaeTeamAlignmentPayload` Structure

Based on Phase D capabilities (D1-D6) and TAE's mission, the payload should include:

```typescript
interface TaeTeamAlignmentPayload {
  // Metadata
  sessionId: string;
  organizationId: string;
  timestamp: string;
  version: string; // e.g., "2.0.0"

  // Core alignment data
  alignment: {
    sessionState: "collecting_perspectives" | "proposing_options" | "deliberating" | "decided";
    stakeholderCount: number;
    perspectivesCollected: number;
    optionsProposed: number;
    consensusLevel: number; // 0-1 scale

    // Shared ground and disagreements
    sharedGround: {
      summary: string; // Plain-English from CEE
      commonGoalWeights: Record<string, number>; // 8 dimensions
      alignedPriorities: string[];
    };

    disagreements: {
      summary: string; // Plain-English from CEE
      axes: Array<{
        dimension: string;
        stakeholdersInvolved: string[];
        severityScore: number; // 0-1
        description: string;
      }>;
    };
  };

  // Decision quality metrics
  decisionQuality?: {
    // From D1: Portfolio Analytics
    healthScore: number; // 0-1 scale
    riskFlags: string[];

    // From Phase B: ISL integration
    causallyValidated: boolean;
    assumptionStrength: number; // 0-1 scale

    // From Phase C: Minority protection
    minorityConcerns: Array<{
      concernId: string;
      stakeholder: string;
      evidenceBased: boolean;
      addressed: boolean;
    }>;
  };

  // Organizational context (Phase D: D4, D5, D6)
  organizationalContext?: {
    // D4: Patterns
    similarDecisions: Array<{
      sessionId: string;
      outcome: "success" | "failure" | "neutral";
      similarity: number;
      keyLessons: string[];
    }>;

    // D5: Advanced analytics
    trendInsights?: {
      organizationDecisionVelocity: string; // e.g., "15% slower than 30-day avg"
      qualityTrend: "improving" | "declining" | "stable";
    };

    // D6: Cross-team coordination
    dependencies?: Array<{
      dependentSessionId: string;
      dependencyType: "blocks" | "informs" | "conflicts";
      team: string;
    }>;

    conflicts?: Array<{
      conflictingSessionId: string;
      conflictType: "temporal" | "resource" | "scope";
      severity: "low" | "medium" | "high";
      resolutionSuggestion?: string;
    }>;
  };

  // Real-time collaboration (Phase D: D2)
  collaboration?: {
    activeStakeholders: string[];
    recentActions: Array<{
      userId: string;
      actionType: "vote_cast" | "concern_raised" | "option_proposed";
      timestamp: string;
    }>;
  };

  // Availability status
  availability: {
    taeAvailable: boolean;
    capabilities: {
      d1_portfolio_analytics: boolean;
      d2_realtime_collaboration: boolean;
      d3_decision_dependencies: boolean;
      d4_organizational_patterns: boolean;
      d5_advanced_analytics: boolean;
      d6_cross_team_coordination: boolean;
    };
    degraded: boolean;
    degradationReason?: string;
  };
}
```

**Rationale for Payload Structure**:
1. **Core Alignment Data**: Essential for TAE's mission (surface disagreements, shared ground)
2. **Decision Quality Metrics**: Integrates Phase B (ISL) and Phase C (minority protection)
3. **Organizational Context**: Leverages Phase D capabilities (D4, D5, D6) for POC v02 value
4. **Graceful Degradation**: `availability` section allows partial functionality
5. **Version Fingerprinting**: `version` field enables deterministic testing

---

## 3. Integration Differences from Standalone Pilot

### 3.1 Architectural Differences

| Aspect | Standalone Pilot (OLD) | PLoT-Orchestrated (NEW) |
|--------|------------------------|-------------------------|
| **Entry Point** | Direct UI → TAE API calls | UI → PLoT → TAE (internal) |
| **Authentication** | User-facing auth (JWT, session tokens) | Service-to-service (API keys) |
| **API Surface** | Public endpoints (RESTful + WebSocket) | Internal-only orchestration endpoint |
| **WebSocket** | Direct UI WebSocket connections | WebSocket proxied through PLoT (or removed) |
| **Error Handling** | HTTP error responses to UI | Graceful degradation in PLoT payload |
| **Rate Limiting** | User-facing rate limits | Service-to-service limits (higher throughput) |
| **Deployment** | Standalone service with public DNS | Internal service (not internet-facing) |

### 3.2 Endpoint Mapping

**OLD (Standalone Pilot)**:
- `GET /api/v1/portfolio/analytics` → Direct UI call
- `WS /api/v1/collaboration/ws/{session_id}` → Direct WebSocket connection
- `POST /api/v1/dependencies` → Direct UI call

**NEW (PLoT-Orchestrated)**:
- `POST /api/v1/plot/alignment-session` → **Single orchestration endpoint**
  - Accepts session_id, organization_id, request context
  - Returns comprehensive `TaeTeamAlignmentPayload`
  - Aggregates data from D1-D6 capabilities internally

**Simplification**: Instead of 25+ public endpoints, TAE exposes a single orchestration endpoint for PLoT integration.

### 3.3 WebSocket Handling (Open Question)

**Current Phase D D2**: Real-time collaboration via WebSocket (`/api/v1/collaboration/ws/{session_id}`)

**Options for PLoT Integration**:

**Option A: Remove WebSocket** (simplest)
- Polling-based updates through PLoT `/v1/run` calls
- UI polls PLoT every 2-5 seconds for session state
- TAE still uses Redis pub/sub internally for coordination
- **Pro**: Simpler integration, stateless HTTP only
- **Con**: Higher latency (~2-5s vs <100ms), more PLoT load

**Option B: PLoT WebSocket Proxy**
- PLoT establishes WebSocket with TAE on behalf of UI
- UI connects to PLoT WebSocket, PLoT forwards to TAE
- **Pro**: Maintains <100ms broadcast latency
- **Con**: More complex integration, stateful connections

**Option C: Hybrid Approach**
- Core deliberation uses HTTP polling (Option A)
- Optional real-time mode uses WebSocket proxy (Option B)
- Feature flag: `FEATURE_REALTIME_COLLABORATION_ENABLED`
- **Pro**: Flexibility, graceful degradation
- **Con**: Maintenance of two code paths

**RECOMMENDATION**: Start with **Option A** (remove WebSocket) for POC v02 MVP, evaluate Option C if pilot feedback demands real-time updates.

---

## 4. Phase D Capabilities in PLoT Context

### 4.1 D1: Portfolio Analytics

**Integration**: PLoT requests portfolio analytics when user navigates to organizational dashboard

```python
# PLoT → TAE call
tae_response = await call_tae_service(
    session_id=None,  # Portfolio is cross-session
    organization_id="org-123",
    request_context={
        "capability": "d1_portfolio_analytics",
        "filters": {
            "start_date": "2025-01-01",
            "end_date": "2025-01-31"
        }
    }
)

# Included in PLoT response
plot_response.taeTeamAlignment.organizationalContext.portfolio = tae_response
```

**Use Case**: Executive dashboard showing decision health across organization

### 4.2 D2: Real-Time Collaboration

**Integration**: See section 3.3 (WebSocket handling)

**Use Case**: Live presence tracking during deliberation sessions (optional for POC v02)

### 4.3 D3: Decision Dependencies

**Integration**: PLoT includes dependency information when session has dependencies

```python
# TAE response includes dependencies
tae_response.organizationalContext.dependencies = [
    {
        "dependentSessionId": "session-456",
        "dependencyType": "blocks",
        "team": "Platform Team",
        "description": "Waiting for API design decision"
    }
]
```

**Use Case**: Warn users when their decision is blocked by or blocks other teams

### 4.4 D4: Organizational Patterns

**Integration**: TAE identifies similar past decisions and lessons learned

```python
# TAE response includes pattern analysis
tae_response.organizationalContext.similarDecisions = [
    {
        "sessionId": "session-789",
        "outcome": "success",
        "similarity": 0.87,
        "keyLessons": [
            "Testing assumptions early prevented rework",
            "Cross-functional alignment saved 2 weeks"
        ]
    }
]
```

**Use Case**: Show users "teams who faced similar decisions learned..."

### 4.5 D5: Advanced Analytics

**Integration**: Trend analysis and forecasting in organizational context

```python
# TAE response includes trend insights
tae_response.organizationalContext.trendInsights = {
    "organizationDecisionVelocity": "15% slower than 30-day avg",
    "qualityTrend": "improving",
    "forecast": {
        "nextQuarterDecisions": 42,
        "confidence": 0.73
    }
}
```

**Use Case**: Organizational health metrics for leadership

### 4.6 D6: Cross-Team Coordination

**Integration**: Conflict detection and resolution suggestions

```python
# TAE response includes conflicts
tae_response.organizationalContext.conflicts = [
    {
        "conflictingSessionId": "session-999",
        "conflictType": "resource",
        "severity": "high",
        "resolutionSuggestion": "Schedule coordination meeting between teams"
    }
]
```

**Use Case**: Alert teams when their decisions conflict with other teams

---

## 5. Implementation Changes Required

### 5.1 New TAE Endpoints for PLoT Integration

**Create**: `src/api/routes/plot_integration.py`

```python
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from src.models.plot import PlotAlignmentRequest, TaeTeamAlignmentPayload
from src.services.orchestration import OrchestrationService

router = APIRouter(prefix="/api/v1/plot", tags=["plot-integration"])

@router.post("/alignment-session", response_model=TaeTeamAlignmentPayload)
async def get_alignment_session(
    request: PlotAlignmentRequest,
    x_api_key: str = Header(...),
    x_request_id: Optional[str] = Header(None),
):
    """
    PLoT orchestration endpoint for TAE integration.

    Returns comprehensive team alignment payload including:
    - Current session state and consensus
    - Shared ground and disagreements
    - Decision quality metrics
    - Organizational context (patterns, dependencies, conflicts)

    This is an INTERNAL-ONLY endpoint, never exposed to UI.
    """
    # Validate API key
    if x_api_key != settings.tae_internal_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Orchestrate data from Phase D services
    orchestration_service = OrchestrationService()

    payload = await orchestration_service.build_alignment_payload(
        session_id=request.session_id,
        organization_id=request.organization_id,
        context=request.context,
        request_id=x_request_id,
    )

    return payload
```

### 5.2 OrchestrationService Implementation

**Create**: `src/services/orchestration.py`

```python
class OrchestrationService:
    """
    Orchestrates Phase D capabilities into unified PLoT payload.

    This service aggregates data from:
    - D1: Portfolio Analytics
    - D2: Real-time Collaboration (if enabled)
    - D3: Decision Dependencies
    - D4: Organizational Patterns
    - D5: Advanced Analytics
    - D6: Cross-Team Coordination
    """

    async def build_alignment_payload(
        self,
        session_id: Optional[str],
        organization_id: str,
        context: dict,
        request_id: Optional[str],
    ) -> TaeTeamAlignmentPayload:
        """Build comprehensive alignment payload for PLoT."""

        # Parallel fetch of Phase D capabilities
        results = await asyncio.gather(
            self._get_session_state(session_id) if session_id else None,
            self._get_portfolio_context(organization_id),
            self._get_patterns(organization_id, session_id),
            self._get_dependencies(session_id) if session_id else None,
            self._get_conflicts(organization_id, session_id),
            return_exceptions=True  # Graceful degradation
        )

        session_state, portfolio, patterns, dependencies, conflicts = results

        # Build payload
        payload = TaeTeamAlignmentPayload(
            sessionId=session_id,
            organizationId=organization_id,
            timestamp=datetime.utcnow().isoformat(),
            version=settings.service_version,
            alignment=self._build_alignment_data(session_state),
            decisionQuality=self._build_quality_metrics(session_state, portfolio),
            organizationalContext={
                "similarDecisions": patterns if not isinstance(patterns, Exception) else [],
                "dependencies": dependencies if not isinstance(dependencies, Exception) else [],
                "conflicts": conflicts if not isinstance(conflicts, Exception) else [],
            },
            availability=self._build_availability_status(results),
        )

        return payload
```

### 5.3 Configuration Changes

**Update**: `.env` / `src/config.py`

```bash
# PLoT Integration (NEW)
TAE_INTERNAL_API_KEY=<secret-internal-key>  # For PLoT → TAE authentication
PLOT_BASE_URL=https://plot-engine.olumi.com  # PLoT endpoint (if TAE needs to call back)

# Remove user-facing authentication (standalone pilot config)
# JWT_SECRET_KEY=<removed>  # No longer needed - TAE is internal-only

# Deployment mode
TAE_DEPLOYMENT_MODE=plot_orchestrated  # or "standalone" for backward compatibility
```

### 5.4 Deployment Architecture Changes

**OLD (Standalone)**:
```
Internet → Load Balancer → TAE Service (public endpoints)
                              ↓
                         PostgreSQL + Redis
```

**NEW (PLoT-Orchestrated)**:
```
Internet → Load Balancer → PLoT Engine
                              ↓
                         [INTERNAL NETWORK]
                              ↓
                         TAE Service (internal-only)
                              ↓
                         PostgreSQL + Redis
```

**Network Security**:
- TAE service NOT exposed to internet
- TAE only accepts connections from PLoT internal network
- Service-to-service API key authentication
- No user-facing rate limiting (PLoT handles that)

---

## 6. Migration Strategy

### 6.1 Backward Compatibility

**Approach**: Support both deployment modes during transition

```python
# src/api/main.py
if settings.tae_deployment_mode == "plot_orchestrated":
    # Only expose internal PLoT integration endpoint
    app.include_router(plot_integration.router)
else:
    # Expose all public endpoints (standalone pilot)
    app.include_router(portfolio.router)
    app.include_router(collaboration.router)
    app.include_router(dependencies.router)
    # ... etc
```

**Rationale**: Allows gradual migration without breaking standalone pilot deployments

### 6.2 Phased Rollout

**Phase 1: Internal-Only Endpoint** (Week 1)
- Implement `/api/v1/plot/alignment-session` endpoint
- Implement `OrchestrationService` aggregation
- Test with mock PLoT requests
- Deploy to staging with `TAE_DEPLOYMENT_MODE=plot_orchestrated`

**Phase 2: PLoT Integration** (Week 2)
- PLoT team implements TAE client (mirrors CEE/ISL pattern)
- Integration testing between PLoT and TAE
- Performance testing (target: <10s p95 latency)

**Phase 3: Pilot with PLoT** (Week 3)
- Update pilot materials for "TAE via Scenario Sandbox" flow
- Pilot users access TAE through Scenario Sandbox UI
- Monitor metrics, gather feedback

**Phase 4: Deprecate Standalone** (Week 4+)
- If POC v02 successful, deprecate standalone mode
- Remove public endpoints, simplify codebase

---

## 7. Architectural Questions and Concerns

### 7.1 Questions Requiring Clarification

**Q1: WebSocket Handling**
- **Question**: Should Phase D D2 (Real-Time Collaboration) use WebSocket proxy through PLoT, or migrate to HTTP polling?
- **Impact**: Affects latency (WebSocket: <100ms, Polling: 2-5s) and integration complexity
- **Recommendation**: Start with HTTP polling (simpler), add WebSocket if pilot feedback demands it

**Q2: Payload Size Optimization**
- **Question**: How much organizational context should be included in every PLoT response?
- **Concern**: Full Phase D context (D1-D6) could be large (10-50KB JSON)
- **Options**:
  - A) Include everything, cache aggressively
  - B) Request-specific capabilities (context.capabilities = ["d4_patterns", "d6_conflicts"])
  - C) Lazy loading (initial response includes IDs, UI requests details separately)
- **Recommendation**: Option B (capability-based filtering) for flexibility

**Q3: Caching Strategy Across PLoT ↔ TAE**
- **Question**: Should TAE maintain its own cache, or should PLoT cache TAE responses?
- **Current**: TAE uses Redis cache (TTL: 5min - 4hr based on data volatility)
- **Options**:
  - A) TAE caches internally, PLoT always gets fresh from TAE
  - B) PLoT caches TAE responses, bypasses TAE cache
  - C) Two-level cache (PLoT: 1min, TAE: 5min-4hr)
- **Recommendation**: Option A (TAE caches internally) - simpler, TAE knows data volatility better

**Q4: Request ID Propagation and Tracing**
- **Question**: How should request IDs flow through UI → PLoT → TAE → CEE/ISL?
- **Current**: TAE generates request IDs like `tae-validate-{option_id}`
- **Proposed**: Use PLoT request ID throughout chain for end-to-end tracing
- **Example**: `plot-run-abc123` → TAE logs as `plot-run-abc123/tae-session-456` → CEE as `plot-run-abc123/tae-session-456/cee-profile-789`
- **Recommendation**: Adopt hierarchical request ID propagation

**Q5: Authentication Between Services**
- **Question**: API key auth sufficient, or should we use mutual TLS for service-to-service?
- **Current**: API keys via `X-API-Key` header (matches CEE/ISL pattern)
- **Security Concern**: If internal network compromised, API key could be intercepted
- **Options**:
  - A) API key only (simplest, matches existing pattern)
  - B) Mutual TLS (more secure, more complex)
  - C) JWT with service accounts (middle ground)
- **Recommendation**: Option A for POC v02, evaluate Option B for production

### 7.2 Phase D Capability Prioritization for POC v02

**Not all Phase D capabilities may be needed for POC v02 MVP**. Recommend prioritizing:

**MUST HAVE (Core TAE value)**:
- ✅ Session state (perspectives, options, consensus)
- ✅ Shared ground and disagreements
- ✅ Decision quality metrics (health score, risk flags)

**SHOULD HAVE (Organizational context)**:
- ✅ D4: Organizational Patterns (similar decisions, lessons learned)
- ✅ D3: Decision Dependencies (blocking/blocked sessions)

**COULD HAVE (Advanced features)**:
- ⚠️ D1: Portfolio Analytics (executive dashboard - might be separate UI)
- ⚠️ D5: Advanced Analytics (trend forecasting - complex, lower priority)
- ⚠️ D6: Cross-Team Coordination (multi-team conflicts - complex)

**DEFER (Complex integration)**:
- ⏸️ D2: Real-Time Collaboration (WebSocket - use polling initially)

**Rationale**: Focus POC v02 on core alignment capabilities (what TAE does uniquely) + basic organizational context. Defer complex features to post-POC.

### 7.3 Concerns and Risks

**C1: Performance Impact of Aggregation**
- **Concern**: Orchestrating D1-D6 capabilities in single call could exceed 10s timeout
- **Mitigation**:
  - Use `asyncio.gather()` for parallel fetching
  - Implement capability filtering (only fetch requested capabilities)
  - Monitor p95 latency, adjust timeouts if needed

**C2: Graceful Degradation Complexity**
- **Concern**: If D4 fails but D3 succeeds, how does UI handle partial data?
- **Mitigation**:
  - `availability.capabilities` field indicates which capabilities succeeded
  - PLoT response includes `status: "partial"` when some TAE capabilities fail
  - UI shows available data with "some features unavailable" notice

**C3: Database Load from PLoT Calls**
- **Concern**: Every PLoT `/v1/run` call might trigger TAE database queries
- **Mitigation**:
  - Aggressive caching (Redis, 5min-4hr TTL)
  - Read replicas for analytics queries
  - Consider caching at PLoT layer for very hot paths

**C4: Testing Complexity**
- **Concern**: Testing PLoT ↔ TAE integration requires both services running
- **Mitigation**:
  - Mock PLoT client for TAE unit tests
  - Contract testing (Pact) to verify PLoT ↔ TAE interface
  - Integration test environment with both services

---

## 8. Next Steps

### 8.1 Immediate Actions

1. **Review this document** with PLoT team to answer architectural questions (Section 7.1)
2. **Prioritize Phase D capabilities** for POC v02 MVP (Section 7.2)
3. **Create `docs/ARCHITECTURAL_QUESTIONS.md`** with open questions flagged above

### 8.2 Implementation Tasks (Post-Review)

1. **Create orchestration endpoint** (`src/api/routes/plot_integration.py`)
2. **Implement OrchestrationService** (`src/services/orchestration.py`)
3. **Define Pydantic models** for PLoT request/response (`src/models/plot.py`)
4. **Update configuration** for PLoT deployment mode
5. **Write integration tests** with mock PLoT requests
6. **Update deployment documentation** for internal-only architecture

### 8.3 Pilot Material Updates

1. **Update Quick Start** for "TAE via Scenario Sandbox" flow
2. **Revise onboarding guide** to remove direct TAE API references
3. **Update FAQ** with POC v02 architecture explanation
4. **Adjust feedback templates** for PLoT-orchestrated experience

---

## 9. Appendix: Reference Materials

### 9.1 Existing TAE Integration Patterns

**CEE Client**: `src/clients/cee_client.py`
- 11 methods for different CEE capabilities
- Async HTTP with timeout, retry, logging
- Graceful error handling with structured fallback

**ISL Client**: `src/clients/isl_client.py`
- Causal validation and sensitivity analysis
- Graceful degradation on timeout/error
- Structured result format for TAE consumption

**Integration Diagram**: `docs/architecture/diagrams/cee-integration.mmd`
- Shows circuit breaker, timeout, retry, caching patterns
- Mock mode support for development

### 9.2 README Architecture Section

```
UI → PLoT Engine (orchestrator)
         ↓
         ├→ CEE (language understanding)
         ├→ ISL (causal validation)
         └→ TAE (deliberation orchestration)
```

This architecture diagram from `README.md:13-20` confirms TAE is positioned as a PLoT-orchestrated service alongside CEE and ISL.

---

**Document Status**: Draft for review
**Next Review**: After PLoT team feedback on architectural questions
**Estimated Implementation Time**: 2-3 weeks (phased rollout)
