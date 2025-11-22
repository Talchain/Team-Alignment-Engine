"""Health check command for all TAE dependencies."""

import asyncio
import time
from typing import Dict
import httpx
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import redis.asyncio as redis

from src.config import settings


async def check_health(deep: bool = False) -> Dict:
    """
    Check health of all TAE dependencies.

    Args:
        deep: Perform deep health checks (slower but more thorough)

    Returns:
        Health status for each component
    """
    health_status = {}

    # Check PostgreSQL
    health_status["postgresql"] = await _check_postgresql(deep)

    # Check Redis
    health_status["redis"] = await _check_redis(deep)

    # Check CEE service
    health_status["cee"] = await _check_http_service(
        "CEE",
        settings.cee_base_url,
        settings.cee_api_key,
        deep
    )

    # Check ISL service
    health_status["isl"] = await _check_http_service(
        "ISL",
        settings.isl_base_url,
        settings.isl_api_key,
        deep
    )

    # Check TAE API itself
    health_status["tae_api"] = await _check_tae_api(deep)

    return health_status


async def _check_postgresql(deep: bool) -> Dict:
    """Check PostgreSQL database connection."""
    try:
        start = time.perf_counter()

        engine = create_async_engine(
            settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
            pool_pre_ping=True,
        )

        async with engine.connect() as conn:
            # Basic check
            await conn.execute(text("SELECT 1"))

            if deep:
                # Check table existence
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
                )
                table_count = result.scalar()

                if table_count == 0:
                    return {
                        "status": "degraded",
                        "message": "No tables found - run migrations",
                        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    }

        await engine.dispose()

        return {
            "status": "healthy",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def _check_redis(deep: bool) -> Dict:
    """Check Redis connection."""
    try:
        start = time.perf_counter()

        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        # Basic check
        await redis_client.ping()

        if deep:
            # Test read/write
            test_key = "tae:health:test"
            await redis_client.set(test_key, "ok", ex=60)
            value = await redis_client.get(test_key)
            if value != "ok":
                return {
                    "status": "degraded",
                    "message": "Redis read/write failed",
                }

        await redis_client.aclose()

        return {
            "status": "healthy",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def _check_http_service(name: str, base_url: str, api_key: str, deep: bool) -> Dict:
    """Check HTTP service availability."""
    try:
        start = time.perf_counter()

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try health endpoint first
            try:
                response = await client.get(
                    f"{base_url}/health",
                    headers={"X-API-Key": api_key} if api_key else {},
                )
                response.raise_for_status()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Health endpoint doesn't exist, try base URL
                    response = await client.get(
                        base_url,
                        headers={"X-API-Key": api_key} if api_key else {},
                    )
                    response.raise_for_status()
                else:
                    raise

        return {
            "status": "healthy",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        }

    except Exception as e:
        # Check if it's a mock service (development)
        if "mock" in base_url.lower() or settings.cee_use_mock:
            return {
                "status": "degraded",
                "message": f"Using mock {name} (development mode)",
            }

        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def _check_tae_api(deep: bool) -> Dict:
    """Check TAE API is running."""
    try:
        start = time.perf_counter()

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            response.raise_for_status()

            health_data = response.json()

        return {
            "status": "healthy" if health_data.get("status") == "ok" else "degraded",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "version": health_data.get("version"),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": "TAE API not running. Start with: uvicorn src.api.main:app",
        }
