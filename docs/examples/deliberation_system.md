# Multi-Round Deliberation System - API Guide

## Overview

The Multi-Round Deliberation System implements science-backed iterative consensus building with:

- **Anonymous Voting**: Votes remain encrypted during active rounds
- **Quality-Based Convergence**: Prevents mediocre compromise through causal validation
- **Minority Protection**: Flags positions with superior evidence
- **Iterative Refinement**: Multiple rounds until quality threshold met

**Scientific Foundation:**
- Habermas Machine (Science 2024): AI-mediated deliberation achieves 40% faster alignment
- FACET (SIGMOD 2024): Robust counterfactual generation with confidence intervals

---

## Quick Start

### Complete Deliberation Flow

```python
import httpx

client = httpx.AsyncClient(base_url="https://api.tae.example.com")

# 1. Start Session
session = await client.post("/api/v1/deliberation/start", json={
    "decision_context": "Should we raise prices by 30%?",
    "participants": ["pm_001", "engineer_002", "designer_003"],
    "convergence_criteria": {
        "min_quality_score": 0.7,
        "max_rounds": 5,
        "min_agreement": 0.6
    }
})
session_id = session.json()["session_id"]
round_1_id = session.json()["round_id"]

# 2. Round 1: Submit Perspectives
for participant in participants:
    await client.post(f"/api/v1/deliberation/{session_id}/submit", json={
        "user_id": participant["id"],
        "round_id": round_1_id,
        "graph": participant["causal_graph"],
        "reasoning": participant["reasoning"]
    })

# 3. Advance to Synthesis
response = await client.post(f"/api/v1/deliberation/{session_id}/advance", json={
    "session_id": session_id,
    "current_round_id": round_1_id
})

# System generates synthesis options
synthesis_round = response.json()["next_round"]
options = synthesis_round["synthesis_options"]

# 4. Round 3: Vote (Anonymous)
for participant in participants:
    await client.post(f"/api/v1/deliberation/{session_id}/vote", json={
        "user_id": participant["id"],
        "round_id": synthesis_round["round_id"],
        "rankings": [
            {"option_id": options[0]["description"], "rank": 1},
            {"option_id": options[1]["description"], "rank": 2},
            {"option_id": options[2]["description"], "rank": 3}
        ]
    })

# 5. Check Convergence
response = await client.post(f"/api/v1/deliberation/{session_id}/advance", json={
    "session_id": session_id,
    "current_round_id": synthesis_round["round_id"]
})

if response.json()["session_complete"]:
    final_outcome = response.json()["final_outcome"]
    print(f"Decision: {final_outcome['selected_option']['description']}")
    print(f"Quality Score: {final_outcome['quality_score']}")
```

---

## API Reference

### 1. POST /api/v1/deliberation/start

Start a new deliberation session.

**Request:**
```json
{
  "decision_context": "Should we implement feature X or fix quality issues first?",
  "participants": ["pm_001", "engineer_002", "designer_003"],
  "convergence_criteria": {
    "min_quality_score": 0.7,
    "max_rounds": 5,
    "min_agreement": 0.6
  }
}
```

**Response:**
```json
{
  "session_id": "session-abc123",
  "round_id": "round-001",
  "round_type": "submission",
  "instructions": "Submit your perspective: create a causal graph and provide reasoning..."
}
```

---

### 2. POST /api/v1/deliberation/{session_id}/submit

Submit perspective for submission/refinement rounds.

**Request:**
```json
{
  "user_id": "pm_001",
  "round_id": "round-001",
  "graph": {
    "nodes": ["feature_x", "user_engagement", "retention", "revenue"],
    "edges": [
      {"source": "feature_x", "target": "user_engagement"},
      {"source": "user_engagement", "target": "retention"},
      {"source": "retention", "target": "revenue"}
    ]
  },
  "reasoning": "Feature X will increase user engagement through improved UX, leading to higher retention and revenue growth."
}
```

