"""Consensus Builder models for science-backed team decision making.

Inspired by Habermas Machine (Science 2024) - prevents mediocre compromise
by weighting inputs with causal evidence strength rather than social influence.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime


# ============================================================================
# REQUEST MODELS
# ============================================================================


class GraphV1(BaseModel):
    """Causal graph structure."""

    nodes: List[str] = Field(..., description="List of variable names")
    edges: List[Dict[str, str]] = Field(
        ...,
        description="List of edges with 'source' and 'target' keys",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": ["price", "quality", "churn", "revenue"],
                "edges": [
                    {"source": "price", "target": "churn"},
                    {"source": "quality", "target": "churn"},
                    {"source": "churn", "target": "revenue"},
                ],
            }
        }


class TeamInputV1(BaseModel):
    """Individual team member's perspective with causal reasoning."""

    user_id: str = Field(..., description="Pseudonymous user ID (e.g., 'user_123')")
    graph: GraphV1 = Field(..., description="Causal graph representing their mental model")
    reasoning: str = Field(
        ...,
        description="Natural language explanation of their position",
        max_length=2000,
    )
    submitted_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO timestamp of submission",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "pm_001",
                "graph": {
                    "nodes": ["price_increase", "churn", "revenue"],
                    "edges": [
                        {"source": "price_increase", "target": "churn"},
                        {"source": "churn", "target": "revenue"},
                    ],
                },
                "reasoning": "A 30% price increase will boost revenue despite small churn",
                "submitted_at": "2025-01-15T10:30:00Z",
            }
        }


class ConsensusRequestV1(BaseModel):
    """Request for consensus building analysis."""

    perspectives: List[TeamInputV1] = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Team member perspectives (2-10 members)",
    )
    decision_context: str = Field(
        ...,
        description="Background context for the decision",
        max_length=1000,
    )
    require_creative_synthesis: bool = Field(
        default=True,
        description="Generate creative options (not just averaging)",
    )
    protect_minority_evidence: bool = Field(
        default=True,
        description="Flag minority positions with strong causal backing",
    )
    min_causal_quality: Literal["any", "partial", "identified"] = Field(
        default="partial",
        description="Minimum causal quality threshold",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "perspectives": [
                    {
                        "user_id": "pm_001",
                        "graph": {"nodes": ["price", "revenue"], "edges": []},
                        "reasoning": "Raise price 30% to boost revenue",
                        "submitted_at": "2025-01-15T10:30:00Z",
                    },
                    {
                        "user_id": "engineer_002",
                        "graph": {
                            "nodes": ["quality", "price", "retention"],
                            "edges": [
                                {"source": "quality", "target": "retention"},
                                {"source": "price", "target": "retention"},
                            ],
                        },
                        "reasoning": "Fix quality first, then consider pricing",
                        "submitted_at": "2025-01-15T10:32:00Z",
                    },
                ],
                "decision_context": "Considering 30% price increase for SaaS product",
                "require_creative_synthesis": True,
                "protect_minority_evidence": True,
                "min_causal_quality": "partial",
            }
        }


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class CausalQualityV1(BaseModel):
    """Causal quality assessment for a team member's input."""

    user_id: str
    identification_status: Literal["identified", "partial", "unidentified"] = Field(
        ..., description="Causal identification status from ISL"
    )
    has_confounders: bool = Field(
        ..., description="Whether confounding variables detected"
    )
    has_mediators: bool = Field(..., description="Whether mediator variables detected")
    robustness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Robustness score (0-1, from FACET if available)"
    )
    validation_issues: List[str] = Field(
        default_factory=list, description="List of validation issues found"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "pm_001",
                "identification_status": "partial",
                "has_confounders": True,
                "has_mediators": False,
                "robustness_score": 0.6,
                "validation_issues": ["Missing edge: quality -> churn"],
            }
        }


class CausalConflictV1(BaseModel):
    """Details for causal-type conflicts."""

    evidence_for: Dict[str, List[str]] = Field(
        ..., description="Evidence supporting each position"
    )
    decisive_test: Optional[str] = Field(
        None, description="Suggested test to resolve conflict"
    )


class ValuesConflictV1(BaseModel):
    """Details for values-type conflicts."""

    trade_off_dimensions: List[str] = Field(
        ..., description="Dimensions of the trade-off"
    )
    pareto_options: List[str] = Field(
        ..., description="Options that are Pareto-efficient"
    )


class FramingConflictV1(BaseModel):
    """Details for framing-type conflicts."""

    shared_goal: str = Field(..., description="The underlying shared goal")
    alternative_paths: List[str] = Field(
        ..., description="Different paths to achieve goal"
    )


