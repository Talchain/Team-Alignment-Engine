"""Advanced analytics endpoints for Phase D5."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.models.portfolio import TrendAnalysis, ComparativeBenchmark
from src.services.analytics_engine import AdvancedAnalyticsEngine
from src.storage.database import get_db

router = APIRouter(prefix="/api/v1/advanced-analytics", tags=["advanced-analytics"])


@router.get("/trends", response_model=TrendAnalysis)
async def analyze_metric_trends(
    organization_id: UUID = Query(..., description="Organization ID"),
    metric_name: str = Query(
        ...,
        description="Metric to analyze",
        regex="^(decision_time|quality_score|satisfaction_score|stakeholder_count)$",
    ),
    lookback_days: int = Query(
        90, ge=30, le=365, description="Days of history to analyze"
    ),
    db: AsyncSession = Depends(get_db),
) -> TrendAnalysis:
    """
    Analyze trends for a decision metric.

    **Available metrics:**
    - `decision_time`: Days from start to completion
    - `quality_score`: Retrospective quality ratings
    - `satisfaction_score`: Stakeholder satisfaction
    - `stakeholder_count`: Number of participants

    **Analysis includes:**
    - **Trend direction**: increasing, decreasing, or stable
    - **Trend strength**: R-squared value (0-1)
    - **Moving average**: 7-day smoothed values
    - **30-day forecast**: Predicted future values
    - **Changepoints**: Significant inflection points
    - **Confidence intervals**: 95% forecast uncertainty

    **Use cases:**
    - Executive dashboards: "Is decision quality improving?"
    - Capacity planning: "Will decision time increase?"
    - Process monitoring: "When did velocity change?"

    **Example response:**
    ```json
    {
        "organization_id": "org-123",
        "metric_name": "decision_time",
        "time_period_days": 90,
        "data_points": [
            {"timestamp": 1234567890, "value": 5.2},
            {"timestamp": 1234654290, "value": 4.8}
        ],
        "trend_direction": "decreasing",
        "trend_strength": 0.72,
        "moving_average": [
            {"timestamp": 1234567890, "value": 5.0}
        ],
        "forecast_30days": [
            {"timestamp": 1235000000, "value": 4.2}
        ],
        "changepoints": ["2025-01-15T00:00:00Z"],
        "confidence_intervals": [
            {
                "timestamp": 1235000000,
                "lower": 3.0,
                "upper": 5.4
            }
        ]
    }
    ```

    **Performance:**
    - Target: <2s for 90 days of data
    - Caching: Results cached for 1 hour

    **Statistical methods:**
    - Linear regression for trend analysis
    - Simple moving average for smoothing
    - T-test for changepoint detection
    - Normal distribution for confidence intervals
    """
    try:
        engine = AdvancedAnalyticsEngine(db)

        analysis = await engine.analyze_trends(
            organization_id=organization_id,
            metric_name=metric_name,
            lookback_days=lookback_days,
        )

        return analysis

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze trends: {str(e)}",
        )


@router.get("/benchmarks", response_model=ComparativeBenchmark)
async def get_comparative_benchmarks(
    organization_id: UUID = Query(..., description="Organization ID"),
    decision_type: str = Query(..., description="Decision type to benchmark"),
    lookback_days: int = Query(
        90, ge=30, le=365, description="Days of history"
    ),
    db: AsyncSession = Depends(get_db),
) -> ComparativeBenchmark:
    """
    Get comparative benchmarks for a decision type.

    **What it provides:**
    - Organization metrics vs. industry average
    - Percentile rankings for key metrics
    - Identified strengths (top quartile)
    - Improvement areas (bottom quartile)

    **Benchmarked metrics:**
    - Decision time (days)
    - Quality score (1-10)
    - Satisfaction score (1-10)
    - Stakeholder count (team size)

    **Use cases:**
    - Executive reporting: "How do we compare to peers?"
    - Goal setting: "What should we target?"
    - Process improvement: "Where should we focus?"

    **Example response:**
    ```json
    {
        "organization_id": "org-123",
        "decision_type": "pricing",
        "sample_size": 15,
        "organization_metrics": {
            "decision_time_days": 4.2,
            "quality_score": 8.5,
            "satisfaction_score": 8.8,
            "stakeholder_count": 3.8
        },
        "industry_average": {
            "decision_time_days": 10.0,
            "quality_score": 7.0,
            "satisfaction_score": 7.5,
            "stakeholder_count": 5.0
        },
        "percentile_rankings": {
            "decision_time_days": 85.0,
            "quality_score": 78.0
        },
        "strengths": [
            "Decision Time Days in top quartile",
            "Quality Score in top quartile"
        ],
        "improvement_areas": []
    }
    ```

    **Performance:**
    - Target: <1s response time
    - Caching: Results cached for 4 hours

    **Note:**
    - Industry averages are based on aggregated data
    - Percentiles calculated against peer organizations
    - Minimum 3 sessions required for meaningful comparison
    """
    try:
        engine = AdvancedAnalyticsEngine(db)

        benchmark = await engine.compare_benchmarks(
            organization_id=organization_id,
            decision_type=decision_type,
            lookback_days=lookback_days,
        )

        return benchmark

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate benchmarks: {str(e)}",
        )
