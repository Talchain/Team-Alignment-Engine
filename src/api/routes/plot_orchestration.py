"""PLoT orchestration endpoint for TAE POC v02 integration.

This is an INTERNAL-ONLY endpoint for PLoT → TAE communication.
Never exposed directly to UI.

PLoT Team Decisions (2025-11-21):
- Q1: HTTP polling only (no WebSocket proxy)
- Q2: Capability-based filtering required
- Q3: TAE caches internally (current approach)
- Q4: Echo PLoT's X-Request-Id header for tracing
- Q5: API key authentication
- Q6: POC v02 priorities = D1/D3/D4 (MUST), D2/D5/D6 (DEFERRED)
- Q7: Partial failures with availability metadata
- Q8: Hybrid testing (contract + integration)
"""

from fastapi import APIRouter, HTTPException, Header, Depends, status
from fastapi.responses import JSONResponse
from typing import Optional
import logging
from datetime import datetime

from src.config import settings
from src.models.plot import (
    PlotAlignmentRequest,
    TaeTeamAlignmentPayload,
    AvailabilityStatus,
    CapabilityAvailability,
)

router = APIRouter(prefix="/api/v1/plot", tags=["plot-integration"])
logger = logging.getLogger(__name__)


# ============================================================================
# AUTHENTICATION
# ============================================================================


