"""Organizational pattern endpoints for Phase D4."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.models.portfolio import OrganizationalPatterns
from src.services.pattern_analyzer import PatternAnalyzer
from src.storage.database import get_db

router = APIRouter(prefix="/api/v1/patterns", tags=["patterns"])


@router.get("/organization/{organization_id}", response_model=OrganizationalPatterns)
async def get_organizational_patterns(
    organization_id: UUID,
    lookback_days: int = Query(
        90, ge=7, le=365, description="Days of history to analyze"
    ),
    min_sample_size: int = Query(
        3, ge=1, le=20, description="Minimum sessions per pattern"
    ),
    db: AsyncSession = Depends(get_db),
) -> OrganizationalPatterns:
    """
    Extract organizational decision patterns.

    **What it does:**
    - Analyzes completed decisions from the past N days
    - Identifies success and failure patterns by decision type
    - Extracts common characteristics of each pattern
    - Determines success factors and failure indicators
    - Generates actionable recommendations

    **Pattern Analysis:**
    - **Success patterns**: Fast decisions with positive outcomes
    - **Failure patterns**: Slow decisions or poor satisfaction
    - **Neutral patterns**: Average performance, room for optimization

    **Characteristics extracted:**
    - Team size (small/large)
    - Decision timeline (rapid/extended)
    - Alignment mode preferences
    - Stakeholder engagement levels

    **Success factors identified:**
    - Fast decision cycles (< 5 days)
    - Optimal team size (4-7 stakeholders)
    - Clear decision context
    - Evidence-based evaluation

    **Failure indicators identified:**
    - Extended deliberation (> 14 days)
    - Large stakeholder groups (> 10)
    - Decision fatigue
    - Analysis paralysis

    **Use cases:**
    - Executive learning: "What makes our decisions successful?"
    - Process improvement: "Where are we consistently struggling?"
    - Training: "What patterns should new teams follow?"
    - Benchmarking: "How do different decision types perform?"

    **Example response:**
    ```json
    {
        "organization_id": "org-123",
        "analysis_period_days": 90,
        "total_sessions_analyzed": 45,
        "patterns": [
            {
                "pattern_id": "pricing_success",
                "pattern_type": "success",
                "decision_type": "pricing",
                "sample_size": 8,
                "description": "pricing decisions typically take 4.2 days",
                "common_characteristics": [
                    "Small team size (< 4 stakeholders)",
                    "Rapid decision cycle (< 3 days)"
                ],
                "avg_metrics": {
                    "avg_time_days": 4.2,
                    "avg_stakeholders": 3.5,
                    "avg_quality": 8.2
                },
                "confidence": 0.75,
                "recommendations": [
                    "Continue current approach for pricing decisions",
                    "Fast cycle time is a strength - maintain urgency"
                ]
            }
        ],
        "success_factors": [
            "Fast decision cycles correlate with positive outcomes",
            "Optimal team size improves decision quality"
        ],
        "failure_indicators": [
            "Extended deliberation correlates with decision fatigue"
        ],
        "recommendations": [
            "Document and share successful decision patterns",
            "Implement decision playbooks for common types"
        ]
    }
    ```

    **Performance:**
    - Target: <3s for 90 days of history
    - Caching: Results cached for 1 hour

    **Parameters:**
    - `lookback_days`: 7-365 days (default: 90)
    - `min_sample_size`: 1-20 sessions (default: 3)
    """
    try:
        analyzer = PatternAnalyzer(db)

        patterns = await analyzer.extract_patterns(
            organization_id=organization_id,
            lookback_days=lookback_days,
            min_sample_size=min_sample_size,
        )

        return patterns

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract patterns: {str(e)}",
        )
