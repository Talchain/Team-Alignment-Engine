"""API routes for Phase 5 graph analysis and refinement.

Endpoints:
- POST /v1/graph/analyze - Analyze graph and suggest refinements
- POST /v1/graph/apply-suggestions - Apply refinement suggestions
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.storage.database import get_db
from src.storage.outcome_repository import OutcomeRepository
from src.services.causal_modelling_agent import CausalModellingAgent
from src.services.decision_pattern_learner import DecisionPatternLearner
from src.clients.isl_client import ISLClient
from src.models.outcomes import (
    AnalyzeGraphRequestV1,
    AnalyzeGraphResponseV1,
    ApplySuggestionsRequestV1,
    ApplySuggestionsResponseV1,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/graph", tags=["graph_analysis"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_causal_modelling_agent(
    db: AsyncSession = Depends(get_db),
) -> CausalModellingAgent:
    """Get causal modelling agent instance.

    Args:
        db: Database session

    Returns:
        Causal modelling agent
    """
    repository = OutcomeRepository(db)
    pattern_learner = DecisionPatternLearner(repository)
    isl_client = ISLClient()

    return CausalModellingAgent(
        repository=repository,
        pattern_learner=pattern_learner,
        isl_client=isl_client,
    )


# ============================================================================
# GRAPH ANALYSIS ENDPOINTS
# ============================================================================


@router.post("/analyze", response_model=AnalyzeGraphResponseV1)
async def analyze_graph(
    request_body: AnalyzeGraphRequestV1,
    current_user: User = Depends(get_current_user),
    agent: CausalModellingAgent = Depends(get_causal_modelling_agent),
) -> AnalyzeGraphResponseV1:
    """Analyze graph and suggest refinements.

    Analyzes a causal graph and generates refinement suggestions based on:
    - Historical learning insights (reliable paths, unreliable assumptions)
    - Similar decision patterns
    - Causal theory validation

    The agent identifies:
    - Missing nodes or edges that historically predict well
    - Edges based on frequently violated assumptions
    - Missing confounders that improve prediction accuracy
    - Mediator variables that clarify causal mechanisms

    Args:
        request_body: Graph analysis request with graph and options
        current_user: Authenticated user
        agent: Causal modelling agent

    Returns:
        Analysis with refinement suggestions, learning insights, and similar decisions

    Raises:
        HTTPException: If analysis fails
    """
    try:
        logger.info(
            f"User {current_user.user_id} analyzing graph for session {request_body.session_id}"
        )
        return await agent.analyze_graph(request_body)
    except Exception as e:
        logger.error(f"Failed to analyze graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze graph: {str(e)}",
        )


@router.post("/apply-suggestions", response_model=ApplySuggestionsResponseV1)
async def apply_suggestions(
    request_body: ApplySuggestionsRequestV1,
    current_user: User = Depends(get_current_user),
    agent: CausalModellingAgent = Depends(get_causal_modelling_agent),
) -> ApplySuggestionsResponseV1:
    """Apply refinement suggestions to a graph.

    Applies selected refinement suggestions to a causal graph:
    1. Loads current graph from session
    2. Applies graph deltas (add/remove nodes and edges)
    3. Validates refined graph with ISL
    4. Returns refined graph if valid

    Requires explicit user approval for all changes.

    Args:
        request_body: Request with suggestion IDs to apply
        current_user: Authenticated user
        agent: Causal modelling agent

    Returns:
        Refined graph and validation results

    Raises:
        HTTPException: If user approval missing or application fails
    """
    try:
        logger.info(
            f"User {current_user.user_id} applying {len(request_body.suggestion_ids)} "
            f"suggestions to session {request_body.session_id}"
        )

        if not request_body.user_approved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User approval required to apply graph refinement suggestions",
            )

        return await agent.apply_suggestions(request_body)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply suggestions: {str(e)}",
        )
