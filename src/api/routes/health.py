"""Health check endpoint."""

from fastapi import APIRouter, status
from datetime import datetime
from pydantic import BaseModel

from src.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str
    timestamp: str
    dependencies: dict


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns service status and dependency health.
    """
    # TODO: Add actual dependency checks (database, redis, cee, isl)
    dependencies = {
        "database": "connected",  # Placeholder
        "redis": "connected",  # Placeholder
        "cee": "available",  # Placeholder
        "isl": "available",  # Placeholder
    }

    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.utcnow().isoformat(),
        dependencies=dependencies,
    )