**Response:**
```json
{
  "accepted": true,
  "causal_quality": {
    "user_id": "pm_001",
    "identification_status": "partial",
    "has_confounders": false,
    "has_mediators": true,
    "robustness_score": 0.72,
    "validation_issues": []
  },
  "validation_issues": []
}
```

---

### 3. POST /api/v1/deliberation/{session_id}/vote

Submit anonymous vote for synthesis options.

**Anonymity Guarantee:**
- User IDs encrypted before storage
- Individual votes remain anonymous during active voting
- Decrypted only after round closes

**Request:**
```json
{
  "user_id": "pm_001",
  "round_id": "round-003",
  "rankings": [
    {
      "option_id": "opt-1",
      "rank": 1,
      "reasoning": "Best balances feature development and quality"
    },
    {
      "option_id": "opt-2",
      "rank": 2
    },
    {
      "option_id": "opt-3",
      "rank": 3
    }
  ]
}
```

**Response:**
```json
{
  "vote_id": "vote-xyz789",
  "accepted": true,
  "vote_count": 2,
  "awaiting_votes_from": 1
}
```

---

### 4. POST /api/v1/deliberation/{session_id}/advance

Advance to next round.

**Request:**
```json
{
  "session_id": "session-abc123",
  "current_round_id": "round-003"
}
```

**Response (Continued):**
```json
{
  "next_round": {
    "round_id": "round-004",
    "round_number": 4,
    "round_type": "refinement",
    "started_at": "2025-01-15T16:00:00Z"
  },
  "convergence_check": {
    "converged": false,
    "quality_score": 0.65,
    "recommendation": "needs_refinement",
    "reason": "High agreement but conflicting causal evidence"
  },
  "session_complete": false
}
```

**Response (Converged):**
```json
{
  "next_round": null,
  "convergence_check": {
    "converged": true,
    "quality_score": 0.82,
    "recommendation": "converge",
    "reason": "Quality threshold met"
  },
  "session_complete": true,
  "final_outcome": {
    "selected_option": {
      "description": "Pilot quality improvements, then staged feature X rollout",
      "causal_mechanism": "Quality fixes reduce churn risk, creating headroom for feature X",
      "satisfies_constraints": ["pm_001", "engineer_002", "designer_003"],
      "pareto_efficiency": 0.85,
      "creative_score": 0.78
    },
    "consensus_level": 0.9,
    "quality_score": 0.82,
    "converged_at": "2025-01-15T16:30:00Z"
  }
}
```

---

### 5. GET /api/v1/deliberation/{session_id}/status

Get current session status.

**Response:**
```json
{
  "session": {
    "session_id": "session-abc123",
    "decision_context": "Should we implement feature X or fix quality issues first?",
    "participants": [...],
    "rounds": [...],
    "status": "active"
  },
  "current_round": {
    "round_id": "round-003",
    "round_number": 3,
    "round_type": "voting",
    "started_at": "2025-01-15T15:00:00Z"
  },
  "next_action": "Awaiting votes (2/3)",
  "awaiting_input_from": ["anonymous_user_0"]
}
```

---

### 6. GET /api/v1/deliberation/{session_id}/history

Get complete deliberation history.

**Response:**
```json
{
  "session": {...},
  "timeline": [
    {
      "timestamp": "2025-01-15T14:00:00Z",
      "event_type": "round_start_submission",
      "round_number": 1,
      "description": "Round 1 (submission) started",
      "actor": "system"
    },
    {
      "timestamp": "2025-01-15T14:10:00Z",
      "event_type": "submission",
      "round_number": 1,
      "description": "Perspective submitted",
      "actor": "pm_001"
    },
    ...
  ],
  "round_details": [
    {
      "round_id": "round-001",
      "round_type": "submission",
      "inputs": [...],
      "synthesis_options": null,
      "votes": null,
      "convergence": null
    },
    ...
  ]
}
```

