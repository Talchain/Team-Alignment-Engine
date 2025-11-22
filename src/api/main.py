"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

from src.config import settings
from src.api.middleware import (
    RequestIDMiddleware,
    setup_error_handlers,
)
from src.api.middleware.redis_rate_limiter import RedisRateLimiterMiddleware
from src.api.routes import (
    health_router,
    sessions_router,
    perspectives_router,
    analysis_router,
    options_router,
    concerns_router,
    decisions_router,
    phase_c_router,
    portfolio_router,
    collaboration_router,
    dependencies_router,
    patterns_router,
    coordination_router,
    advanced_analytics_router,
    plot_orchestration_router,
)
from src.api.metrics import MetricsMiddleware, metrics_endpoint
from src.storage import init_db, init_cache

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Team Alignment Engine",
    description="Causally-validated team deliberation service",
    version=settings.service_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RedisRateLimiterMiddleware)
app.add_middleware(MetricsMiddleware)

# Set up error handlers
setup_error_handlers(app)

# Include routers
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(perspectives_router)
app.include_router(analysis_router)
app.include_router(options_router)
app.include_router(concerns_router)
app.include_router(decisions_router)
app.include_router(phase_c_router)  # Phase C: Intelligent Assistance
app.include_router(portfolio_router)  # Phase D1: Portfolio Analytics
app.include_router(collaboration_router)  # Phase D2: Real-time Collaboration
app.include_router(dependencies_router)  # Phase D3: Decision Dependencies
app.include_router(patterns_router)  # Phase D4: Organizational Patterns
app.include_router(advanced_analytics_router)  # Phase D5: Advanced Analytics
app.include_router(coordination_router)  # Phase D6: Cross-Team Coordination
app.include_router(plot_orchestration_router)  # PLoT Integration (POC v02)

# Add metrics endpoint
app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], tags=["monitoring"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    logger.info(f"Environment: {settings.environment}")

    try:
        # Validate production secrets on startup (fail fast if missing)
        if settings.environment == "production":
            from src.config.secrets import validate_production_secrets
            validate_production_secrets()
            logger.info("Production secrets validated")

        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Initialize cache
        await init_cache()
        logger.info("Cache initialized")

        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down application")
    # Close connections, cleanup resources
    logger.info("Shutdown complete")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }
