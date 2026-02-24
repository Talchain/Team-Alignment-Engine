# Team Alignment Engine - API Documentation

**Version:** 1.0.0
**Base URL:** `http://localhost:8000`

---

## Overview

The Team Alignment Engine (TAE) provides a RESTful API for causally-validated team deliberation. All endpoints follow error.v1 standard for error responses and support X-Request-ID headers for tracing.

---

## Authentication

All endpoints (except health check) require JWT authentication via Bearer token:

```
Authorization: Bearer <token>
```

---

## Endpoints

### Health Check

#### GET /health

Check service health and dependency status.

**Response:**
```json
{
  "status": "ok",
  "service": "team-alignment-engine",
  "version": "1.0.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "dependencies": {
    "database": "connected",
    "redis": "connected",
    "cee": "available",
    "isl": "available"
  }
}
```

---

### Sessions

#### POST /api/v1/alignment/sessions

Create a new alignment session.

**Request:**
```json
{
  "team_id": "550e8400-e29b-41d4-a716-446655440000",
  "decision_topic": "Q2 Pricing Strategy",
  "decision_context": "Need to balance revenue growth with retention",
  "decision_type": "pricing",
  "alignment_mode": "evidence_backed",
  "stakeholders": [
    {
      "user_id": "user_001",
      "role": "owner",
      "name": "Alice",
      "email": "alice@company.com"
    }
  ],
  "created_by": "user_001"
}
```

**Response (201 Created):**
```json
{
  "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "collecting",
  "invite_links": {
    "user_001": "/join/session_id?token=invite_token_user_001"
  }
}
```

#### GET /api/v1/alignment/sessions/{session_id}

Get session status and progress.

**Response (200 OK):**
```json
{
  "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "deliberating",
  "decision_topic": "Q2 Pricing Strategy",
  "alignment_mode": "evidence_backed",
  "progress": {
    "profiles_collected": 3,
    "profiles_total": 3,
    "options_proposed": 2,
    "options_validated": 2,
    "current_phase": "deliberating"
  },
  "shared_ground": {...},
  "disagreement_map": {...}
}
```

---

### Perspectives

#### POST /api/v1/alignment/sessions/{session_id}/perspectives

Submit stakeholder perspective.

**Request:**
```json
{
  "user_id": "user_001",
  "role": "PM",
  "desired_outcome": "Increase revenue by 15% while maintaining churn below 5%",
  "key_concerns": [
    "Customer reaction to price changes",
    "Competitive positioning"
  ],
  "preferred_option": null
}
```

**Response (201 Created):**
```json
{
  "profile_id": "profile_123",
  "status": "processing",
  "session_status": "collecting"
}
```

#### GET /api/v1/alignment/sessions/{session_id}/perspectives/{profile_id}

Get extracted profile.

**Response (200 OK):**
```json
{
  "profile_id": "profile_123",
  "user_id": "user_001",
  "role": "PM",
  "raw_input": {
    "desired_outcome": "Increase revenue by 15%...",
    "key_concerns": ["Customer reaction..."],
    "preferred_option": null
  },
  "extracted_profile": {
    "goal_weights": {
      "revenue_growth": 0.9,
      "customer_retention": 0.7
    },
    "risk_tolerance": "moderate",
    "time_horizon": "quarterly",
    "must_have_constraints": [],
    "red_lines": []
  },
  "extraction_metadata": {
    "confidence": 0.85,
    "source": "cee"
  }
}
```

---

### Analysis

#### POST /api/v1/alignment/sessions/{session_id}/analyze

Generate shared ground and disagreement map.

**Response (200 OK):**
```json
{
  "shared_ground": {
    "common_goals": [
      {
        "goal": "revenue_growth",
        "agreement_score": 0.85,
        "stakeholder_weights": {...}
      }
    ],
    "common_concerns": ["customer_churn", "timeline"],
    "summary": "Team aligns on revenue growth and retention..."
  },
  "disagreement_map": {
    "primary_tensions": [
      {
        "dimension_pair": ["speed", "quality"],
        "tension_score": 0.72,
        "positions": [...]
      }
    ],
    "summary": "Primary tension: speed vs quality"
  }
}
```

---

### Options

#### POST /api/v1/alignment/sessions/{session_id}/options

Propose an option.

**Request:**
```json
{
  "proposed_by": "user_001",
  "title": "15% Price Increase with Feature Bundle",
  "description": "Increase price 15% while adding value features",
  "expected_outcome": "Revenue increase with minimal churn",
  "causal_rationale": "Price elasticity research shows...",
  "addresses_goals": ["revenue_growth"],
  "trade_offs": ["implementation_time"],
  "key_assumptions": [
    {
      "assumption_id": "assump_001",
      "assumption_text": "Price elasticity < 0.5"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "option_id": "option_456",
  "status": "validating",
  "validation_in_progress": true
}
```

