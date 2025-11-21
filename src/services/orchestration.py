"""Orchestration service for PLoT integration (POC v02).

Aggregates Phase D capabilities (D1/D3/D4) into unified response payload.
Implements capability-based filtering and graceful degradation.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.plot import (
    TaeTeamAlignmentPayload,
    AlignmentData,
    SharedGroundData,
    DisagreementData,
    DisagreementAxis,
    DecisionQualityMetrics,
    OrganizationalContext,
    SimilarDecision,
    DecisionDependency,
    AvailabilityStatus,
    CapabilityAvailability,
)
from src.services.session_manager import SessionManager
from src.services.dependency_manager import DecisionDependencyManager
from src.services.pattern_analyzer import PatternAnalyzer
from src.storage.cache import get_cache

logger = logging.getLogger(__name__)


class OrchestrationService:
    """Orchestrates Phase D capabilities for PLoT integration.

    Aggregates data from multiple Phase D services (D1/D3/D4) into
    a unified TaeTeamAlignmentPayload for PLoT's /v1/run endpoint.

    POC v02 Priorities (Q6 decision):
    - D1: Core Alignment (session state, shared ground, disagreements)
    - D3: Decision Dependencies (dependency graph)
    - D4: Organizational Patterns (pattern extraction)

    Deferred capabilities (return unavailable status):
    - D2: Real-Time Collaboration (HTTP polling only)
    - D5: Advanced Analytics (trend forecasting)
    - D6: Cross-Team Coordination (multi-team conflicts)
    """

    def __init__(
        self,
        db: AsyncSession,
        session_manager: Optional[SessionManager] = None,
        dependency_manager: Optional[DecisionDependencyManager] = None,
        pattern_analyzer: Optional[PatternAnalyzer] = None,
    ):
        """Initialize orchestration service.

        Args:
            db: Database session
            session_manager: Optional session manager instance
            dependency_manager: Optional dependency manager instance
            pattern_analyzer: Optional pattern analyzer instance
        """
        self.db = db
        self.session_manager = session_manager or SessionManager()
        self.dependency_manager = dependency_manager or DecisionDependencyManager(db)
        self.pattern_analyzer = pattern_analyzer or PatternAnalyzer(db)

    async def build_alignment_payload(
        self,
        session_id: Optional[str],
        organization_id: str,
        capabilities: List[str],
        context: Dict[str, Any],
        request_id: Optional[str],
    ) -> TaeTeamAlignmentPayload:
        """Build comprehensive alignment payload for PLoT.

        Orchestrates requested capabilities with graceful degradation.

        Args:
            session_id: Session ID (optional - null for portfolio queries)
            organization_id: Organization ID
            capabilities: Requested capabilities list
            context: Additional request context
            request_id: Request ID from PLoT for tracing

        Returns:
            TaeTeamAlignmentPayload with requested capabilities
        """
        start_time = datetime.utcnow()

        logger.info(
            "Building alignment payload",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "organization_id": organization_id,
                "capabilities": capabilities,
            },
        )

        # Track capability results and availability
        capability_results: Dict[str, Any] = {}
        availability_status: Dict[str, bool] = {}
        errors: List[str] = []

        # Execute requested capabilities in parallel for performance
        capability_tasks = {}

        if "core_alignment" in capabilities:
            capability_tasks["core_alignment"] = self._get_core_alignment(session_id)

        if "d3_dependencies" in capabilities:
            capability_tasks["d3_dependencies"] = self._get_dependencies(session_id)

        if "d4_patterns" in capabilities:
            capability_tasks["d4_patterns"] = self._get_patterns(
                session_id, organization_id
            )

        # Execute all capability tasks in parallel
        results = await asyncio.gather(
            *capability_tasks.values(), return_exceptions=True
        )

        # Process results and track availability
        for capability_name, result in zip(capability_tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(
                    f"Capability {capability_name} failed",
                    extra={
                        "request_id": request_id,
                        "capability": capability_name,
                        "error": str(result),
                    },
                    exc_info=result,
                )
                availability_status[capability_name] = False
                errors.append(
                    f"{capability_name} unavailable: {str(result)[:100]}"
                )
            else:
                capability_results[capability_name] = result
                availability_status[capability_name] = True

        # Build alignment data (D1)
        alignment_data = capability_results.get("core_alignment")

        # Build decision quality metrics (if core alignment available)
        decision_quality = None
        if alignment_data and session_id:
            decision_quality = self._build_decision_quality(alignment_data)

        # Build organizational context (D3/D4)
        org_context = OrganizationalContext(
            similar_decisions=capability_results.get("d4_patterns", []),
            dependencies=capability_results.get("d3_dependencies", []),
            trend_insights=None,  # D5 deferred
            conflicts=[],  # D6 deferred
        )

        # Build availability status with feature flags
        availability = self._build_availability_status(
            availability_status, has_errors=len(errors) > 0
        )

        # Determine overall status
        status = "success"
        if errors:
            # Partial failure if any requested capability failed
            requested_count = len([c for c in capabilities if c in capability_tasks])
            failed_count = len([k for k, v in availability_status.items() if not v])

            if failed_count == requested_count:
                status = "error"  # All capabilities failed
            else:
                status = "partial"  # Some capabilities failed

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            "Alignment payload built",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "status": status,
                "duration_ms": duration_ms,
                "capabilities_succeeded": len(capability_results),
                "capabilities_failed": len(errors),
            },
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

    # =========================================================================
    # D1: CORE ALIGNMENT
    # =========================================================================

    async def _get_core_alignment(
        self, session_id: Optional[str]
    ) -> Optional[AlignmentData]:
        """Get core alignment data for session (D1).

        Args:
            session_id: Session ID

        Returns:
            AlignmentData or None if session not found
        """
        if not session_id:
            return None

        if not settings.feature_portfolio_analytics_enabled:
            logger.warning(
                "D1 (portfolio analytics) disabled via feature flag",
                extra={"session_id": session_id},
            )
            return None

        try:
            # Get session from session manager
            try:
                session_uuid = UUID(session_id)
            except ValueError:
                logger.warning(
                    "Invalid session ID format for core alignment",
                    extra={"session_id": session_id},
                )
                return None

            session = await self.session_manager.get(session_uuid)

            if not session:
                logger.warning(
                    "Session not found for core alignment",
                    extra={"session_id": session_id},
                )
                return None

            # Extract alignment data from session
            stakeholder_count = len(session.stakeholders) if session.stakeholders else 0

            # Count perspectives collected (would query perspectives table in real impl)
            perspectives_collected = stakeholder_count  # Simplified

            # Count options proposed (would query options table)
            options_proposed = len(session.options) if hasattr(session, "options") else 0

            # Calculate consensus level from shared ground
            consensus_level = self._calculate_consensus(session)

            # Build shared ground data
            shared_ground = self._build_shared_ground(session)

            # Build disagreement data
            disagreements = self._build_disagreements(session)

            return AlignmentData(
                session_state=self._map_session_status(session.status),
                stakeholder_count=stakeholder_count,
                perspectives_collected=perspectives_collected,
                options_proposed=options_proposed,
                consensus_level=consensus_level,
                shared_ground=shared_ground,
                disagreements=disagreements,
            )

        except Exception as e:
            logger.error(
                "Failed to get core alignment",
                extra={"session_id": session_id, "error": str(e)},
                exc_info=True,
            )
            raise

    def _map_session_status(self, status) -> str:
        """Map session status to alignment state."""
        # Handle SessionStatus enum
        status_str = status.value if hasattr(status, 'value') else str(status)

        status_mapping = {
            "collecting": "collecting_perspectives",
            "analyzing": "proposing_options",
            "deliberating": "deliberating",
            "complete": "decided",
        }
        return status_mapping.get(status_str, "unknown")

    def _calculate_consensus(self, session) -> float:
        """Calculate consensus level from session data.

        Returns value between 0.0 (no consensus) and 1.0 (full consensus).
        """
        # Simplified calculation - would use more sophisticated logic
        if hasattr(session, "shared_ground") and session.shared_ground:
            # If shared ground exists and has content, consensus is higher
            ground_count = len(session.shared_ground.get("common_priorities", []))
            if ground_count >= 3:
                return 0.8
            elif ground_count >= 1:
                return 0.6
            return 0.4
        return 0.5  # Default moderate consensus

    def _build_shared_ground(self, session) -> SharedGroundData:
        """Build shared ground data from session."""
        if hasattr(session, "shared_ground") and session.shared_ground:
            return SharedGroundData(
                summary=session.shared_ground.get(
                    "summary", "Common ground identified"
                ),
                common_goal_weights=session.shared_ground.get("goal_weights", {}),
                aligned_priorities=session.shared_ground.get("common_priorities", []),
            )

        # Default when no shared ground yet
        return SharedGroundData(
            summary="Shared ground analysis pending",
            common_goal_weights={},
            aligned_priorities=[],
        )

    def _build_disagreements(self, session) -> DisagreementData:
        """Build disagreement data from session."""
        axes = []

        if hasattr(session, "disagreement_map") and session.disagreement_map:
            # Extract disagreement axes from disagreement map
            for axis_data in session.disagreement_map.get("axes", []):
                axes.append(
                    DisagreementAxis(
                        dimension=axis_data.get("dimension", "unknown"),
                        stakeholders_involved=axis_data.get("stakeholders", []),
                        severity_score=axis_data.get("severity", 0.5),
                        description=axis_data.get("description", ""),
                    )
                )

            return DisagreementData(
                summary=session.disagreement_map.get(
                    "summary", "Disagreements identified"
                ),
                axes=axes,
            )

        # Default when no disagreements yet
        return DisagreementData(
            summary="Disagreement analysis pending",
            axes=[],
        )

    def _build_decision_quality(
        self, alignment_data: AlignmentData
    ) -> DecisionQualityMetrics:
        """Build decision quality metrics from alignment data.

        Args:
            alignment_data: Core alignment data

        Returns:
            DecisionQualityMetrics
        """
        # Calculate health score from consensus and disagreement severity
        health_score = alignment_data.consensus_level

        # Adjust for disagreement severity
        if alignment_data.disagreements.axes:
            avg_severity = sum(
                axis.severity_score for axis in alignment_data.disagreements.axes
            ) / len(alignment_data.disagreements.axes)
            health_score = health_score * (1.0 - (avg_severity * 0.3))

        # Identify risk flags
        risk_flags = []
        if alignment_data.consensus_level < 0.5:
            risk_flags.append("Low consensus")
        if len(alignment_data.disagreements.axes) > 3:
            risk_flags.append("Multiple disagreement axes")
        if alignment_data.stakeholder_count < 3:
            risk_flags.append("Limited stakeholder input")

        # Simplified metrics - would integrate with ISL/CEE in real implementation
        return DecisionQualityMetrics(
            health_score=max(0.0, min(1.0, health_score)),
            risk_flags=risk_flags,
            causally_validated=False,  # Would check ISL validation status
            assumption_strength=0.7,  # Placeholder
            minority_concerns=[],  # Would query from Phase C data
        )

    # =========================================================================
    # D3: DEPENDENCIES
    # =========================================================================

    async def _get_dependencies(
        self, session_id: Optional[str]
    ) -> List[DecisionDependency]:
        """Get decision dependencies for session (D3).

        Args:
            session_id: Session ID

        Returns:
            List of DecisionDependency objects
        """
        if not session_id:
            return []

        if not settings.feature_decision_dependencies_enabled:
            logger.warning(
                "D3 (dependencies) disabled via feature flag",
                extra={"session_id": session_id},
            )
            return []

        try:
            try:
                session_uuid = UUID(session_id)
            except ValueError:
                logger.warning(
                    "Invalid session ID format for dependencies",
                    extra={"session_id": session_id},
                )
                return []

            # Get dependencies for this session
            dependencies_list = await self.dependency_manager.get_dependencies_for_session(
                session_uuid
            )

            # Convert to DecisionDependency models for payload
            result = []
            for dep in dependencies_list:
                result.append(
                    DecisionDependency(
                        dependent_session_id=str(dep.target_session_id),
                        dependency_type=(
                            "blocks"
                            if dep.dependency_type == "blocks"
                            else "informs"
                        ),
                        team="Unknown Team",  # Would lookup team info
                        description=dep.description,
                        status="pending"
                        if not dep.resolved_at
                        else "resolved",
                    )
                )

            logger.info(
                "Dependencies retrieved",
                extra={
                    "session_id": session_id,
                    "dependency_count": len(result),
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to get dependencies",
                extra={"session_id": session_id, "error": str(e)},
                exc_info=True,
            )
            raise

    # =========================================================================
    # D4: ORGANIZATIONAL PATTERNS
    # =========================================================================

    async def _get_patterns(
        self, session_id: Optional[str], organization_id: str
    ) -> List[SimilarDecision]:
        """Get organizational patterns for session (D4).

        Args:
            session_id: Session ID
            organization_id: Organization ID

        Returns:
            List of SimilarDecision objects (patterns)
        """
        if not session_id:
            return []

        if not settings.feature_organizational_patterns_enabled:
            logger.warning(
                "D4 (patterns) disabled via feature flag",
                extra={"session_id": session_id},
            )
            return []

        try:
            try:
                session_uuid = UUID(session_id)
                org_uuid = UUID(organization_id)
            except ValueError:
                logger.warning(
                    "Invalid UUID format for patterns",
                    extra={"session_id": session_id, "organization_id": organization_id},
                )
                return []

            # Extract patterns for this session
            patterns = await self.pattern_analyzer.extract_patterns(
                organization_id=org_uuid,
                retrospectives=[],  # Would query retrospectives from DB
            )

            # Convert to SimilarDecision models (top 5 most similar)
            result = []
            for pattern in patterns[:5]:  # Limit to top 5
                # Map pattern to similar decision format
                result.append(
                    SimilarDecision(
                        session_id=f"session-{pattern.pattern_id}",
                        outcome="success"
                        if pattern.pattern_type == "success_pattern"
                        else "neutral",
                        similarity=pattern.confidence,
                        key_lessons=pattern.recommended_actions[:3],  # Top 3 lessons
                        timestamp=datetime.utcnow(),  # Would use actual timestamp
                    )
                )

            logger.info(
                "Patterns retrieved",
                extra={
                    "session_id": session_id,
                    "pattern_count": len(result),
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to get patterns",
                extra={
                    "session_id": session_id,
                    "organization_id": organization_id,
                    "error": str(e)},
                exc_info=True,
            )
            raise

    # =========================================================================
    # AVAILABILITY STATUS
    # =========================================================================

    def _build_availability_status(
        self, capability_status: Dict[str, bool], has_errors: bool
    ) -> AvailabilityStatus:
        """Build availability status with feature flags.

        Args:
            capability_status: Dict of capability name -> success bool
            has_errors: Whether any capability failed

        Returns:
            AvailabilityStatus with per-capability flags
        """
        # Build capability availability based on feature flags and execution results
        capabilities = CapabilityAvailability(
            d1_portfolio_analytics=settings.feature_portfolio_analytics_enabled
            and capability_status.get("core_alignment", True),
            d2_realtime_collaboration=settings.feature_realtime_collaboration_enabled,  # Always False for POC v02
            d3_decision_dependencies=settings.feature_decision_dependencies_enabled
            and capability_status.get("d3_dependencies", True),
            d4_organizational_patterns=settings.feature_organizational_patterns_enabled
            and capability_status.get("d4_patterns", True),
            d5_advanced_analytics=settings.feature_advanced_analytics_enabled,  # Deferred
            d6_cross_team_coordination=settings.feature_cross_team_coordination_enabled,  # Deferred
        )

        # Determine degradation status
        degraded = has_errors
        degradation_reason = None
        if degraded:
            failed_capabilities = [
                k for k, v in capability_status.items() if not v
            ]
            degradation_reason = (
                f"Some capabilities unavailable: {', '.join(failed_capabilities)}"
            )

        return AvailabilityStatus(
            tae_available=True,  # Service is running
            capabilities=capabilities,
            degraded=degraded,
            degradation_reason=degradation_reason,
        )
