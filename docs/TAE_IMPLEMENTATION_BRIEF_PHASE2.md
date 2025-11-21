# TAE Phase 2 Implementation Brief - PLoT Integration

**Date:** 21 November 2025  
**For:** Claude Code  
**Status:** 🟢 Architectural questions answered - proceed with implementation

---

## Excellent Work on Phase 1

Your architectural discovery was thorough and raised exactly the right questions. PLoT team has reviewed and provided clear decisions on all 8 questions. You're cleared to proceed with Phase 2 implementation.

---

## PLoT Team Architectural Decisions

### Q1: WebSocket Handling 🔴 → ANSWERED

**Decision:** HTTP polling only for POC v02. No WebSockets.

**Implementation:**
- D2 (Real-Time Collaboration) is **DEFERRED** to post-POC
- TAE exposes stateless HTTP API only
- Remove WebSocket infrastructure from POC v02 scope
- If session state updates needed, use HTTP polling via PLoT

### Q2: Payload Size / Capability Filtering 🔴 → ANSWERED

**Decision:** Capability-based filtering required.

**Implementation:**
```python
# PLoT request format
{
  "session_id": "sess_abc123",
  "capabilities": ["core_alignment", "d3_dependencies", "d4_patterns"]
}

# TAE returns ONLY requested capabilities
{
  "status": "success",
  "data": {
    "core_alignment": { ... },
    "d3_dependencies": { ... },
    "d4_patterns": { ... }
    # D5, D6 omitted because not requested
  }
}
```

**Action:** Update `TaeTeamAlignmentPayload` to support selective capability inclusion.

### Q3: Caching Strategy 🟡 → ANSWERED

**Decision:** TAE caches internally. PLoT does NOT add TAE cache.

**Implementation:**
- Keep current Redis caching strategy (5min-4hr TTL)
- PLoT may dedupe within single run for idempotency
- No cross-run caching in PLoT

**Action:** No changes needed - current approach approved.

### Q4: Request ID Propagation 🟡 → ANSWERED

**Decision:** Use PLoT's opaque `X-Request-Id` as canonical trace ID.

**Implementation:**
```python
# PLoT sends
headers = {"X-Request-Id": "plot-run-abc123"}

# TAE echoes same ID
response_headers = {"X-Request-Id": "plot-run-abc123"}

# TAE may add sub-ID in payload
{
  "request_id": "plot-run-abc123",  # Echo PLoT's ID
  "tae_session_id": "tae-456"       # Optional TAE-specific ID
}
```

**Action:** Update response structure to echo `X-Request-Id` header and include in payload.

### Q5: Authentication 🟢 → ANSWERED

**Decision:** API key for POC v02 (aligned with CEE/ISL).

**Implementation:**
- Add `TAE_API_KEY` environment variable
- Validate API key in orchestration endpoint
- Match CEE/ISL authentication pattern

**Action:** Add API key validation middleware to orchestration endpoint.

### Q6: Phase D Capability Prioritization 🔴 → ANSWERED

**Decision:**

**MUST-HAVE (POC v02):**
- D1: Core Alignment
- D3: Dependencies  
- D4: Patterns

**DEFER to post-POC:**
- D2: Real-Time Collaboration (no WebSocket)
- D5: Advanced Analytics (basic version acceptable)
- D6: Cross-Team Coordination (portfolio out of scope)

**Implementation Priority:**
1. Build orchestration endpoint with D1/D3/D4 only
2. Stub D2/D5/D6 with `"unavailable"` status
3. Post-POC can enable deferred capabilities

**Action:** Focus Phase 2 implementation on D1, D3, D4 only.

### Q7: Error Handling & Graceful Degradation 🟡 → ANSWERED

**Decision:** Use `status: "partial"` + `availability.capabilities` metadata.

