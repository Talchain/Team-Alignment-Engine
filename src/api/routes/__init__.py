"""API routes."""

from src.api.routes.health import router as health_router
from src.api.routes.sessions import router as sessions_router
from src.api.routes.perspectives import router as perspectives_router
from src.api.routes.analysis import router as analysis_router
from src.api.routes.options import router as options_router
from src.api.routes.concerns import router as concerns_router
from src.api.routes.decisions import router as decisions_router
from src.api.routes.phase_c import router as phase_c_router

__all__ = [
    "health_router",
    "sessions_router",
    "perspectives_router",
    "analysis_router",
    "options_router",
    "concerns_router",
    "decisions_router",
    "phase_c_router",
]