---

## Round Flow

```
┌─────────────────────┐
│  Round 1: SUBMISSION │
│  ─────────────────   │
│  • Each participant  │
│    submits graph +   │
│    reasoning         │
│  • ISL validates     │
│    causal quality    │
│  • System extracts   │
│    shared goals      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Round 2: SYNTHESIS  │
│  ─────────────────   │
│  • LLM generates 3-5 │
│    creative options  │
│  • Each option       │
│    validated by ISL  │
│  • Pareto efficiency │
│    computed          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Round 3: VOTING     │
│  ─────────────────   │
│  • Participants rank │
│    options (anon)    │
│  • System analyzes   │
│    vote patterns     │
│  • Agreement level   │
│    calculated        │
└──────────┬──────────┘
           │
           ▼
    ┌─────┴──────┐
    │ Converged? │
    └─────┬──────┘
          │
     ┌────┴─────┐
     │          │
    Yes         No
     │          │
     │    ┌─────┴──────────┐
     │    │ Quality High?  │
     │    └─────┬──────────┘
     │          │
     │     ┌────┴─────┐
     │    Yes         No
     │     │          │
     ▼     ▼          ▼
  ┌──────────┐  ┌──────────────┐
  │ COMPLETE │  │ REFINEMENT   │
  │          │  │  ──────────  │
  │ Final    │  │ • Diagnose   │
  │ Outcome  │  │   conflicts  │
  └──────────┘  │ • Suggest    │
                │   tests      │
                │ • Refined    │
                │   positions  │
                └──────┬───────┘
                       │
                       ▼
                  Return to
                  Synthesis
```

---

## Convergence Criteria

### Quality-Based (Not Just Vote Count)

**Composite Quality Score:**
```
quality_score = (
    agreement_level * 0.3 +
    causal_quality * 0.4 +
    creative_synthesis * 0.2 +
    minority_protected_bonus * 0.1
)
```

**Convergence Conditions:**
1. ✅ Agreement ≥ min_agreement (default: 0.6)
2. ✅ Causal quality ≥ threshold (0.5)
3. ✅ Quality score ≥ min_quality_score (default: 0.7)
4. ✅ No unresolved minority evidence
5. ✅ OR max_rounds reached (forced decision)

**Divergence Triggers:**
- **Continue**: Agreement < threshold
- **Needs Refinement**: High agreement but low causal quality
- **Needs Refinement**: Minority has superior evidence

---

## Minority Protection

**Example Scenario:**

```
Team votes 9-1 for price increase:
- 9 people: "Price up = revenue up" (simple)
- 1 engineer: "Price up → churn up → revenue DOWN" (strong causal evidence)

System Response:
- ⚠️ Warning: "engineer_003's position has superior causal backing (0.9 vs. avg 0.4)"
- 🚫 Blocks convergence
- 📋 Suggests refinement round to address engineer's evidence
```

**Protection Logic:**
```python
if minority_robustness_score > avg_score + 0.3:
    if minority_size < total_participants / 3:
        # Minority has strong evidence - protect
        return ConvergenceStatus(
            converged=False,
            recommendation="needs_refinement",
            reason=f"{minority_user}'s evidence superior - review before deciding"
        )
```

---

## Anonymous Voting

### How It Works

**During Active Voting:**
```python
# User submits vote
vote = {
    "user_id": "pm_001",
    "rankings": [...]
}

# System encrypts user ID
encrypted_vote = {
    "user_id": "encrypted-4f9a2c1b",  # Deterministic encryption
    "rankings": [...]
}

# Individual votes remain anonymous
```

**After Round Closes:**
```python
# System decrypts for aggregation
decrypted_votes = [
    {"user_id": "pm_001", "rankings": [...]},
    {"user_id": "engineer_002", "rankings": [...]},
    ...
]

# Individual votes now visible in history
```