**Implementation:**
```python
# If D4 fails but D3 succeeds
{
  "status": "partial",
  "availability": {
    "capabilities": {
      "core_alignment": "available",
      "d3_dependencies": "available", 
      "d4_patterns": "unavailable"
    }
  },
  "error": {
    "code": "TAE_D4_FAILED",
    "retryable": false,
    "suggested_action": "fail"
  },
  "data": {
    "core_alignment": { ... },
    "d3_dependencies": { ... }
    # d4_patterns omitted
  }
}
```

**PLoT behavior:**
- Never fails whole run if D1/D3 available
- Forwards status + availability to UI
- Decision result remains valid

**UI behavior:**
- Shows "Some team alignment insights temporarily unavailable"
- Greys out missing capability sections

**Action:** Implement partial failure handling in orchestration service.

### Q8: Testing Strategy 🟢 → ANSWERED

**Decision:** Hybrid approach (contract tests + staging integration).

**Implementation:**
- TAE owns contract tests for API schema
- Create golden fixtures for typical/edge cases
- Staging integration tests with PLoT
- Pin to stable fixtures for cross-team testing

**Action:** Create contract test suite with golden fixtures.

---

## Phase 2 Implementation Plan

### Milestone 1: Core Orchestration Endpoint (3-4 days)

**Create:** `POST /api/v1/plot/alignment-session`

**Features:**
1. Request validation (session_id, capabilities)
2. API key authentication
3. Capability-based routing (D1/D3/D4 only)
4. Response aggregation into `TaeTeamAlignmentPayload`
5. Request ID propagation
6. Error handling with partial status

**Files to create:**
```
src/api/routes/plot_orchestration.py       # New endpoint
src/services/orchestration_service.py      # Aggregation logic
src/models/plot_contracts.py               # Request/response models
src/middleware/api_key_auth.py             # Auth middleware
```

**Acceptance criteria:**
- ✅ Endpoint accepts capability-based requests
- ✅ Returns only requested capabilities (D1/D3/D4)
- ✅ Echoes X-Request-Id header
- ✅ API key validation works
- ✅ Partial failure handling implemented
- ✅ Response size <50KB for typical session

### Milestone 2: Capability Implementation (4-5 days)

**Implement POC v02 priority capabilities:**

**D1: Core Alignment**
- Session state summary
- Shared ground identification
- Disagreement mapping
- Alignment health score

**D3: Dependencies**
- Decision dependency graph
- Critical path identification
- Blocked decision detection

**D4: Patterns**
- Pattern recognition from session history
- Anti-pattern detection
- Organizational learning insights

**Stub deferred capabilities:**
```python
# D2, D5, D6 return unavailable status
{
  "d2_collaboration": {
    "status": "deferred",
    "message": "Real-time collaboration available post-POC"
  }
}
```

**Acceptance criteria:**
- ✅ D1/D3/D4 return real data
- ✅ D2/D5/D6 return clean unavailable stubs
- ✅ Performance targets met (<10s p95)

### Milestone 3: Contract Tests & Golden Fixtures (2-3 days)

**Create test suite:**
```
tests/contract/
  test_plot_orchestration_contract.py      # API contract tests
  fixtures/
    golden_full_response.json              # All capabilities
    golden_partial_d1d3.json               # Subset request
    golden_partial_failure.json            # D4 fails
    golden_error_response.json             # Complete failure
```

**Test scenarios:**
1. Full request (D1/D3/D4) → success
2. Partial request (D1 only) → success
3. Partial failure (D4 fails) → partial status
4. Complete failure → error response
5. Invalid API key → 401
6. Invalid capabilities → 400

**Acceptance criteria:**
- ✅ Contract tests cover all scenarios
- ✅ Golden fixtures committed
- ✅ Tests run in CI pipeline

### Milestone 4: Configuration & Deployment (2-3 days)

**Environment configuration:**
```bash
# New environment variables
TAE_DEPLOYMENT_MODE=plot_orchestrated
TAE_PLOT_API_KEY=<secret>
TAE_ORCHESTRATION_TIMEOUT=30
TAE_CAPABILITIES_ENABLED=d1,d3,d4
```

