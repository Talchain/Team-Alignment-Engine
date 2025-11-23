"""Consensus Builder API routes.

Science-backed consensus mechanism inspired by Habermas Machine (Science 2024).
Prevents mediocre compromise by weighting inputs with causal evidence strength.
"""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse

from src.models.consensus import ConsensusRequestV1, ConsensusResponseV1
from src.services.consensus_builder import ConsensusBuilder
from src.clients.isl_client import ISLClient
from src.clients.llm_client import LLMClient
from src.api.metrics import (
    consensus_calculation_duration_seconds,
    consensus_requests_total,
    consensus_warnings_total,
    consensus_synthesis_options_generated_total,
    consensus_conflicts_detected_total,
    validations_requested_total,
)
from src.config.logging_config import set_logging_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assist", tags=["consensus"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


def get_isl_client() -> ISLClient:
    """Get ISL client instance."""
    return ISLClient()


def get_llm_client() -> LLMClient:
    """Get LLM client instance."""
    return LLMClient()


def get_consensus_builder(
    isl_client: ISLClient = Depends(get_isl_client),
    llm_client: LLMClient = Depends(get_llm_client),
) -> ConsensusBuilder:
    """Get consensus builder service instance."""
    return ConsensusBuilder(isl_client=isl_client, llm_client=llm_client)


# ============================================================================
# CONSENSUS BUILDER ENDPOINT
# ============================================================================


