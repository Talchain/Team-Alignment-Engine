"""Enhanced health check endpoints for TAE.

Provides three levels of health checking:
- /health/live: Liveness probe (is service running?)
- /health/ready: Readiness probe (can serve traffic?)
- /health/metrics: Detailed health metrics

Returns 503 when degraded with X-Olumi-Degraded header.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, status, Response
from fastapi.responses import JSONResponse

from src.config import settings
from src.storage.database import engine
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


# ============================================================================
# LIVENESS PROBE
# ============================================================================


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Minimal health check - is the service running?",
)
async def liveness_probe() -> JSONResponse:
    """
    Liveness probe endpoint.

    Returns 200 if service is running. This is a minimal check
    that doesn't verify dependencies.

    Used by: Kubernetes liveness probes, monitoring systems

    Returns:
        200 OK if service is alive
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": settings.service_name,
            "version": settings.service_version,
        },
    )


# ============================================================================
# READINESS PROBE
# ============================================================================


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Deep health check - can the service handle traffic?",
)
async def readiness_probe(response: Response) -> JSONResponse:
    """
    Readiness probe endpoint.

    Checks all critical dependencies:
    - PostgreSQL database
    - Redis cache
    - (Optional) External services

    Returns:
        200 OK if all dependencies are healthy
        503 Service Unavailable if any critical dependency is down

    Headers:
        X-Olumi-Degraded: Reason for degraded mode (if applicable)
    """
    health_status = {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {},
        "degraded": False,
        "degraded_components": [],
    }

    # Check PostgreSQL
    db_healthy, db_latency = await _check_database()
    health_status["checks"]["database"] = {
        "status": "healthy" if db_healthy else "unhealthy",
        "latency_ms": db_latency,
    }

    # Check Redis
    redis_healthy, redis_latency = await _check_redis()
    health_status["checks"]["redis"] = {
        "status": "healthy" if redis_healthy else "unhealthy",
        "latency_ms": redis_latency,
    }

    # Determine overall status
    critical_checks = ["database"]  # Database is critical
    optional_checks = ["redis"]  # Redis degradation is acceptable

    # Check if any critical components are unhealthy
    critical_unhealthy = any(
        not health_status["checks"][check].get("status") == "healthy"
        for check in critical_checks
        if check in health_status["checks"]
    )

    # Check if any optional components are unhealthy (degraded mode)
    optional_unhealthy = any(
        not health_status["checks"][check].get("status") == "healthy"
        for check in optional_checks
        if check in health_status["checks"]
    )

    if critical_unhealthy:
        # Critical failure - not ready
        health_status["status"] = "not_ready"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        # Identify failed components
        failed_components = [
            check
            for check in critical_checks
            if check in health_status["checks"]
            and health_status["checks"][check]["status"] != "healthy"
        ]
        response.headers["X-Olumi-Degraded"] = ",".join(failed_components)

    elif optional_unhealthy:
        # Degraded but operational
        health_status["status"] = "degraded"
        health_status["degraded"] = True

        degraded_components = [
            check
            for check in optional_checks
            if check in health_status["checks"]
            and health_status["checks"][check]["status"] != "healthy"
        ]
        health_status["degraded_components"] = degraded_components
        response.headers["X-Olumi-Degraded"] = ",".join(degraded_components)

    return JSONResponse(
        status_code=response.status_code,
        content=health_status,
    )