async def validate_plot_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Validate PLoT internal API key.

    This is service-to-service authentication. PLoT must provide
    the correct API key in X-API-Key header.

    Args:
        x_api_key: API key from request header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is invalid
    """
    if not settings.plot_internal_api_key:
        logger.error(
            "PLoT internal API key not configured",
            extra={"config_var": "PLOT_INTERNAL_API_KEY"},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PLoT integration not configured",
        )

    if x_api_key != settings.plot_internal_api_key:
        logger.warning(
            "Invalid PLoT API key attempt",
            extra={"provided_key_prefix": x_api_key[:8] if x_api_key else "empty"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return x_api_key


# ============================================================================
# ORCHESTRATION ENDPOINT
# ============================================================================


@router.post(
    "/alignment-session",
    response_model=TaeTeamAlignmentPayload,
    status_code=status.HTTP_200_OK,
    summary="Get TAE alignment session data (PLoT orchestration)",
    description="""
    Internal-only endpoint for PLoT → TAE integration.

    Returns comprehensive team alignment payload including:
    - Core alignment data (session state, shared ground, disagreements)
    - Decision quality metrics (health score, risk flags, minority concerns)
    - Organizational context (D1/D3/D4 capabilities)

    **Authentication**: Service-to-service API key via X-API-Key header
    **Tracing**: Echoes X-Request-Id for distributed tracing
    **Capability Filtering**: Only returns requested capabilities (Q2 decision)
    **Graceful Degradation**: Partial failures indicated via availability metadata (Q7 decision)
    """,
)
async def get_alignment_session(
    request: PlotAlignmentRequest,
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
    api_key: str = Depends(validate_plot_api_key),
) -> TaeTeamAlignmentPayload:
    """Get team alignment session data for PLoT orchestration.

    This endpoint aggregates Phase D capabilities (D1/D3/D4 for POC v02)
    into a unified response for PLoT's /v1/run endpoint.

    **POC v02 Capabilities** (Q6 decision):
    - core_alignment: Session state, shared ground, disagreements
    - d1_portfolio: Portfolio analytics (MUST HAVE)
    - d3_dependencies: Decision dependencies (MUST HAVE)
    - d4_patterns: Organizational patterns (MUST HAVE)

    **Deferred for POC v02**:
    - d2_collaboration: Real-time collaboration (use HTTP polling)
    - d5_analytics: Advanced analytics (trend forecasting)
    - d6_coordination: Cross-team coordination

    Args:
        request: PLoT alignment request with session_id, org_id, capabilities
        x_request_id: Optional request ID from PLoT for tracing (Q4 decision)
        api_key: Validated API key (dependency injection)

    Returns:
        TaeTeamAlignmentPayload with requested capabilities

    Raises:
        HTTPException: If request is invalid or TAE service unavailable
    """
    start_time = datetime.utcnow()

    logger.info(
        "PLoT orchestration request received",
        extra={
            "request_id": x_request_id,
            "session_id": request.session_id,
            "organization_id": request.organization_id,
            "capabilities": request.capabilities,
        },
    )

    # Check if PLoT deployment mode is enabled
    if not settings.plot_deployment_mode:
        logger.warning(
            "PLoT orchestration endpoint called but plot_deployment_mode=False",
            extra={"request_id": x_request_id},
        )
        # Allow the call but log the warning (supports hybrid deployments)

    try:
        # TODO: Import OrchestrationService once implemented
        # from src.services.orchestration import OrchestrationService
        # orchestration_service = OrchestrationService()

        # TODO: Build alignment payload from OrchestrationService
        # payload = await orchestration_service.build_alignment_payload(
        #     session_id=request.session_id,
        #     organization_id=request.organization_id,
        #     capabilities=request.capabilities,
        #     context=request.context,
        #     request_id=x_request_id,
        # )

        # TEMPORARY: Return mock payload for Milestone 1
        # This will be replaced with real OrchestrationService in next step
        payload = _build_mock_payload(
            session_id=request.session_id,
            organization_id=request.organization_id,
            request_id=x_request_id,
            capabilities=request.capabilities,
        )

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info(
            "PLoT orchestration request completed",
            extra={
                "request_id": x_request_id,
                "session_id": request.session_id,
                "duration_ms": duration_ms,
                "capabilities_returned": len(request.capabilities),
                "degraded": payload.availability.degraded,
            },
        )

        return payload

    except Exception as e:
        logger.error(
            "PLoT orchestration request failed",
            extra={
                "request_id": x_request_id,
                "session_id": request.session_id,
                "error": str(e),
            },
            exc_info=True,
        )

        # Return error payload with availability status (Q7 decision)
        return TaeTeamAlignmentPayload(
            session_id=request.session_id,
            organization_id=request.organization_id,
            timestamp=datetime.utcnow(),
            version=settings.service_version,
            request_id=x_request_id,
            alignment=None,
            decision_quality=None,
            organizational_context={
                "similar_decisions": [],
                "dependencies": [],
                "conflicts": [],
            },
            collaboration=None,
            availability=AvailabilityStatus(
                tae_available=False,
                capabilities=CapabilityAvailability(
                    d1_portfolio_analytics=False,
                    d2_realtime_collaboration=False,
                    d3_decision_dependencies=False,
                    d4_organizational_patterns=False,
                    d5_advanced_analytics=False,
                    d6_cross_team_coordination=False,
                ),
                degraded=True,
                degradation_reason=f"TAE service error: {str(e)[:100]}",
            ),
        )


# ============================================================================
# HELPER FUNCTIONS (TEMPORARY FOR MILESTONE 1)
# ============================================================================


def _build_mock_payload(
    session_id: Optional[str],
    organization_id: str,
    request_id: Optional[str],
    capabilities: list[str],
) -> TaeTeamAlignmentPayload:
    """Build mock payload for Milestone 1 testing.

    This is TEMPORARY scaffolding. Will be replaced with OrchestrationService.

    Args:
        session_id: Session ID (optional)
        organization_id: Organization ID
        request_id: Request ID for tracing
        capabilities: Requested capabilities

    Returns:
        Mock TaeTeamAlignmentPayload
    """
    from src.models.plot import (
        AlignmentData,
        SharedGroundData,
        DisagreementData,
        DisagreementAxis,
        DecisionQualityMetrics,
        OrganizationalContext,
        SimilarDecision,
        DecisionDependency,
    )

    logger.info(
        "Building mock payload (TEMPORARY - Milestone 1)",
        extra={
            "session_id": session_id,
            "capabilities": capabilities,
        },
    )

    # Check which capabilities are requested (Q2 decision: capability filtering)
    include_core = "core_alignment" in capabilities
    include_d1 = "d1_portfolio" in capabilities
    include_d3 = "d3_dependencies" in capabilities
    include_d4 = "d4_patterns" in capabilities

    # Build alignment data if core_alignment requested
    alignment_data = None
    if include_core and session_id:
        alignment_data = AlignmentData(
            session_state="deliberating",
            stakeholder_count=3,
            perspectives_collected=3,
            options_proposed=2,
            consensus_level=0.7,
            shared_ground=SharedGroundData(
                summary="All stakeholders prioritize user experience and speed",
                common_goal_weights={
                    "user_satisfaction": 0.9,
                    "performance": 0.85,
                },
                aligned_priorities=["Fast load times", "Mobile support"],
            ),
            disagreements=DisagreementData(
                summary="Technical implementation approach differs",
                axes=[
                    DisagreementAxis(
                        dimension="feasibility",
                        stakeholders_involved=["PM", "Engineer"],
                        severity_score=0.6,
                        description="PM wants MVP in 2 weeks, Engineer needs 4 weeks",
                    )
                ],
            ),
        )

    # Build decision quality (always included if session exists)
    decision_quality = None
    if session_id:
        decision_quality = DecisionQualityMetrics(
            health_score=0.75,
            risk_flags=["Timeline pressure"],
            causally_validated=True,
            assumption_strength=0.68,
            minority_concerns=[],
        )

    # Build organizational context
    org_context = OrganizationalContext(
        similar_decisions=[
            SimilarDecision(
                session_id="session-old123",
                outcome="success",
                similarity=0.82,
                key_lessons=["Early prototyping saved time", "Clear requirements helped"],
                timestamp=datetime(2025, 10, 15, 14, 0, 0),
            )
        ]
        if include_d4
        else [],
        dependencies=[
            DecisionDependency(
                dependent_session_id="session-api456",
                dependency_type="blocks",
                team="Platform Team",
                description="Waiting for API design decision",
                status="pending",
            )
        ]
        if include_d3
        else [],
        trend_insights=None,  # D5 deferred
        conflicts=[],  # D6 deferred
    )

    # Build availability status (Q6 decision: D1/D3/D4 = true, D2/D5/D6 = false)
    availability = AvailabilityStatus(
        tae_available=True,
        capabilities=CapabilityAvailability(
            d1_portfolio_analytics=settings.feature_portfolio_analytics_enabled,
            d2_realtime_collaboration=settings.feature_realtime_collaboration_enabled,
            d3_decision_dependencies=settings.feature_decision_dependencies_enabled,
            d4_organizational_patterns=settings.feature_organizational_patterns_enabled,
            d5_advanced_analytics=settings.feature_advanced_analytics_enabled,
            d6_cross_team_coordination=settings.feature_cross_team_coordination_enabled,
        ),
        degraded=False,
        degradation_reason=None,
    )

    return TaeTeamAlignmentPayload(
        session_id=session_id,
        organization_id=organization_id,
        timestamp=datetime.utcnow(),
        version=settings.service_version,
        request_id=request_id,
        alignment=alignment_data,
        decision_quality=decision_quality,
        organizational_context=org_context,
        collaboration=None,  # D2 deferred (Q1 decision: HTTP polling only)
        availability=availability,
    )