class ConflictPositionV1(BaseModel):
    """Individual position in a conflict."""

    user_id: str
    position: str
    causal_backing: CausalQualityV1


class ConflictAnalysisV1(BaseModel):
    """Analysis of conflict between team perspectives."""

    conflict_type: Literal["causal", "values", "framing", "mixed"]
    positions: List[ConflictPositionV1]

    # Type-specific details
    causal_conflict: Optional[CausalConflictV1] = None
    values_conflict: Optional[ValuesConflictV1] = None
    framing_conflict: Optional[FramingConflictV1] = None


class CausalGraphChangesV1(BaseModel):
    """Changes to causal graph in synthesis option."""

    nodes_added: List[str] = Field(default_factory=list)
    edges_added: List[str] = Field(default_factory=list)
    mediators_introduced: List[str] = Field(default_factory=list)


class SynthesisOptionV1(BaseModel):
    """Creative synthesis option that satisfies multiple constraints."""

    description: str = Field(..., description="Natural language description of option")
    causal_mechanism: str = Field(
        ..., description="How this option achieves outcomes"
    )
    satisfies_constraints: List[str] = Field(
        ..., description="Which stakeholder needs are met"
    )
    pareto_efficiency: float = Field(
        ..., ge=0.0, le=1.0, description="Pareto efficiency score (0-1)"
    )
    creative_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Novelty vs. obvious averaging (0=identical, 1=novel)",
    )
    causal_graph_changes: CausalGraphChangesV1


class ConsensusWarningV1(BaseModel):
    """Warning about consensus quality issues."""

    warning_type: Literal[
        "minority_has_strong_evidence", "forced_compromise", "weak_causal_backing"
    ]
    severity: Literal["info", "warning", "critical"]
    message: str
    affected_positions: List[str] = Field(..., description="User IDs affected")
    recommendation: str


class QualityMetricsV1(BaseModel):
    """Quality metrics for consensus process."""

    causal_validation_passed: bool
    minority_positions_examined: bool
    creative_synthesis_attempted: bool
    forced_compromise_detected: bool


class TraceMetadataV1(BaseModel):
    """Trace metadata for debugging."""

    correlation_id: str
    processing_time_ms: float
    isl_calls: int
    llm_calls: int


class ConsensusResponseV1(BaseModel):
    """Response from consensus builder."""

    shared_goals: List[str] = Field(
        default_factory=list, description="Goals all team members agree on"
    )
    shared_beliefs: List[str] = Field(
        default_factory=list, description="Causal relationships all agree on"
    )
    synthesis_options: List[SynthesisOptionV1] = Field(
        default_factory=list, description="Creative synthesis options"
    )
    conflicts: List[ConflictAnalysisV1] = Field(
        default_factory=list, description="Identified conflicts"
    )
    warnings: List[ConsensusWarningV1] = Field(
        default_factory=list, description="Quality warnings"
    )
    quality_metrics: QualityMetricsV1
    trace: TraceMetadataV1

    class Config:
        json_schema_extra = {
            "example": {
                "shared_goals": ["Increase revenue", "Maintain customer satisfaction"],
                "shared_beliefs": ["Quality affects retention"],
                "synthesis_options": [
                    {
                        "description": "Improve UX, then 20% price increase (staged)",
                        "causal_mechanism": "UX improvements increase perceived value, reducing price sensitivity",
                        "satisfies_constraints": [
                            "pm_001 (revenue growth)",
                            "designer_002 (UX first)",
                            "engineer_003 (quality)",
                        ],
                        "pareto_efficiency": 0.85,
                        "creative_score": 0.72,
                        "causal_graph_changes": {
                            "nodes_added": ["perceived_value"],
                            "edges_added": ["ux -> perceived_value", "perceived_value -> price_sensitivity"],
                            "mediators_introduced": ["perceived_value"],
                        },
                    }
                ],
                "conflicts": [],
                "warnings": [
                    {
                        "warning_type": "minority_has_strong_evidence",
                        "severity": "warning",
                        "message": "Engineer's position has superior causal backing",
                        "affected_positions": ["pm_001"],
                        "recommendation": "Consider evidence from engineer_003 before proceeding",
                    }
                ],
                "quality_metrics": {
                    "causal_validation_passed": True,
                    "minority_positions_examined": True,
                    "creative_synthesis_attempted": True,
                    "forced_compromise_detected": False,
                },
                "trace": {
                    "correlation_id": "consensus-abc123",
                    "processing_time_ms": 3450.5,
                    "isl_calls": 3,
                    "llm_calls": 2,
                },
            }
        }
