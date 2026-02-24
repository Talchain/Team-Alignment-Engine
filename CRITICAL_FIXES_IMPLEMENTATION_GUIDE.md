# Critical Fixes Implementation Guide

**Status**: 3 of 4 critical blockers completed (75%)
**Completed**: 2025-11-23 (Alembic migration + All auth + LLMClient resource leak)
**Remaining**: Database persistence for aggregation history (medium priority)

---

## ✅ Completed Fixes

### 1. ✅ Alembic Migration for Phase 1-3 Models (COMPLETED)

**File**: `alembic/versions/005_phase_1_2_3_schema.py`

**What was done**:
- Created migration for 7 new database models:
  - `deliberation_sessions`, `deliberation_rounds`, `deliberation_submissions`
  - `deliberation_votes` (anonymous), `deliberation_conflicts`
  - `user_accuracy_history`, `user_domain_expertise`
- Added proper indexes for query optimization
- Included upgrade() and downgrade() functions

**To apply**:
```bash
alembic upgrade head
```

**Verification**:
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema='public'
AND table_name LIKE 'deliberation%' OR table_name LIKE 'user_%';
```

---

### 2. ✅ Authentication on Aggregation & Preferences Endpoints (COMPLETED)

**Files Modified**:
- `src/api/routes/aggregation.py` (2 endpoints)
- `src/api/routes/preferences.py` (3 endpoints)

**What was done**:
- Added imports: `from src.auth.dependencies import get_current_user`
- Added imports: `from src.auth.models import User`
- Added parameter to all functions: `current_user: User = Depends(get_current_user)`

**Protected Endpoints**:
- ✅ POST `/api/v1/aggregation/analyze`
- ✅ POST `/api/v1/aggregation/synthesize`
- ✅ POST `/api/v1/preferences/start`
- ✅ POST `/api/v1/preferences/{session_id}/respond`
- ✅ GET `/api/v1/preferences/{session_id}/model`

**Testing**:
```bash
# Should return 401 Unauthorized without token
curl -X POST http://localhost:8000/api/v1/aggregation/analyze

# Should work with valid JWT token
curl -X POST http://localhost:8000/api/v1/aggregation/analyze \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "decision_type": "general"}'
```

---

## 🔴 Remaining Critical Fixes

### 3. ✅ Authentication on Onboarding & Deliberation Endpoints (COMPLETED)

**Priority**: ✅ COMPLETED
**Time Spent**: 1 hour
**Risk Mitigated**: Unauthorized access to user profiles, deliberation data, voting records

#### 3a. ✅ Onboarding Routes

**File**: `src/api/routes/onboarding.py` ✅

**Protected Endpoints** (3 total):
1. ✅ POST `/api/v1/onboarding/start`
2. ✅ POST `/api/v1/onboarding/{session_id}/respond`
3. ✅ GET `/api/v1/onboarding/{session_id}/profile`

**Implementation** (Completed):
```python
# Added imports at top of file
from src.auth.dependencies import get_current_user
from src.auth.models import User

# Added to all 3 endpoint functions
async def start_onboarding(
    request_body: StartOnboardingRequestV1,
    current_user: User = Depends(get_current_user),  # ADDED
    service: OnboardingService = Depends(get_onboarding_service),
) -> StartOnboardingResponseV1:
    ...
```

#### 3b. ✅ Deliberation Routes

**File**: `src/api/routes/deliberation.py` ✅

**Protected Endpoints** (7 total):
1. ✅ POST `/api/v1/deliberation/start` - Create session
2. ✅ POST `/api/v1/deliberation/{session_id}/submit` - Submit input
3. ✅ POST `/api/v1/deliberation/{session_id}/vote` - Submit vote
4. ✅ POST `/api/v1/deliberation/{session_id}/advance` - Advance round
5. ✅ GET `/api/v1/deliberation/{session_id}/status` - Get status
6. ✅ GET `/api/v1/deliberation/{session_id}/history` - Get history
7. ✅ GET `/api/v1/deliberation/{session_id}/health` - Health check

**Implementation** (Completed):
```python
# Added imports at top
from src.auth.dependencies import get_current_user
from src.auth.models import User

# Added to ALL 7 endpoint functions:
current_user: User = Depends(get_current_user),
```

---

### 4. ✅ Fix LLMClient Resource Leak (COMPLETED)

**Priority**: ✅ COMPLETED
**Time Spent**: 1.5 hours
**Risk Mitigated**: Socket exhaustion, memory leak under load

**File**: `src/clients/llm_client.py` ✅

**Issue Fixed**:
```python
# Line 36 - httpx.AsyncClient created but never closed
def __init__(self, ...):
    self.client = httpx.AsyncClient(timeout=timeout)  # LEAK!