# ============================================================================
# DETAILED HEALTH METRICS
# ============================================================================


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Detailed health metrics",
    description="Comprehensive health metrics with component details",
)
async def health_metrics() -> JSONResponse:
    """
    Detailed health metrics endpoint.

    Provides comprehensive health information including:
    - All dependency statuses
    - Response time metrics
    - System resource usage
    - Aggregated health score

    Returns:
        200 OK with detailed metrics
    """
    metrics = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": {
            "name": settings.service_name,
            "version": settings.service_version,
            "environment": settings.environment,
        },
        "dependencies": {},
        "health_score": 0.0,
        "degraded_mode": False,
        "degraded_reasons": [],
        "phase_d_capabilities": _get_phase_d_capabilities(),
    }

    # Check all dependencies
    db_healthy, db_latency = await _check_database()
    redis_healthy, redis_latency = await _check_redis()
    cee_healthy, cee_latency = await _check_external_service("CEE", settings.cee_base_url)
    isl_healthy, isl_latency = await _check_external_service("ISL", settings.isl_base_url)

    metrics["dependencies"] = {
        "database": {
            "status": "healthy" if db_healthy else "unhealthy",
            "latency_ms": db_latency,
            "critical": True,
        },
        "redis": {
            "status": "healthy" if redis_healthy else "unhealthy",
            "latency_ms": redis_latency,
            "critical": False,
        },
        "cee": {
            "status": "healthy" if cee_healthy else "unhealthy",
            "latency_ms": cee_latency,
            "critical": False,
        },
        "isl": {
            "status": "healthy" if isl_healthy else "unhealthy",
            "latency_ms": isl_latency,
            "critical": False,
        },
    }

    # Calculate health score (0.0 - 1.0)
    component_scores = {
        "database": 1.0 if db_healthy else 0.0,
        "redis": 1.0 if redis_healthy else 0.5,  # Degraded mode acceptable
        "cee": 1.0 if cee_healthy else 0.7,
        "isl": 1.0 if isl_healthy else 0.7,
    }

    # Weighted average (database has higher weight)
    weights = {"database": 0.4, "redis": 0.2, "cee": 0.2, "isl": 0.2}
    metrics["health_score"] = sum(
        component_scores[comp] * weights[comp] for comp in weights
    )

    # Determine degraded mode
    if not redis_healthy:
        metrics["degraded_mode"] = True
        metrics["degraded_reasons"].append("redis_unavailable")
    if not cee_healthy:
        metrics["degraded_mode"] = True
        metrics["degraded_reasons"].append("cee_unavailable")
    if not isl_healthy:
        metrics["degraded_mode"] = True
        metrics["degraded_reasons"].append("isl_unavailable")

    # Add database pool metrics (if available)
    metrics["database_pool"] = _get_database_pool_metrics()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=metrics,
    )


# ============================================================================
# LEGACY /health ENDPOINT (for backward compatibility)
# ============================================================================


@router.get(
    "",
    summary="Legacy health check",
    description="Backward-compatible health check (redirects to /health/ready)",
)
async def legacy_health_check(response: Response) -> JSONResponse:
    """
    Legacy health check endpoint for backward compatibility.

    Delegates to /health/ready endpoint.
    """
    return await readiness_probe(response)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def _check_database() -> tuple[bool, float]:
    """
    Check PostgreSQL database health.

    Returns:
        Tuple of (healthy: bool, latency_ms: float)
    """
    import time

    try:
        start = time.time()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = (time.time() - start) * 1000
        return True, round(latency_ms, 2)
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return False, 0.0


async def _check_redis() -> tuple[bool, float]:
    """
    Check Redis cache health.

    Returns:
        Tuple of (healthy: bool, latency_ms: float)
    """
    import time

    try:
        from src.storage.cache import redis_client

        start = time.time()
        await redis_client.ping()
        latency_ms = (time.time() - start) * 1000
        return True, round(latency_ms, 2)
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return False, 0.0


async def _check_external_service(
    service_name: str, base_url: str, timeout: float = 5.0
) -> tuple[bool, float]:
    """
    Check external service health.

    Args:
        service_name: Service name (for logging)
        base_url: Service base URL
        timeout: Request timeout in seconds

    Returns:
        Tuple of (healthy: bool, latency_ms: float)
    """
    import time
    import httpx

    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Try health endpoint
            response = await client.get(f"{base_url}/health", timeout=timeout)
            latency_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                return True, round(latency_ms, 2)
            else:
                logger.warning(
                    f"{service_name} health check returned {response.status_code}"
                )
                return False, round(latency_ms, 2)

    except httpx.TimeoutException:
        logger.warning(f"{service_name} health check timed out after {timeout}s")
        return False, timeout * 1000
    except Exception as e:
        logger.warning(f"{service_name} health check failed: {e}")
        return False, 0.0


def _get_database_pool_metrics() -> Dict[str, Any]:
    """
    Get database connection pool metrics.

    Returns:
        Dictionary of pool metrics
    """
    try:
        pool = engine.pool

        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
        }
    except Exception as e:
        logger.warning(f"Failed to get database pool metrics: {e}")
        return {
            "size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "total_connections": 0,
        }


def _get_phase_d_capabilities() -> Dict[str, bool]:
    """Get Phase D feature flag status."""
    return {
        "d1_portfolio_analytics": settings.feature_portfolio_analytics_enabled,
        "d2_realtime_collaboration": settings.feature_realtime_collaboration_enabled,
        "d3_decision_dependencies": settings.feature_decision_dependencies_enabled,
        "d4_organizational_patterns": settings.feature_organizational_patterns_enabled,
        "d5_advanced_analytics": settings.feature_advanced_analytics_enabled,
        "d6_cross_team_coordination": settings.feature_cross_team_coordination_enabled,
    }