**Guarantee:**
- Same user_id → same encrypted value (deduplication)
- Cannot decrypt during active voting
- Full transparency after round closes

---

## FACET Robustness Analysis

### Counterfactual Validation

```python
# Example: "Price increase causes churn"
robustness = await facet_client.compute_robustness(
    graph=causal_graph,
    intervention="price_increase",
    outcome="churn",
    num_scenarios=20
)

# Result:
{
    "robustness_score": 0.85,  # 17/20 scenarios support claim
    "confidence_interval": {
        "lower": 0.78,
        "upper": 0.92,
        "confidence_level": 0.95
    },
    "robust_region": {
        "interventions": [
            "10% price increase",
            "20% price increase",
            "30% price increase"
        ],
        "all_lead_to": "increased churn"
    },
    "sensitivity_factors": [
        {
            "factor": "customer_segment",
            "impact_on_estimate": "high"
        }
    ]
}
```

### Interpretation

- **Robustness ≥ 0.7**: Strong evidence
- **0.4 ≤ Robustness < 0.7**: Moderate evidence
- **Robustness < 0.4**: Weak/conflicting evidence

---

## Best Practices

### 1. Set Realistic Convergence Criteria

✅ **Good:**
```json
{
  "min_quality_score": 0.7,
  "max_rounds": 5,
  "min_agreement": 0.6
}
```

❌ **Too Strict:**
```json
{
  "min_quality_score": 0.95,  // Rarely achievable
  "max_rounds": 20  // Too many rounds
}
```

### 2. Provide Strong Causal Reasoning

✅ **Good:**
> "Price increase → customer churn → revenue loss. Based on Q3 data showing 15% churn increase with each 10% price hike. Confounded by product quality (also affects churn). Mechanism: perceived value decreases when price exceeds quality expectations."

❌ **Weak:**
> "I think higher prices might reduce revenue."

### 3. Monitor Convergence Metrics

```promql
# Convergence rate
rate(tae_deliberation_sessions_total{status="converged"}[1h]) /
rate(tae_deliberation_sessions_total[1h])

# Average rounds to convergence
avg(tae_deliberation_rounds_per_session)

# Minority protections triggered
rate(tae_deliberation_minority_protections_triggered[1h])
```

---

## Prometheus Metrics

```promql
# Session metrics
tae_deliberation_sessions_total{num_participants="2-5"}
tae_deliberation_rounds_per_session
tae_deliberation_convergence_rate

# Quality metrics
tae_deliberation_quality_score
tae_deliberation_vote_agreement_level

# Protection metrics
tae_deliberation_minority_protections_triggered

# FACET metrics
tae_facet_robustness_calls_total
tae_facet_robustness_score
```

---

## Troubleshooting

### Issue: Session Not Converging

**Symptoms:**
- Reached max_rounds without convergence
- Quality score stuck below threshold

**Causes:**
1. Participants have fundamentally different values (not causal disagreement)
2. Weak causal reasoning across all perspectives
3. Unresolved minority evidence

**Solutions:**
1. Check convergence_check.reason for diagnosis
2. Review conflicts in round details
3. Consider values conflict → Pareto analysis (not forcing consensus)

---

### Issue: All Votes Unanimous But No Convergence

**Cause:** High agreement but low causal quality

**System Response:**
```json
{
  "converged": false,
  "reason": "High agreement (0.9) but low causal quality (0.3) - gather evidence"
}
```

**Solution:** Request stronger causal reasoning from participants

---

## Further Reading

- [Consensus Builder API](./consensus_builder.md)
- [Causal Validation Guide](./causal_validation.md)
- [FACET Integration](./facet_integration.md)
- [Habermas Machine Paper (Science 2024)](https://www.science.org/doi/10.1126/science.example)

---

## Support

- GitHub Issues: https://github.com/your-org/tae/issues
- Email: support@tae.example.com
- Slack: #team-alignment-engine