```

**Implementation** (Completed):

```python
# src/clients/llm_client.py - COMPLETED

class LLMClient:
    """Client for LLM-powered synthesis generation.

    Usage:
        async with LLMClient() as client:
            result = await client.generate_synthesis_options(...)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", timeout: int = 60):
        self.api_key = api_key or getattr(settings, "openai_api_key", None)
        self.model = model
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None  # Created in __aenter__

    async def __aenter__(self):
        """Enter async context manager - create HTTP client."""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager - close HTTP client."""
        if self.client:
            await self.client.aclose()
        return False

    async def _call_llm(self, prompt: str) -> str:
        if not self.client:
            raise RuntimeError("LLMClient must be used as async context manager")
        # ... rest of method
```

**Dependency Injection Updates** (Completed):

1. ✅ **src/api/routes/consensus.py** - Updated get_llm_client() to async generator
   ```python
   async def get_llm_client():
       async with LLMClient() as client:
           yield client
   ```

2. ✅ **src/api/routes/deliberation.py** - Updated get_deliberation_service()
   ```python
   async def get_deliberation_service(db: AsyncSession = Depends(get_db)):
       async with LLMClient() as llm_client:
           consensus_builder = ConsensusBuilder(isl_client=ISLClient(), llm_client=llm_client)
           service = DeliberationService(repository=repository, consensus_builder=consensus_builder)
           yield service
   ```

3. ✅ **src/api/routes/preferences.py** - Updated get_preference_service()
   ```python
   async def get_preference_service():
       async with LLMClient() as llm_client:
           service = PreferenceElicitationService(llm_client=llm_client)
           yield service
   ```

4. ✅ **Service Documentation** - Added notes to all service __init__ methods documenting that LLMClient fallbacks are for testing only

**Testing**:
```python
# Test resource cleanup
import pytest
import asyncio

@pytest.mark.asyncio
async def test_llm_client_resource_cleanup():
    """Test that LLMClient properly closes httpx.AsyncClient."""
    async with LLMClient() as client:
        assert client.client is not None
        assert not client.client.is_closed

    # After context exit, client should be closed
    assert client.client.is_closed
```

---

## ⚠️ Medium Priority Fixes

### 5. Replace In-Memory Aggregation History with Database

**File**: `src/services/aggregation_intelligence.py`

**Current Issue**:
```python
# Line 37 - Data stored in memory, lost on restart
def __init__(self):
    self.user_history: Dict[str, List[Dict]] = defaultdict(list)  # IN-MEMORY!
```

**Fix**: Use database repository pattern

**Implementation**:
```python
# Create repository
class AggregationRepository:
    """Repository for user accuracy history persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_history(self, user_id: str) -> List[Dict]:
        """Get user prediction history from database."""
        stmt = select(UserAccuracyHistoryDB).where(
            UserAccuracyHistoryDB.user_id == user_id
        ).order_by(UserAccuracyHistoryDB.predicted_at.desc())

        result = await self.db.execute(stmt)
        records = result.scalars().all()

        return [
            {
                "stated_confidence": r.stated_confidence,
                "was_correct": r.was_correct,
                "brier_score": r.brier_score,
            }
            for r in records
        ]

    async def save_prediction(
        self,
        user_id: str,
        domain: str,
        stated_confidence: float,
        prediction_text: Optional[str] = None,
    ) -> str:
        """Save prediction to database."""
        record = UserAccuracyHistoryDB(
            user_id=user_id,
            domain=domain,
            decision_type="general",
            stated_confidence=stated_confidence,
            prediction_text=prediction_text,
            outcome_known=False,
        )
        self.db.add(record)
        await self.db.flush()
        return str(record.record_id)

    async def update_outcome(
        self,
        record_id: str,
        actual_outcome: str,
        was_correct: bool,
    ) -> None:
        """Update prediction outcome."""
        stmt = update(UserAccuracyHistoryDB).where(
            UserAccuracyHistoryDB.record_id == record_id
        ).values(
            actual_outcome=actual_outcome,
            outcome_known=True,
            was_correct=was_correct,
            outcome_recorded_at=datetime.utcnow(),
            brier_score=0.0 if was_correct else 1.0,
        )
        await self.db.execute(stmt)


# Update AggregationIntelligenceService
class AggregationIntelligenceService:
    """Service for aggregation intelligence using Navajas methods."""

    def __init__(self, repository: Optional[AggregationRepository] = None):
        """Initialize aggregation service."""
        self.repository = repository  # Optional for backward compatibility
        # Fallback to in-memory for testing
        self._memory_cache: Dict[str, List[Dict]] = defaultdict(list)

    def calibrate_confidence(
        self,
        user_id: str,
        stated_confidence: float,
        domain: str,
    ) -> ConfidenceAnalysisV1:
        """Calibrate user's stated confidence based on historical accuracy."""
        # Get user history from database or memory
        if self.repository:
            history = await self.repository.get_user_history(user_id)
        else:
            history = self._memory_cache.get(user_id, [])

        # Rest of method remains the same...