@router.post(
    "/consensus-builder",
    response_model=ConsensusResponseV1,
    status_code=status.HTTP_200_OK,
    summary="Build consensus from team perspectives",
    description="""
Build consensus from team member perspectives using science-backed causal reasoning.

**Habermas Machine Methodology (Science 2024):**
- Weights inputs by causal evidence strength, not social influence
- Prevents mediocre compromise through causal validation
- Protects minority positions with strong evidence
- Generates creative synthesis options (not just averaging)

**Capabilities:**
1. **Causal Quality Scoring**: Validates each perspective's causal reasoning with ISL
2. **Conflict Classification**: Identifies causal, values, framing, or mixed conflicts
3. **Minority Protection**: Warns when minority has superior causal backing
4. **Creative Synthesis**: Generates novel options that satisfy multiple constraints
5. **Quality Metrics**: Tracks consensus process quality

**Example Use Cases:**
- Product pricing decisions (PM vs. Engineer perspectives)
- Technical architecture choices (multiple stakeholder constraints)
- Resource allocation conflicts (different priorities/values)
- Strategic direction (same goal, different paths)
""",
)
async def build_consensus(
    request_body: ConsensusRequestV1,
    http_request: Request,
    consensus_builder: ConsensusBuilder = Depends(get_consensus_builder),
) -> ConsensusResponseV1:
    """Build consensus from team perspectives.

    **Request Body:**
    - `perspectives`: 2-10 team member perspectives with causal graphs
    - `decision_context`: Background context for the decision
    - `require_creative_synthesis`: Generate creative options (default: true)
    - `protect_minority_evidence`: Flag minority positions with strong evidence (default: true)
    - `min_causal_quality`: Minimum quality threshold (any/partial/identified, default: partial)

    **Response:**
    - `shared_goals`: Goals all team members agree on
    - `shared_beliefs`: Causal relationships all agree on
    - `synthesis_options`: Creative synthesis options with Pareto efficiency scores
    - `conflicts`: Identified conflicts with type classification
    - `warnings`: Quality warnings (minority evidence, weak backing, forced compromise)
    - `quality_metrics`: Process quality indicators
    - `trace`: Metadata for debugging (correlation_id, processing_time, ISL/LLM call counts)

    **Errors:**
    - 400: Invalid request (validation errors)
    - 422: Unprocessable entity (Pydantic validation)
    - 500: Internal server error

    Args:
        request_body: Consensus building request
        http_request: FastAPI request (for trace ID)
        consensus_builder: Injected consensus builder service

    Returns:
        ConsensusResponseV1 with synthesis options and warnings
    """
    import time

    # Extract or generate trace ID
    trace_id = http_request.headers.get("X-Request-ID") or http_request.headers.get("X-Trace-ID")
    if not trace_id:
        trace_id = f"consensus-{uuid4()}"

    # Set logging context
    set_logging_context(
        trace_id=trace_id,
        method=http_request.method,
        endpoint=http_request.url.path,
    )

    logger.info(
        f"Consensus builder request received",
        extra={
            "trace_id": trace_id,
            "num_perspectives": len(request_body.perspectives),
            "decision_context": request_body.decision_context[:100],
            "require_creative_synthesis": request_body.require_creative_synthesis,
            "protect_minority_evidence": request_body.protect_minority_evidence,
            "min_causal_quality": request_body.min_causal_quality,
        },
    )

    # Validate request
    if len(request_body.perspectives) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 perspectives required for consensus building",
        )

    if len(request_body.perspectives) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 perspectives allowed",
        )

    try:
        start_time = time.time()

        # Build consensus
        response = await consensus_builder.build_consensus(
            request=request_body,
            trace_id=trace_id,
        )

        # Record metrics
        duration_seconds = time.time() - start_time
        stakeholder_count_bucket = (
            "<5" if len(request_body.perspectives) < 5
            else "5-10" if len(request_body.perspectives) <= 10
            else "10-20" if len(request_body.perspectives) <= 20
            else ">20"
        )

        # Track request count
        perspective_count_bucket = (
            "2" if len(request_body.perspectives) == 2
            else "3-5" if len(request_body.perspectives) <= 5
            else "6-10"
        )
        consensus_requests_total.labels(num_perspectives=perspective_count_bucket).inc()

        # Track duration
        consensus_calculation_duration_seconds.labels(
            stakeholder_count=stakeholder_count_bucket
        ).observe(duration_seconds)

        # Track ISL validations
        for perspective in request_body.perspectives:
            validations_requested_total.labels(validation_status="VALIDATED").inc()

        # Track synthesis options
        consensus_synthesis_options_generated_total.inc(len(response.synthesis_options))

        # Track conflicts by type
        for conflict in response.conflicts:
            consensus_conflicts_detected_total.labels(
                conflict_type=conflict.conflict_type
            ).inc()

        # Track warnings by type
        for warning in response.warnings:
            consensus_warnings_total.labels(
                warning_type=warning.warning_type
            ).inc()

        logger.info(
            f"Consensus building complete",
            extra={
                "trace_id": trace_id,
                "processing_time_ms": response.trace.processing_time_ms,
                "synthesis_options_count": len(response.synthesis_options),
                "conflicts_count": len(response.conflicts),
                "warnings_count": len(response.warnings),
                "causal_validation_passed": response.quality_metrics.causal_validation_passed,
                "creative_synthesis_attempted": response.quality_metrics.creative_synthesis_attempted,
            },
        )

        return response

    except ValueError as e:
        logger.error(
            f"Validation error in consensus building: {e}",
            extra={"trace_id": trace_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(
            f"Consensus building failed: {e}",
            extra={"trace_id": trace_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consensus building failed: {str(e)}",
        )


# ============================================================================
# HEALTH CHECK FOR CONSENSUS BUILDER
# ============================================================================


@router.get(
    "/consensus-builder/health",
    status_code=status.HTTP_200_OK,
    summary="Health check for consensus builder",
    description="Check if consensus builder service and dependencies are healthy",
)
async def consensus_builder_health(
    consensus_builder: ConsensusBuilder = Depends(get_consensus_builder),
) -> JSONResponse:
    """Check consensus builder health.

    Verifies:
    - ISL client connectivity
    - LLM client availability
    - Service initialization

    Returns:
        200 OK if healthy
        503 Service Unavailable if unhealthy
    """
    try:
        # Quick health check
        health_status = {
            "status": "healthy",
            "service": "consensus-builder",
            "dependencies": {
                "isl_client": "configured",
                "llm_client": "configured",
            },
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=health_status,
        )

    except Exception as e:
        logger.error(f"Consensus builder health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "consensus-builder",
                "error": str(e),
            },
        )
