"""Orchestration service for PLoT integration (POC v02).

Aggregates Phase D capabilities (D1/D3/D4) into unified response payload.
Implements capability-based filtering and graceful degradation.

Phase 4: Added resilience patterns (timeouts + circuit breakers) to prevent
cascading failures and ensure <5s p95 latency target.
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
    TrendInsights,
    CrossTeamConflict,
    CollaborationData,
    RecentAction,
    AvailabilityStatus,
    CapabilityAvailability,
)
from src.services.session_manager import SessionManager
from src.services.dependency_manager import DecisionDependencyManager
from src.services.pattern_analyzer import PatternAnalyzer
from src.services.analytics_engine import AdvancedAnalyticsEngine
from src.services.coordination_manager import CrossTeamCoordinator
from src.services.collaboration_manager import CollaborationManager
from src.storage.cache import get_cache
from src.utils.profiling import profile_async, profile_block
from src.utils.resilience import (
    get_circuit_breaker,
    CircuitBreakerOpenError,
    TimeoutError as ResilienceTimeoutError,
)

logger = logging.getLogger(__name__)

# Per-capability timeout configuration (seconds)
# Allocated from 5s total budget, accounting for parallel execution
CAPABILITY_TIMEOUTS = {
    "core_alignment": 1.0,  # D1: Fast session lookup
    "d2_collaboration": 0.5,  # D2: Redis-backed, should be fast
    "d3_dependencies": 1.5,  # D3: Graph queries, moderate complexity
    "d4_patterns": 2.0,  # D4: Pattern analysis (with caching)
    "d5_analytics": 3.0,  # D5: Most expensive (even with caching)
    "d6_coordination": 1.5,  # D6: Conflict detection (optimized bulk queries)
}


class OrchestrationService:
    """Orchestrates Phase D capabilities for PLoT integration.

    Aggregates data from multiple Phase D services (D1/D3/D4/D5/D6/D2) into
    a unified TaeTeamAlignmentPayload for PLoT's /v1/run endpoint.

    Phase 3: All capabilities available (feature-flag gated):
    - D1: Core Alignment (session state, shared ground, disagreements)
    - D2: Real-Time Collaboration (HTTP polling + WebSocket stubs)
    - D3: Decision Dependencies (dependency graph)
    - D4: Organizational Patterns (pattern extraction)
    - D5: Advanced Analytics (trend analysis, forecasting, benchmarks)
    - D6: Cross-Team Coordination (conflict detection, resolution)
    """

    def __init__(
        self,
        db: AsyncSession,
        session_manager: Optional[SessionManager] = None,
        dependency_manager: Optional[DecisionDependencyManager] = None,
        pattern_analyzer: Optional[PatternAnalyzer] = None,
        analytics_engine: Optional[AdvancedAnalyticsEngine] = None,
        coordination_manager: Optional[CrossTeamCoordinator] = None,
        collaboration_manager: Optional[CollaborationManager] = None,
    ):
        """Initialize orchestration service.

        Args:
            db: Database session
            session_manager: Optional session manager instance
            dependency_manager: Optional dependency manager instance
            pattern_analyzer: Optional pattern analyzer instance
            analytics_engine: Optional analytics engine instance (D5)
            coordination_manager: Optional coordination manager instance (D6)
            collaboration_manager: Optional collaboration manager instance (D2)
        """
        self.db = db
        self.session_manager = session_manager or SessionManager()
        self.dependency_manager = dependency_manager or DecisionDependencyManager(db)
        self.pattern_analyzer = pattern_analyzer or PatternAnalyzer(db)
        self.analytics_engine = analytics_engine or AdvancedAnalyticsEngine(db)
        self.coordination_manager = coordination_manager or CrossTeamCoordinator(db)
        self.collaboration_manager = collaboration_manager or CollaborationManager(db)

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

        # Execute requested capabilities in parallel with timeouts
        capability_tasks = {}

        if "core_alignment" in capabilities:
            timeout = CAPABILITY_TIMEOUTS["core_alignment"]
            capability_tasks["core_alignment"] = asyncio.wait_for(
                self._get_core_alignment(session_id),
                timeout=timeout,
            )

        if "d3_dependencies" in capabilities:
            timeout = CAPABILITY_TIMEOUTS["d3_dependencies"]
            capability_tasks["d3_dependencies"] = asyncio.wait_for(
                self._get_dependencies(session_id),
                timeout=timeout,
            )

        if "d4_patterns" in capabilities:
            timeout = CAPABILITY_TIMEOUTS["d4_patterns"]
            capability_tasks["d4_patterns"] = asyncio.wait_for(
                self._get_patterns(session_id, organization_id),
                timeout=timeout,
            )

        if "d5_analytics" in capabilities:
            # D5 uses circuit breaker pattern due to high latency
            timeout = CAPABILITY_TIMEOUTS["d5_analytics"]
            capability_tasks["d5_analytics"] = asyncio.wait_for(
                self._get_analytics_with_circuit_breaker(organization_id),
                timeout=timeout,
            )

        if "d6_coordination" in capabilities:
            timeout = CAPABILITY_TIMEOUTS["d6_coordination"]
            capability_tasks["d6_coordination"] = asyncio.wait_for(
                self._get_conflicts(session_id, organization_id),
                timeout=timeout,
            )

        if "d2_collaboration" in capabilities:
            timeout = CAPABILITY_TIMEOUTS["d2_collaboration"]
            capability_tasks["d2_collaboration"] = asyncio.wait_for(
                self._get_collaboration(session_id),
                timeout=timeout,
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

        # Build organizational context (D3/D4/D5/D6)
        org_context = OrganizationalContext(
            similar_decisions=capability_results.get("d4_patterns", []),
            dependencies=capability_results.get("d3_dependencies", []),
            trend_insights=capability_results.get("d5_analytics"),  # D5
            conflicts=capability_results.get("d6_coordination", []),  # D6
        )

        # Build collaboration data (D2)
        collaboration_data = capability_results.get("d2_collaboration")

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
            collaboration=collaboration_data,  # D2 (HTTP polling + WebSocket stubs)
            availability=availability,
        )

    # =========================================================================
    # D1: CORE ALIGNMENT
    # =========================================================================

    @profile_async("d1_core_alignment", capability="d1")
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

    @profile_async("d3_dependencies", capability="d3")
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

    @profile_async("d4_patterns", capability="d4")
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
            d2_realtime_collaboration=settings.feature_realtime_collaboration_enabled
            and capability_status.get("d2_collaboration", True),
            d3_decision_dependencies=settings.feature_decision_dependencies_enabled
            and capability_status.get("d3_dependencies", True),
            d4_organizational_patterns=settings.feature_organizational_patterns_enabled
            and capability_status.get("d4_patterns", True),
            d5_advanced_analytics=settings.feature_advanced_analytics_enabled
            and capability_status.get("d5_analytics", True),
            d6_cross_team_coordination=settings.feature_cross_team_coordination_enabled
            and capability_status.get("d6_coordination", True)
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

    # =========================================================================
    # D5: ADVANCED ANALYTICS
    # =========================================================================

    async def _get_analytics_with_circuit_breaker(
        self, organization_id: str
    ) -> Optional[TrendInsights]:
        """Get analytics with circuit breaker pattern for fault tolerance.

        Wraps _get_analytics with circuit breaker to prevent cascading failures
        when D5 analytics service is experiencing high error rates.

        Args:
            organization_id: Organization ID

        Returns:
            TrendInsights or None (fallback if circuit is open)
        """
        # Get or create circuit breaker for D5 analytics
        circuit_breaker = get_circuit_breaker(
            name="d5_analytics",
            failure_threshold=0.5,  # Open after 50% failure rate
            min_requests=5,  # Need at least 5 requests to evaluate
            recovery_timeout=30.0,  # Test recovery after 30 seconds
        )

        try:
            # Execute with circuit breaker protection
            result = await circuit_breaker.call(
                self._get_analytics,
                organization_id,
                fallback=None,  # Return None if circuit is open
            )
            return result

        except CircuitBreakerOpenError as e:
            logger.warning(
                "D5 analytics circuit breaker open - returning fallback",
                extra={
                    "organization_id": organization_id,
                    "circuit_state": circuit_breaker.state,
                    "failure_rate": circuit_breaker.failure_rate,
                },
            )
            return None  # Graceful degradation
        except Exception as e:
            logger.error(
                "D5 analytics failed through circuit breaker",
                extra={"organization_id": organization_id, "error": str(e)},
                exc_info=True,
            )
            raise

    @profile_async("d5_analytics", capability="d5")
    async def _get_analytics(self, organization_id: str) -> Optional[TrendInsights]:
        """Get advanced analytics trend insights (D5).

        Args:
            organization_id: Organization ID

        Returns:
            TrendInsights with trend analysis and forecasts, or None if disabled
        """
        if not settings.feature_advanced_analytics_enabled:
            logger.warning(
                "D5 (advanced analytics) disabled via feature flag",
                extra={"organization_id": organization_id},
            )
            return None

        try:
            org_uuid = UUID(organization_id)

            # Analyze decision velocity trend
            velocity_trend = await self.analytics_engine.analyze_trends(
                organization_id=org_uuid,
                metric_name="decision_time",
                lookback_days=90,
            )

            # Analyze quality trend
            quality_trend = await self.analytics_engine.analyze_trends(
                organization_id=org_uuid,
                metric_name="quality_score",
                lookback_days=90,
            )

            # Calculate velocity comparison
            # Baseline: 10 days average (industry standard)
            avg_decision_time = sum(p["value"] for p in velocity_trend.data_points) / len(
                velocity_trend.data_points
            )
            baseline = 10.0
            velocity_pct = ((avg_decision_time - baseline) / baseline) * 100

            if abs(velocity_pct) < 5:
                velocity_description = "on pace with baseline"
            elif velocity_pct > 0:
                velocity_description = f"{abs(velocity_pct):.0f}% slower than baseline"
            else:
                velocity_description = f"{abs(velocity_pct):.0f}% faster than baseline"

            # Map quality trend direction
            quality_trend_status = quality_trend.trend_direction
            if quality_trend_status == "increasing":
                quality_trend_str = "improving"
            elif quality_trend_status == "decreasing":
                quality_trend_str = "declining"
            else:
                quality_trend_str = "stable"

            # Build forecast data
            forecast_data = {
                "velocity_forecast": velocity_trend.forecast_30days[:7],  # Next 7 days
                "quality_forecast": quality_trend.forecast_30days[:7],
                "confidence_intervals": velocity_trend.confidence_intervals[:7],
                "trend_strength": velocity_trend.trend_strength,
            }

            logger.info(
                "Analytics retrieved",
                extra={
                    "organization_id": organization_id,
                    "velocity_trend": velocity_trend.trend_direction,
                    "quality_trend": quality_trend_str,
                },
            )

            return TrendInsights(
                organization_decision_velocity=velocity_description,
                quality_trend=quality_trend_str,
                forecast=forecast_data,
            )

        except ValueError:
            logger.warning(
                "Invalid organization ID format for analytics",
                extra={"organization_id": organization_id},
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get analytics",
                extra={"organization_id": organization_id, "error": str(e)},
                exc_info=True,
            )
            raise

    # =========================================================================
    # D6: CROSS-TEAM COORDINATION
    # =========================================================================

    @profile_async("d6_conflicts", capability="d6")
    async def _get_conflicts(
        self, session_id: Optional[str], organization_id: str
    ) -> List[CrossTeamConflict]:
        """Get cross-team conflicts (D6).

        Args:
            session_id: Session ID
            organization_id: Organization ID

        Returns:
            List of CrossTeamConflict objects
        """
        if not settings.feature_cross_team_coordination_enabled:
            logger.warning(
                "D6 (cross-team coordination) disabled via feature flag",
                extra={"organization_id": organization_id},
            )
            return []

        if not session_id:
            return []

        try:
            try:
                session_uuid = UUID(session_id)
                org_uuid = UUID(organization_id)
            except ValueError:
                logger.warning(
                    "Invalid UUID format for conflicts",
                    extra={"session_id": session_id, "organization_id": organization_id},
                )
                return []

            # Detect conflicts for this session
            detected_conflicts = await self.coordination_manager.detect_conflicts(
                organization_id=org_uuid,
                session_ids=[session_uuid],
            )

            # Convert to CrossTeamConflict models for payload
            result = []
            for conflict in detected_conflicts:
                # Find the conflicting session (not the current one)
                conflicting_session_ids = [
                    sid for sid in conflict.session_ids if sid != session_uuid
                ]

                for conflicting_sid in conflicting_session_ids:
                    result.append(
                        CrossTeamConflict(
                            conflicting_session_id=str(conflicting_sid),
                            conflict_type=conflict.conflict_type,
                            severity=conflict.severity,
                            resolution_suggestion=conflict.resolution_suggestions[0]
                            if conflict.resolution_suggestions
                            else None,
                        )
                    )

            logger.info(
                "Conflicts retrieved",
                extra={
                    "session_id": session_id,
                    "conflict_count": len(result),
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to get conflicts",
                extra={
                    "session_id": session_id,
                    "organization_id": organization_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    # =========================================================================
    # D2: REAL-TIME COLLABORATION
    # =========================================================================

    @profile_async("d2_collaboration", capability="d2")
    async def _get_collaboration(
        self, session_id: Optional[str]
    ) -> Optional[CollaborationData]:
        """Get collaboration data (D2) - HTTP polling mode.

        Args:
            session_id: Session ID

        Returns:
            CollaborationData with active stakeholders and recent actions
        """
        if not settings.feature_realtime_collaboration_enabled:
            logger.warning(
                "D2 (collaboration) disabled via feature flag",
                extra={"session_id": session_id},
            )
            return None

        if not session_id:
            return None

        try:
            try:
                session_uuid = UUID(session_id)
            except ValueError:
                logger.warning(
                    "Invalid session ID format for collaboration",
                    extra={"session_id": session_id},
                )
                return None

            # Get active presence (HTTP polling - last 5 minutes)
            active_users = await self.collaboration_manager.get_active_presence(
                session_uuid, time_window_seconds=300
            )

            # Get recent actions (last 10)
            recent_actions_data = await self.collaboration_manager.get_recent_actions(
                session_uuid, limit=10
            )

            # Convert to RecentAction models
            recent_actions = []
            for action in recent_actions_data:
                recent_actions.append(
                    RecentAction(
                        user_id=str(action.user_id),
                        action_type=action.action_type,
                        timestamp=action.timestamp,
                        metadata=action.metadata,
                    )
                )

            logger.info(
                "Collaboration data retrieved",
                extra={
                    "session_id": session_id,
                    "active_users": len(active_users),
                    "recent_actions": len(recent_actions),
                },
            )

            return CollaborationData(
                active_stakeholders=[str(uid) for uid in active_users],
                recent_actions=recent_actions,
            )

        except Exception as e:
            logger.error(
                "Failed to get collaboration data",
                extra={"session_id": session_id, "error": str(e)},
                exc_info=True,
            )
            raise
