"""Portfolio analytics endpoints for Phase D1."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.models.portfolio import (
    PortfolioAnalysis,
    PortfolioFilters,
    DateRange,
)
from src.models.enums import SessionStatus
from src.services.portfolio_analyzer import PortfolioAnalyzer, InsufficientDataError
from src.storage.database import get_db

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])
logger = logging.getLogger(__name__)


class PortfolioAnalysisResponse(BaseModel):
    """Response model for portfolio analytics."""

    analysis: PortfolioAnalysis
    request_id: Optional[str] = None


@router.get("/analytics", response_model=PortfolioAnalysisResponse)
async def get_portfolio_analytics(
    organization_id: UUID = Query(..., description="Organization ID to analyze"),
    start_date: Optional[datetime] = Query(
        None, description="Start date for analysis period (defaults to 30 days ago)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="End date for analysis period (defaults to now)"
    ),
    teams: Optional[List[UUID]] = Query(
        None, description="Filter by specific team IDs"
    ),
    decision_types: Optional[List[str]] = Query(
        None, description="Filter by decision types"
    ),
    status: Optional[List[SessionStatus]] = Query(
        None, description="Filter by session status"
    ),
    min_risk_score: Optional[float] = Query(
        None, ge=0, le=1, description="Minimum risk score threshold (0-1)"
    ),
    db: AsyncSession = Depends(get_db),
) -> PortfolioAnalysisResponse:
    """
    Get portfolio-level analytics across multiple decisions.

    Returns aggregated metrics, decision clusters, bottlenecks,
    and CEE-generated strategic insights for organizational decision health.

    **What it does:**
    - Aggregates decision metrics across sessions
    - Identifies clusters of related decisions
    - Detects bottlenecks and stuck sessions
    - Calculates portfolio health score
    - Generates strategic insights via CEE

    **Use cases:**
    - Executive dashboard showing decision-making health
    - Identifying patterns across multiple decisions
    - Surfacing organizational bottlenecks
    - Strategic planning and resource allocation

    **Example:**
    ```
    GET /api/v1/portfolio/analytics?organization_id=123&start_date=2025-01-01
    ```

    **Performance:**
    - Target: <5s for 100 sessions
    - Caching recommended for large portfolios

    **Returns:**
    - `total_sessions`: Total sessions in period
    - `active_sessions`: Sessions still in progress
    - `completed_sessions`: Finished sessions
    - `metrics`: Aggregated portfolio metrics
    - `clusters`: Groups of related decisions
    - `bottlenecks`: Stuck or problematic sessions
    - `health_score`: Overall portfolio health (0-1)
    - `strategic_insights`: CEE-generated recommendations
    """
    try:
        # Set default date range if not provided (last 30 days)
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        logger.info(
            "portfolio_analytics_request",
            extra={
                "organization_id": str(organization_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "teams_count": len(teams) if teams else 0,
                "decision_types_count": len(decision_types) if decision_types else 0,
            },
        )

        # Build filters
        filters = PortfolioFilters(
            date_range=DateRange(start=start_date, end=end_date),
            teams=teams,
            decision_types=decision_types,
            status=status,
            min_risk_score=min_risk_score,
        )

        # Initialize analyzer with database session
        analyzer = PortfolioAnalyzer(db=db)

        # Generate portfolio view
        analysis = await analyzer.generate_portfolio_view(
            organization_id=organization_id, filters=filters
        )

        logger.info(
            "portfolio_analytics_completed",
            extra={
                "organization_id": str(organization_id),
                "total_sessions": analysis.total_sessions,
                "health_score": analysis.health_score,
                "cluster_count": len(analysis.clusters),
                "bottleneck_count": len(analysis.bottlenecks),
            },
        )

        return PortfolioAnalysisResponse(analysis=analysis)

    except InsufficientDataError as e:
        logger.warning(
            "insufficient_data_for_portfolio_analytics",
            extra={
                "organization_id": str(organization_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        logger.warning(
            "portfolio_analytics_validation_error",
            extra={
                "organization_id": str(organization_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request parameters: {str(e)}",
        )
    except Exception as e:
        logger.error(
            "portfolio_analytics_error",
            extra={
                "organization_id": str(organization_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate portfolio analytics. Check logs for details.",
        )


@router.get("/health-score", response_model=dict)
async def get_portfolio_health_score(
    organization_id: UUID = Query(..., description="Organization ID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get a quick portfolio health score without full analytics.

    Lightweight endpoint for dashboards and monitoring.
    Returns just the health score and key counts.

    **Performance:**
    - Target: <1s response time
    - Suitable for frequent polling

    **Returns:**
    - `health_score`: 0-1 score (higher is better)
    - `total_sessions`: Total sessions analyzed
    - `high_priority_bottlenecks`: Count of critical issues
    """
    try:
        # Set defaults
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        filters = PortfolioFilters(
            date_range=DateRange(start=start_date, end=end_date)
        )

        analyzer = PortfolioAnalyzer(db=db)
        analysis = await analyzer.generate_portfolio_view(
            organization_id=organization_id, filters=filters
        )

        high_priority_bottlenecks = len(
            [b for b in analysis.bottlenecks if b.severity == "high"]
        )

        return {
            "organization_id": str(organization_id),
            "health_score": analysis.health_score,
            "total_sessions": analysis.total_sessions,
            "active_sessions": analysis.active_sessions,
            "completed_sessions": analysis.completed_sessions,
            "high_priority_bottlenecks": high_priority_bottlenecks,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        }

    except InsufficientDataError:
        return {
            "organization_id": str(organization_id),
            "health_score": 0.0,
            "total_sessions": 0,
            "active_sessions": 0,
            "completed_sessions": 0,
            "high_priority_bottlenecks": 0,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        }
    except Exception as e:
        logger.error(
            "portfolio_health_score_error",
            extra={"organization_id": str(organization_id), "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate health score",
        )