#### GET /api/v1/alignment/sessions/{session_id}/options/{option_id}

Get option with fit and validation.

**Response (200 OK):**
```json
{
  "tier1_summary": {
    "option_id": "option_456",
    "title": "15% Price Increase...",
    "fit_summary": {
      "overall_alignment": 0.75,
      "consensus_level": "moderate",
      "stakeholder_fits": {...}
    },
    "validation_summary": {
      "status": "validated",
      "data_sufficiency": "sufficient",
      "key_outcomes": {
        "revenue_growth": "12.5% (range: 8% to 18%)"
      },
      "warnings": []
    }
  },
  "tier2_details": {
    "option": {...},
    "fit_analysis": {...},
    "causal_validation": {...}
  }
}
```

---

### Concerns

#### POST /api/v1/alignment/sessions/{session_id}/options/{option_id}/concerns

Flag a minority concern.

**Request:**
```json
{
  "raised_by": "user_002",
  "concern_text": "Timeline assumption unrealistic",
  "concern_type": "assumption",
  "assumption_id_tested": "assump_001",
  "request_sensitivity_test": true,
  "factor_to_test": "timeline",
  "baseline_value": 8,
  "alternative_value": 12
}
```

**Response (201 Created):**
```json
{
  "concern_id": "concern_789",
  "status": "validating",
  "sensitivity_test_initiated": true
}
```

#### GET /api/v1/alignment/sessions/{session_id}/concerns/{concern_id}

Get concern with validation results.

**Response (200 OK):**
```json
{
  "concern_id": "concern_789",
  "raised_by": "user_002",
  "concern_text": "Timeline assumption unrealistic",
  "sensitivity_result": {
    "factor_tested": "timeline",
    "baseline_outcome": 12.5,
    "alternative_outcome": 8.2,
    "outcome_delta": -4.3,
    "is_material": true,
    "explanation": "Extending timeline reduces projected revenue by 34%"
  },
  "status": "validated",
  "resolution": null
}
```

---

### Decisions

#### POST /api/v1/alignment/sessions/{session_id}/decide

Record final decision.

**Request:**
```json
{
  "decided_by": "user_001",
  "chosen_option_id": "option_456",
  "decision_rationale": "Best balance of risk and reward",
  "stakeholder_support": {
    "user_001": "strong",
    "user_002": "moderate",
    "user_003": "strong"
  },
  "accepted_assumptions": [...],
  "monitored_risks": ["Market reaction"],
  "minority_concerns_addressed": ["Timeline extended to 12 weeks"],
  "review_date": "2025-04-01T00:00:00Z",
  "success_criteria": ["Revenue +12%", "Churn <5%"],
  "monitoring_plan": ["Weekly dashboard review"]
}
```

**Response (201 Created):**
```json
{
  "brief_id": "brief_abc",
  "session_id": "session_id",
  "status": "complete",
  "decision_brief_url": "/api/v1/alignment/sessions/session_id/brief"
}
```

#### GET /api/v1/alignment/sessions/{session_id}/brief

Export decision brief.

**Response (200 OK):**
```json
{
  "brief_id": "brief_abc",
  "session_id": "session_id",
  "chosen_option": {...},
  "decision_rationale": "...",
  "consensus_strength": 0.83,
  "validated_outcomes": {...},
  "accepted_assumptions": [...],
  "minority_concerns_raised": [...],
  "minority_concerns_addressed": [...],
  "review_date": "2025-04-01T00:00:00Z",
  "success_criteria": [...],
  "monitoring_plan": [...]
}
```

---

## Error Responses

All errors follow error.v1 standard:

```json
{
  "schema": "error.v1",
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "request_id": "req_123",
  "suggested_action": "check_request_parameters"
}
```

**Common Error Codes:**
- `HTTP_400`: Bad request
- `HTTP_401`: Unauthorized
- `HTTP_403`: Forbidden
- `HTTP_404`: Not found
- `HTTP_422`: Validation error
- `HTTP_429`: Rate limit exceeded
- `HTTP_500`: Internal error

---

## Rate Limiting

- **Limit:** 100 requests per 60 seconds per IP
- **Headers:**
  - `X-Rate-Limit-Limit`: Maximum requests
  - `X-Rate-Limit-Remaining`: Remaining requests
  - `X-Rate-Limit-Reset`: Reset timestamp

---

## Request Tracing

All requests receive a unique `X-Request-ID` header for tracing through logs and errors.