**Update deployment docs:**
- Staging deployment procedures
- Environment variable reference
- Health check verification
- Integration testing guide

**Acceptance criteria:**
- ✅ Staging deployment successful
- ✅ Health checks passing
- ✅ Integration tests with PLoT passing

---

## Implementation Details

### TaeTeamAlignmentPayload Structure (Final)

```python
class TaeTeamAlignmentPayload(BaseModel):
    """Response payload for PLoT orchestration."""
    
    # Metadata
    request_id: str                    # Echo PLoT's X-Request-Id
    tae_session_id: Optional[str]      # TAE internal session ID
    timestamp: str                     # ISO 8601
    
    # Status
    status: Literal["success", "partial", "error"]
    availability: AvailabilityMetadata
    error: Optional[ErrorDetail]
    
    # Data (capability-based)
    data: Dict[str, Any]  # Keys match requested capabilities
    
class AvailabilityMetadata(BaseModel):
    """Per-capability availability status."""
    capabilities: Dict[str, Literal["available", "unavailable", "deferred"]]
    
class ErrorDetail(BaseModel):
    """Error details for partial/complete failures."""
    code: str
    retryable: bool
    suggested_action: Literal["retry", "fix_input", "fail"]
    trace_id: Optional[str]
```

### Example Responses

**Full success (D1/D3/D4):**
```json
{
  "request_id": "plot-run-abc123",
  "tae_session_id": "tae-session-456",
  "timestamp": "2025-11-21T12:00:00Z",
  "status": "success",
  "availability": {
    "capabilities": {
      "core_alignment": "available",
      "d3_dependencies": "available",
      "d4_patterns": "available"
    }
  },
  "error": null,
  "data": {
    "core_alignment": {
      "health_score": 0.85,
      "shared_ground": ["objective_clarity", "constraint_awareness"],
      "disagreements": [...]
    },
    "d3_dependencies": {
      "critical_path": ["decision_a", "decision_b"],
      "blocked_count": 2
    },
    "d4_patterns": {
      "detected_patterns": ["analysis_paralysis", "premature_commitment"],
      "confidence": 0.72
    }
  }
}
```

**Partial failure (D4 unavailable):**
```json
{
  "request_id": "plot-run-abc123",
  "status": "partial",
  "availability": {
    "capabilities": {
      "core_alignment": "available",
      "d3_dependencies": "available",
      "d4_patterns": "unavailable"
    }
  },
  "error": {
    "code": "TAE_D4_TIMEOUT",
    "retryable": true,
    "suggested_action": "retry"
  },
  "data": {
    "core_alignment": { ... },
    "d3_dependencies": { ... }
  }
}
```

**Deferred capability:**
```json
{
  "status": "success",
  "availability": {
    "capabilities": {
      "d2_collaboration": "deferred"
    }
  },
  "data": {
    "d2_collaboration": {
      "status": "deferred",
      "message": "Real-time collaboration available post-POC",
      "estimated_availability": "POC v03"
    }
  }
}
```

---

## Integration with Existing TAE Code

### Reuse existing services:

**D1 Core Alignment:**
- `PortfolioAnalyzer` (simplified for single session)
- `SessionState` model
- Alignment calculation logic

**D3 Dependencies:**
- `DependencyGraphService`
- Graph algorithms (already implemented)
- Critical path computation

**D4 Patterns:**
- `OrganizationalPatternsService`
- Pattern detection logic
- Learning from retrospectives

### New orchestration layer:

