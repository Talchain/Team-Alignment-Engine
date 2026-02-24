# Consensus Builder API - Usage Guide

## Overview

The Consensus Builder is a science-backed consensus mechanism inspired by the **Habermas Machine** methodology published in *Science* (2024). Unlike traditional voting or averaging approaches, it:

- **Weights inputs by causal evidence strength**, not social influence
- **Prevents mediocre compromise** through causal validation
- **Protects minority positions** with strong evidence backing
- **Generates creative synthesis options** (not just averaging)

## Table of Contents

- [Quick Start](#quick-start)
- [API Endpoint](#api-endpoint)
- [Request Schema](#request-schema)
- [Response Schema](#response-schema)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Basic Example

```bash
curl -X POST https://api.tae.example.com/api/v1/assist/consensus-builder \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "perspectives": [
      {
        "user_id": "pm_001",
        "graph": {
          "nodes": ["price", "revenue"],
          "edges": [{"source": "price", "target": "revenue"}]
        },
        "reasoning": "Raise price 30% to boost revenue"
      },
      {
        "user_id": "engineer_002",
        "graph": {
          "nodes": ["price", "churn", "quality", "revenue"],
          "edges": [
            {"source": "price", "target": "churn"},
            {"source": "quality", "target": "churn"},
            {"source": "churn", "target": "revenue"}
          ]
        },
        "reasoning": "Fix quality first, then consider pricing"
      }
    ],
    "decision_context": "Considering 30% price increase for SaaS product"
  }'
```

---

## API Endpoint

### POST /api/v1/assist/consensus-builder

Build consensus from team member perspectives using causal reasoning.

**URL:** `POST /api/v1/assist/consensus-builder`

**Authentication:** Required (API Key or Bearer Token)

**Rate Limit:** 100 requests/hour per team

**Timeout:** 60 seconds

---

## Request Schema

### ConsensusRequestV1

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `perspectives` | `List[TeamInputV1]` | Yes | Team member perspectives (2-10) |
| `decision_context` | `string` | Yes | Background context for decision (max 1000 chars) |
| `require_creative_synthesis` | `boolean` | No | Generate creative options (default: `true`) |
| `protect_minority_evidence` | `boolean` | No | Flag minority positions with strong evidence (default: `true`) |
| `min_causal_quality` | `enum` | No | Minimum quality threshold: `any`, `partial`, `identified` (default: `partial`) |

### TeamInputV1

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | `string` | Yes | Pseudonymous user ID (e.g., `"user_123"`) |
| `graph` | `GraphV1` | Yes | Causal graph representing mental model |
| `reasoning` | `string` | Yes | Natural language explanation (max 2000 chars) |
| `submitted_at` | `string` | No | ISO timestamp (auto-generated if omitted) |

### GraphV1

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nodes` | `List[string]` | Yes | List of variable names |
| `edges` | `List[Edge]` | Yes | List of edges with `source` and `target` |

---

## Response Schema

### ConsensusResponseV1

| Field | Type | Description |
|-------|------|-------------|
| `shared_goals` | `List[string]` | Goals all team members agree on |
| `shared_beliefs` | `List[string]` | Causal relationships all agree on |
| `synthesis_options` | `List[SynthesisOptionV1]` | Creative synthesis options |
| `conflicts` | `List[ConflictAnalysisV1]` | Identified conflicts |
| `warnings` | `List[ConsensusWarningV1]` | Quality warnings |
| `quality_metrics` | `QualityMetricsV1` | Process quality indicators |
| `trace` | `TraceMetadataV1` | Debugging metadata |

### SynthesisOptionV1

| Field | Type | Description |
|-------|------|-------------|
| `description` | `string` | Natural language description |
| `causal_mechanism` | `string` | How this option achieves outcomes |
| `satisfies_constraints` | `List[string]` | Which stakeholder needs are met (user_ids) |
| `pareto_efficiency` | `float` | Pareto efficiency score (0-1) |
| `creative_score` | `float` | Novelty vs. obvious averaging (0-1) |
| `causal_graph_changes` | `CausalGraphChangesV1` | Graph modifications |

### ConsensusWarningV1

| Field | Type | Description |
|-------|------|-------------|
| `warning_type` | `enum` | `minority_has_strong_evidence`, `forced_compromise`, `weak_causal_backing` |
| `severity` | `enum` | `info`, `warning`, `critical` |
| `message` | `string` | Human-readable warning message |
| `affected_positions` | `List[string]` | User IDs affected |
| `recommendation` | `string` | Recommended action |

---

## Usage Examples

### Example 1: Product Pricing Decision

**Scenario:** PM wants 30% price increase, Engineer warns about churn

```json
{
  "perspectives": [
    {
      "user_id": "pm_001",
      "graph": {
        "nodes": ["price_increase", "revenue"],
        "edges": [
          {"source": "price_increase", "target": "revenue"}
        ]
      },
      "reasoning": "A 30% price increase will directly boost revenue by increasing average revenue per user"
    },
    {
      "user_id": "engineer_003",
      "graph": {
        "nodes": ["price_increase", "churn", "quality", "revenue"],
        "edges": [
          {"source": "price_increase", "target": "churn"},
          {"source": "quality", "target": "churn"},
          {"source": "churn", "target": "revenue"}
        ]
      },
      "reasoning": "Price increase will cause customer churn. We have quality issues that already risk churn. Fix quality first."
    }
  ],
  "decision_context": "Deciding on 30% SaaS price increase for enterprise product"
}
```

**Expected Response:**

```json
{
  "shared_goals": ["Increase revenue", "Maintain customer base"],
  "shared_beliefs": [],
  "synthesis_options": [
    {
      "description": "Pilot quality improvements with beta customers, then implement staged 15% price increase over 6 months",
      "causal_mechanism": "Quality improvements increase perceived value, reducing price sensitivity before staged increase",
      "satisfies_constraints": ["pm_001", "engineer_003"],
      "pareto_efficiency": 0.85,
      "creative_score": 0.72,
      "causal_graph_changes": {
        "nodes_added": ["perceived_value", "customer_satisfaction"],
        "edges_added": [
          "quality → perceived_value",
          "perceived_value → price_sensitivity"
        ],
        "mediators_introduced": ["perceived_value"]
      }
    }
  ],
  "conflicts": [
    {
      "conflict_type": "causal",
      "positions": [
        {
          "user_id": "pm_001",
          "position": "Price increase directly boosts revenue",
          "causal_backing": {
            "user_id": "pm_001",
            "identification_status": "partial",
            "robustness_score": 0.5
          }
        },
        {
          "user_id": "engineer_003",
          "position": "Price increase causes churn which reduces revenue",
          "causal_backing": {
            "user_id": "engineer_003",
            "identification_status": "identified",
            "robustness_score": 0.9
          }
        }
      ],
      "causal_conflict": {
        "evidence_for": {
          "pm_001": ["Claims: price_increase → revenue"],
          "engineer_003": [
            "Claims: price_increase → churn",
            "Claims: churn → revenue"
          ]
        },
        "decisive_test": "Run A/B test: does price increase cause churn?"
      }
    }
  ],
  "warnings": [
    {
      "warning_type": "minority_has_strong_evidence",
      "severity": "warning",
      "message": "engineer_003's position has superior causal backing (0.9 vs. avg 0.5)",
      "affected_positions": ["pm_001"],
      "recommendation": "Review evidence from engineer_003 before proceeding"
    }
  ],
  "quality_metrics": {
    "causal_validation_passed": true,
    "minority_positions_examined": true,
    "creative_synthesis_attempted": true,
    "forced_compromise_detected": false
  },
  "trace": {
    "correlation_id": "consensus-abc123",
    "processing_time_ms": 2450.5,
    "isl_calls": 2,
    "llm_calls": 1
  }
}
```

---

### Example 2: Architecture Decision

**Scenario:** Different architectural approaches for scaling

```json
{
  "perspectives": [
    {
      "user_id": "architect_001",
      "graph": {
        "nodes": ["microservices", "complexity", "development_speed", "scalability"],
        "edges": [
          {"source": "microservices", "target": "complexity"},
          {"source": "complexity", "target": "development_speed"},
          {"source": "microservices", "target": "scalability"}
        ]
      },
      "reasoning": "Microservices enable scalability but increase complexity and slow development"
    },
    {
      "user_id": "tech_lead_002",
      "graph": {
        "nodes": ["monolith", "development_speed", "team_size", "complexity"],
        "edges": [
          {"source": "monolith", "target": "development_speed"},
          {"source": "team_size", "target": "complexity"}
        ]
      },
      "reasoning": "Monolith is faster to develop with our team size. We can scale vertically for now."
    }
  ],
  "decision_context": "Choosing architecture for new product (expected 100K users in year 1)",
  "min_causal_quality": "partial"
}
```

**Insight:** This is a **framing conflict** (same goal, different paths). The consensus builder will:
1. Identify the shared goal: "Build scalable product quickly"
2. Classify as framing conflict (not causal disagreement)
3. Generate synthesis options that satisfy both constraints

---

### Example 3: Values Conflict

**Scenario:** Speed vs. Quality trade-off

```json
{
  "perspectives": [
    {
      "user_id": "product_manager",
      "graph": {
        "nodes": ["fast_launch", "market_share", "revenue"],
        "edges": [
          {"source": "fast_launch", "target": "market_share"},
          {"source": "market_share", "target": "revenue"}
        ]
      },
      "reasoning": "Launch quickly to capture market share before competitors"
    },
    {
      "user_id": "qa_engineer",
      "graph": {
        "nodes": ["thorough_testing", "quality", "reputation", "revenue"],
        "edges": [
          {"source": "thorough_testing", "target": "quality"},
          {"source": "quality", "target": "reputation"},
          {"source": "reputation", "target": "revenue"}
        ]
      },
      "reasoning": "Thorough testing ensures quality, protecting long-term reputation and revenue"
    }
  ],
  "decision_context": "Launch timeline for new feature"
}
```

**Insight:** This is a **values conflict** (different priorities). The consensus builder will:
1. Identify shared goal: "Maximize revenue"
2. Classify as values conflict (speed vs. quality)
3. Compute Pareto-efficient options that balance both

---

## Best Practices

### 1. Provide Clear Causal Graphs

✅ **Good:**
```json
{
  "nodes": ["price_increase", "churn", "revenue"],
  "edges": [
    {"source": "price_increase", "target": "churn"},
    {"source": "churn", "target": "revenue"}
  ]
}
```

❌ **Bad:**
```json
{
  "nodes": ["stuff", "things", "outcomes"],
  "edges": []
}
```

### 2. Write Detailed Reasoning

✅ **Good:**
> "A 30% price increase will increase churn from 5% to 8% based on competitor analysis. However, the revenue gain from higher ARPU (+30%) will offset the churn loss (-3% customers), resulting in net +24% revenue growth."

❌ **Bad:**
> "Price up = revenue up"

### 3. Use Pseudonymous User IDs

✅ **Good:** `pm_001`, `engineer_alice`, `analyst_team_b`

❌ **Bad:** `alice.smith@company.com`, `Real Name`

### 4. Set Appropriate Quality Thresholds

- `"any"`: Accept all inputs (use for brainstorming)
- `"partial"`: Require some causal structure (default, recommended)
- `"identified"`: Require fully identified causal graphs (strict, research-grade)

### 5. Handle Warnings Properly

Always check `warnings` in the response:

```python
response = consensus_builder_api.build_consensus(request)

for warning in response.warnings:
    if warning.warning_type == "minority_has_strong_evidence":
        print(f"⚠️  {warning.message}")
        print(f"📋 Recommendation: {warning.recommendation}")
```

---

## Troubleshooting

### Issue: "At least 2 perspectives required"

**Cause:** You provided fewer than 2 perspectives.

**Solution:** Add more team member inputs.

```json
{
  "perspectives": [
    {"user_id": "user_1", ...},
    {"user_id": "user_2", ...}  // Minimum 2
  ]
}
```

---

### Issue: "Maximum 10 perspectives allowed"

**Cause:** You provided more than 10 perspectives.

**Solution:** Reduce to 10 or fewer, or split into multiple consensus requests.

---

### Issue: Low Creative Scores

**Symptom:** `creative_score` is consistently < 0.3

**Causes:**
1. All perspectives have similar graphs
2. LLM is averaging rather than synthesizing
3. No new causal mechanisms introduced

**Solution:** Encourage diverse perspectives with different mental models.

---

### Issue: "forced_compromise" Warning

**Symptom:** `forced_compromise_detected: true`

**Cause:** Conflicts exist but no creative synthesis found.

**Solution:**
1. Review conflicts in `response.conflicts`
2. Check `causal_conflict.decisive_test` for suggested experiments
3. Gather more evidence before deciding

---

### Issue: All Synthesis Options Have Same Description

**Cause:** LLM API key not configured (using mock responses).

**Solution:** Configure `OPENAI_API_KEY` environment variable.

```bash
export OPENAI_API_KEY="sk-..."
```

---

## Metrics and Monitoring

Track consensus builder usage with Prometheus metrics:

```promql
# Request rate
rate(tae_consensus_requests_total[5m])

# Processing duration
histogram_quantile(0.95, rate(tae_consensus_calculation_duration_seconds_bucket[5m]))

# Warning rate by type
rate(tae_consensus_warnings_total{warning_type="minority_has_strong_evidence"}[5m])

# Synthesis option generation
rate(tae_consensus_synthesis_options_generated_total[5m])
```

---

## API Limits

| Limit | Value |
|-------|-------|
| Min perspectives | 2 |
| Max perspectives | 10 |
| Max reasoning length | 2000 characters |
| Max decision_context length | 1000 characters |
| Max nodes per graph | 100 |
| Max edges per graph | 500 |
| Request timeout | 60 seconds |
| Rate limit | 100 requests/hour per team |

---

## Further Reading

- [Habermas Machine Paper (Science 2024)](https://www.science.org/doi/10.1126/science.example)
- [TAE Causal Validation Guide](./causal_validation.md)
- [ISL Integration Documentation](./isl_integration.md)
- [Phase C Intelligent Assistance](./phase_c_guide.md)

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/tae/issues
- Email: support@tae.example.com
- Slack: #team-alignment-engine
