"""Health check endpoint with Phase D service validation."""

from fastapi import APIRouter, status, Depends
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from src.config import settings
from src.storage.database import get_db
from src.storage.cache import get_cache

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str
    environment: str
    timestamp: str
    dependencies: Dict[str, Any]
    phase_d_capabilities: Dict[str, bool]


async def check_database(db: AsyncSession) -> Dict[str, Any]:
    """Check PostgreSQL database connection."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "connected", "type": "postgresql"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "error": str(e)}


async def check_redis() -> Dict[str, Any]:
    """Check Redis connection."""
    try:
        redis = await get_cache()
        await redis.ping()
        return {"status": "connected", "type": "redis"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "error", "error": str(e)}


def get_phase_d_capabilities() -> Dict[str, bool]:
    """Get Phase D feature flag status."""
    return {
        "d1_portfolio_analytics": settings.feature_portfolio_analytics_enabled,
        "d2_realtime_collaboration": settings.feature_realtime_collaboration_enabled,
        "d3_decision_dependencies": settings.feature_decision_dependencies_enabled,
        "d4_organizational_patterns": settings.feature_organizational_patterns_enabled,
        "d5_advanced_analytics": settings.feature_advanced_analytics_enabled,
        "d6_cross_team_coordination": settings.feature_cross_team_coordination_enabled,
    }


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Enhanced health check endpoint with Phase D validation.

    Validates:
    - PostgreSQL database connection
    - Redis cache connection
    - Phase D feature flags
    - Service configuration

    Returns service status, version, and all dependency health.
    """
    # Check database
    db_status = await check_database(db)

    # Check Redis
    redis_status = await check_redis()

    # Get Phase D capabilities
    phase_d_status = get_phase_d_capabilities()

    # Determine overall status
    overall_status = "ok"
    if db_status.get("status") != "connected":
        overall_status = "degraded"
    if redis_status.get("status") != "connected":
        overall_status = "degraded"

    dependencies = {
        "database": db_status,
        "redis": redis_status,
        "cee": {
            "status": "mock" if settings.cee_use_mock else "configured",
            "base_url": settings.cee_base_url
        },
        "isl": {
            "status": "configured",
            "base_url": settings.isl_base_url
        }
    }

    return HealthResponse(
        status=overall_status,
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.environment,
        timestamp=datetime.utcnow().isoformat(),
        dependencies=dependencies,
        phase_d_capabilities=phase_d_status,
    )
