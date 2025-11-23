"""API routes."""

from src.api.routes.health import router as health_router
from src.api.routes.sessions import router as sessions_router
from src.api.routes.perspectives import router as perspectives_router
from src.api.routes.analysis import router as analysis_router
from src.api.routes.options import router as options_router
from src.api.routes.concerns import router as concerns_router
from src.api.routes.decisions import router as decisions_router
from src.api.routes.phase_c import router as phase_c_router
from src.api.routes.portfolio import router as portfolio_router
from src.api.routes.collaboration import router as collaboration_router
from src.api.routes.dependencies import router as dependencies_router
from src.api.routes.patterns import router as patterns_router
from src.api.routes.coordination import router as coordination_router
from src.api.routes.analytics import router as advanced_analytics_router
from src.api.routes.plot_orchestration import router as plot_orchestration_router
from src.api.routes.consensus import router as consensus_router

__all__ = [
    "health_router",
    "sessions_router",
    "perspectives_router",
    "analysis_router",
    "options_router",
    "concerns_router",
    "decisions_router",
    "phase_c_router",
    "portfolio_router",
    "collaboration_router",
    "dependencies_router",
    "patterns_router",
    "coordination_router",
    "advanced_analytics_router",
    "plot_orchestration_router",
    "consensus_router",
]