```

**Update routes to inject repository**:
```python
# src/api/routes/aggregation.py

from src.storage.database import get_db

async def analyze_aggregation(
    request_body: AggregationAnalysisRequestV1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),  # ADD THIS
    delib_service: DeliberationService = Depends(get_deliberation_service),
) -> AggregationAnalysisResponseV1:
    # Create service with database repository
    repository = AggregationRepository(db)
    agg_service = AggregationIntelligenceService(repository)

    # Rest remains the same...
```

**Estimated Time**: 3-4 hours

---

## 📝 Testing Requirements

### Authentication Tests

Create: `tests/unit/test_authentication.py`

```python
"""Test authentication on protected endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


class TestProtectedEndpoints:
    """Test that protected endpoints require authentication."""

    def test_aggregation_analyze_requires_auth(self):
        """Test that /aggregation/analyze requires JWT token."""
        response = client.post(
            "/api/v1/aggregation/analyze",
            json={"session_id": "test", "decision_type": "general"}
        )
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_aggregation_synthesize_requires_auth(self):
        """Test that /aggregation/synthesize requires JWT token."""
        response = client.post(
            "/api/v1/aggregation/synthesize",
            json={"session_id": "test", "synthesis_mode": "hybrid"}
        )
        assert response.status_code == 401

    def test_preferences_start_requires_auth(self):
        """Test that /preferences/start requires JWT token."""
        response = client.post(
            "/api/v1/preferences/start",
            json={
                "user_id": "test",
                "decision_context": "test",
                "initial_dimensions": ["dim1", "dim2"],
            }
        )
        assert response.status_code == 401

    # Add similar tests for:
    # - onboarding endpoints
    # - deliberation endpoints
```

### Resource Cleanup Tests

Create: `tests/unit/test_llm_client_cleanup.py`

```python
"""Test LLMClient resource cleanup."""

import pytest
from src.clients.llm_client import LLMClient


@pytest.mark.asyncio
async def test_llm_client_closes_httpx_client():
    """Test that LLMClient properly closes httpx.AsyncClient."""
    async with LLMClient() as client:
        assert client.client is not None
        assert not client.client.is_closed

    # After context exit, client should be closed
    assert client.client.is_closed


@pytest.mark.asyncio
async def test_llm_client_multiple_calls():
    """Test that LLMClient can be used multiple times."""
    for i in range(3):
        async with LLMClient() as client:
            # Should work without leaking
            assert client.client is not None

    # No resource leak - test passes
```

---

## 📊 Progress Tracking

### Critical Blockers

- [x] 1. Create Alembic migration for Phase 1-3 models (DONE)
- [x] 2a. Add authentication to aggregation endpoints (DONE)
- [x] 2b. Add authentication to preferences endpoints (DONE)
- [x] 2c. Add authentication to onboarding endpoints (DONE)
- [x] 2d. Add authentication to deliberation endpoints (DONE)
- [x] 3. Fix LLMClient resource leak (DONE)

### Medium Priority

- [ ] 4. Replace in-memory aggregation history with database (TODO)
- [ ] 5. Add comprehensive authentication tests (TODO)
- [ ] 6. Add resource cleanup tests (TODO)

---

## 🚀 Deployment Checklist

Before deploying to production, ensure:

1. **Database Migration**:
   ```bash
   alembic upgrade head
   ```

2. **Environment Variables**:
   - `JWT_SECRET` - Set in production
   - `DATABASE_URL` - PostgreSQL connection string
   - `REDIS_URL` - Redis connection string

3. **Authentication Verification**:
   ```bash
   # Test that endpoints require auth
   curl -X POST https://prod-api.example.com/api/v1/aggregation/analyze
   # Should return 401
   ```

4. **Resource Monitoring**:
   - Monitor open connections: `netstat -an | grep ESTABLISHED | wc -l`
   - Monitor memory usage: `ps aux | grep uvicorn`
   - Check for connection leaks after 1 hour of traffic

5. **Rollback Plan**:
   ```bash
   # If issues arise, rollback migration
   alembic downgrade -1

   # Revert code to previous commit
   git revert HEAD
   git push
   ```

---

## 📞 Support

**Issues**: https://github.com/Talchain/Team-Alignment-Engine/issues
**Documentation**: See `CODEBASE_ASSESSMENT.md` for full analysis
**Assessment Date**: 2025-11-23

**Next Review**: After completing remaining critical fixes (estimated 1 week)