```python
# src/services/orchestration_service.py
class OrchestrationService:
    """Aggregates Phase D capabilities for PLoT."""
    
    def __init__(self):
        self.portfolio = PortfolioAnalyzer()
        self.dependencies = DependencyGraphService()
        self.patterns = OrganizationalPatternsService()
    
    async def get_alignment_session(
        self,
        session_id: str,
        capabilities: List[str],
        request_id: str
    ) -> TaeTeamAlignmentPayload:
        """Orchestrate requested capabilities."""
        
        results = {}
        availability = {}
        errors = []
        
        # Execute requested capabilities
        if "core_alignment" in capabilities:
            try:
                results["core_alignment"] = await self._get_d1(session_id)
                availability["core_alignment"] = "available"
            except Exception as e:
                availability["core_alignment"] = "unavailable"
                errors.append(self._format_error(e, "TAE_D1_FAILED"))
        
        # Similar for D3, D4...
        
        # Determine overall status
        status = self._determine_status(availability, errors)
        
        return TaeTeamAlignmentPayload(
            request_id=request_id,
            status=status,
            availability=AvailabilityMetadata(capabilities=availability),
            error=errors[0] if errors else None,
            data=results
        )
```

---

## Testing Strategy

### Unit tests:
```python
# tests/unit/test_orchestration_service.py
def test_full_capabilities_success():
    """Test successful D1+D3+D4 orchestration."""
    
def test_partial_capability_request():
    """Test requesting only D1+D3."""
    
def test_partial_failure_d4():
    """Test D4 failure with D1+D3 success."""
    
def test_deferred_capability():
    """Test requesting D2 (deferred)."""
```

### Contract tests:
```python
# tests/contract/test_plot_orchestration_contract.py
def test_response_schema_matches_contract():
    """Validate response matches TaeTeamAlignmentPayload schema."""
    
def test_golden_fixtures_match_schema():
    """Validate all golden fixtures are valid."""
```

### Integration tests:
```python
# tests/integration/test_plot_integration.py
@pytest.mark.integration
async def test_orchestration_endpoint_with_redis():
    """Test full endpoint with real Redis cache."""
```

---

## Timeline

**Week 1 (22-26 Nov):**
- Days 1-2: Milestone 1 (Core endpoint)
- Days 3-4: Milestone 2 start (D1/D3 implementation)
- Day 5: Milestone 2 continue (D4 implementation)

**Week 2 (29 Nov - 3 Dec):**
- Days 1-2: Milestone 2 complete (D4 + stubs)
- Days 3-4: Milestone 3 (Contract tests + fixtures)
- Day 5: Milestone 4 start (Configuration)

**Week 3 (4-6 Dec):**
- Days 1-2: Milestone 4 complete (Deployment)
- Day 3: Integration testing with PLoT
- Days 4-5: Bug fixes and refinement

**Target:** POC v02-ready TAE by 6 Dec

---

## Success Criteria

**Phase 2 complete when:**
- ✅ POST /api/v1/plot/alignment-session endpoint live
- ✅ D1/D3/D4 capabilities implemented and tested
- ✅ D2/D5/D6 cleanly stubbed as deferred
- ✅ Contract tests passing with golden fixtures
- ✅ Staging deployment successful
- ✅ Integration tests with PLoT passing
- ✅ Performance <10s p95 latency
- ✅ Documentation updated for POC v02

---

## Key Reminders

**What's approved:**
✅ HTTP only (no WebSockets)
✅ Capability-based filtering
✅ D1/D3/D4 only for POC v02
✅ API key authentication
✅ Partial failure handling
✅ Internal caching (current approach)

**What's deferred:**
❌ D2 real-time collaboration (WebSocket)
❌ D5 advanced analytics (beyond basic)
❌ D6 portfolio/cross-team coordination

**What to escalate:**
- Integration issues with PLoT team
- Performance problems (<10s target)
- Schema mismatches in contract tests
- Capability implementation blockers

---

## Next Steps

1. **Today:** Begin Milestone 1 (orchestration endpoint scaffolding)
2. **Tomorrow:** Complete endpoint + API key auth
3. **This week:** Implement D1/D3/D4 capabilities
4. **Next week:** Contract tests + deployment
5. **Week 3:** Integration testing + refinement

**Report progress daily in commit messages. Flag blockers immediately.**

---

**You're cleared to proceed. Begin with Milestone 1. 🚀**
