"""Portfolio analytics service for Phase D1."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from src.models.portfolio import (
    PortfolioAnalysis,
    PortfolioFilters,
    PortfolioMetrics,
    DecisionCluster,
    DecisionBottleneck,
    DateRange,
)
from src.models.session import AlignmentSession
from src.models.enums import SessionStatus
from src.clients.cee_client import CEEClient

logger = logging.getLogger(__name__)


class InsufficientDataError(Exception):
    """Raised when insufficient data for analysis."""
    pass


class PortfolioAnalyzer:
    """Analyze multiple decisions for portfolio-level insights."""

    def __init__(
        self,
        db: AsyncSession,
        cee_client: Optional[CEEClient] = None
    ):
        """Initialize portfolio analyzer."""
        self.db = db
        self.cee_client = cee_client or CEEClient()

    async def generate_portfolio_view(
        self,
        organization_id: UUID,
        filters: PortfolioFilters
    ) -> PortfolioAnalysis:
        """
        Generate portfolio analytics across multiple sessions.

        Process:
        1. Query sessions matching filters
        2. Aggregate decision metrics
        3. Identify decision clusters
        4. Surface bottlenecks
        5. Calculate portfolio health score
        6. Generate strategic insights via CEE
        """
        # Get sessions
        sessions = await self._get_sessions(organization_id, filters)

        if not sessions:
            raise InsufficientDataError("No sessions found matching filters")

        # Count active and completed
        active_sessions = len([s for s in sessions if s.status != SessionStatus.COMPLETE])
        completed_sessions = len([s for s in sessions if s.status == SessionStatus.COMPLETE])

        # Aggregate metrics
        metrics = await self._aggregate_metrics(sessions)

        # Identify clusters
        clusters = self._identify_clusters(sessions)

        # Detect bottlenecks
        bottlenecks = self._detect_bottlenecks(sessions)

        # Calculate health score
        health_score = self._calculate_health(metrics, bottlenecks, active_sessions)

        # Generate strategic insights via CEE
        insights = await self._generate_insights(
            sessions_count=len(sessions),
            metrics=metrics,
            clusters=clusters,
            bottlenecks=bottlenecks,
            health_score=health_score
        )

        return PortfolioAnalysis(
            organization_id=organization_id,
            period=filters.date_range,
            total_sessions=len(sessions),
            active_sessions=active_sessions,
            completed_sessions=completed_sessions,
            metrics=metrics,
            clusters=clusters,
            bottlenecks=bottlenecks,
            health_score=health_score,
            strategic_insights=insights,
            generated_at=datetime.utcnow()
        )

    async def _get_sessions(
        self,
        organization_id: UUID,
        filters: PortfolioFilters
    ) -> List[AlignmentSession]:
        """Query sessions matching filters."""
        conditions = [
            AlignmentSession.created_at >= filters.date_range.start,
            AlignmentSession.created_at <= filters.date_range.end
        ]

        if filters.teams:
            conditions.append(AlignmentSession.team_id.in_(filters.teams))

        if filters.decision_types:
            conditions.append(AlignmentSession.decision_type.in_(filters.decision_types))

        if filters.status:
            conditions.append(AlignmentSession.status.in_(filters.status))

        query = select(AlignmentSession).where(and_(*conditions))

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        return list(sessions)

    async def _aggregate_metrics(
        self,
        sessions: List[AlignmentSession]
    ) -> PortfolioMetrics:
        """Aggregate metrics across sessions."""
        completed_sessions = [s for s in sessions if s.status == SessionStatus.COMPLETE]

        if not completed_sessions:
            # Return defaults for incomplete sessions
            return PortfolioMetrics(
                avg_decision_time_days=0.0,
                avg_quality_rating=0.0,
                avg_satisfaction_score=0.0,
                total_options_proposed=0,
                total_ai_options_used=0,
                causal_validation_success_rate=0.0,
                minority_concern_validation_rate=0.0
            )

        # Calculate average decision time
        decision_times = []
        for session in completed_sessions:
            if session.completed_at and session.created_at:
                delta = session.completed_at - session.created_at
                decision_times.append(delta.total_seconds() / 86400)  # Convert to days

        avg_decision_time = sum(decision_times) / len(decision_times) if decision_times else 0.0

        # For now, use placeholder values for metrics we don't have yet
        # These would come from retrospective data and option/validation tables
        return PortfolioMetrics(
            avg_decision_time_days=avg_decision_time,
            avg_quality_rating=7.5,  # Placeholder - would query retrospectives
            avg_satisfaction_score=8.0,  # Placeholder - would query retrospectives
            total_options_proposed=len(completed_sessions) * 4,  # Placeholder
            total_ai_options_used=len(completed_sessions) * 1,  # Placeholder
            causal_validation_success_rate=0.85,  # Placeholder
            minority_concern_validation_rate=0.20  # Placeholder
        )

    def _identify_clusters(
        self,
        sessions: List[AlignmentSession]
    ) -> List[DecisionCluster]:
        """Identify clusters of related decisions."""
        # Group by decision type
        clusters_by_type: Dict[str, List[AlignmentSession]] = defaultdict(list)

        for session in sessions:
            clusters_by_type[session.decision_type].append(session)

        clusters = []
        for decision_type, type_sessions in clusters_by_type.items():
            if len(type_sessions) >= 2:  # Only cluster if 2+ sessions
                # Extract common stakeholders
                stakeholder_counts: Dict[str, int] = defaultdict(int)
                for session in type_sessions:
                    for stakeholder in session.stakeholders:
                        user_id = stakeholder.get("user_id", "")
                        stakeholder_counts[user_id] += 1

                # Get stakeholders appearing in >50% of sessions
                threshold = len(type_sessions) * 0.5
                common_stakeholders = [
                    uid for uid, count in stakeholder_counts.items()
                    if count >= threshold
                ]

                clusters.append(DecisionCluster(
                    cluster_id=f"{decision_type}_cluster",
                    theme=decision_type.replace("_", " ").title(),
                    session_ids=[s.session_id for s in type_sessions],
                    avg_complexity=0.6,  # Placeholder - would calculate from data
                    common_stakeholders=common_stakeholders[:5]  # Top 5
                ))

        return clusters

    def _detect_bottlenecks(
        self,
        sessions: List[AlignmentSession]
    ) -> List[DecisionBottleneck]:
        """Detect bottlenecks in decision flow."""
        bottlenecks = []
        now = datetime.utcnow()

        for session in sessions:
            # Stuck session detection
            if session.status == SessionStatus.DELIBERATING:
                days_deliberating = (now - session.created_at).days

                if days_deliberating >= 12:
                    bottlenecks.append(DecisionBottleneck(
                        bottleneck_type="stuck_session",
                        session_id=session.session_id,
                        description=f"Session stuck in deliberating for {days_deliberating} days",
                        severity="high" if days_deliberating >= 20 else "medium",
                        recommendation="Assign facilitator or trigger AI synthesis"
                    ))
                elif days_deliberating >= 7:
                    bottlenecks.append(DecisionBottleneck(
                        bottleneck_type="stuck_session",
                        session_id=session.session_id,
                        description=f"Session deliberating for {days_deliberating} days",
                        severity="medium",
                        recommendation="Check if stakeholders need additional information"
                    ))

        return bottlenecks

    def _calculate_health(
        self,
        metrics: PortfolioMetrics,
        bottlenecks: List[DecisionBottleneck],
        active_sessions: int
    ) -> float:
        """Calculate overall portfolio health score."""
        # Start with base score
        health = 0.8

        # Penalize slow decisions
        if metrics.avg_decision_time_days > 7:
            health -= 0.1
        if metrics.avg_decision_time_days > 14:
            health -= 0.1

        # Penalize bottlenecks
        high_severity_bottlenecks = len([b for b in bottlenecks if b.severity == "high"])
        health -= (high_severity_bottlenecks * 0.05)

        medium_severity_bottlenecks = len([b for b in bottlenecks if b.severity == "medium"])
        health -= (medium_severity_bottlenecks * 0.02)

        # Reward good validation rates
        if metrics.causal_validation_success_rate > 0.85:
            health += 0.05

        # Clamp to [0, 1]
        return max(0.0, min(1.0, health))

    async def _generate_insights(
        self,
        sessions_count: int,
        metrics: PortfolioMetrics,
        clusters: List[DecisionCluster],
        bottlenecks: List[DecisionBottleneck],
        health_score: float
    ) -> List[str]:
        """Generate strategic insights via CEE."""
        try:
            # Prepare request payload
            request_payload = {
                "sessions_count": sessions_count,
                "metrics": {
                    "avg_decision_time_days": metrics.avg_decision_time_days,
                    "avg_quality_rating": metrics.avg_quality_rating,
                    "causal_validation_success_rate": metrics.causal_validation_success_rate,
                },
                "clusters": [
                    {"theme": c.theme, "size": len(c.session_ids)}
                    for c in clusters
                ],
                "bottleneck_count": len(bottlenecks),
                "health_score": health_score
            }

            logger.info(
                "Generating portfolio insights via CEE",
                extra={"sessions_count": sessions_count, "health_score": health_score}
            )

            # Call CEE for insights generation
            response = await self.cee_client.client.post(
                f"{self.cee_client.base_url}/assist/v1/generate-insights",
                json=request_payload,
                headers={
                    "X-API-Key": self.cee_client.api_key,
                    "Content-Type": "application/json",
                }
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("insights", self._generate_fallback_insights(metrics, bottlenecks))
            else:
                logger.warning(f"CEE insights generation failed: {response.status_code}")
                return self._generate_fallback_insights(metrics, bottlenecks)

        except Exception as e:
            logger.error(f"Failed to generate CEE insights: {e}", exc_info=True)
            return self._generate_fallback_insights(metrics, bottlenecks)

    def _generate_fallback_insights(
        self,
        metrics: PortfolioMetrics,
        bottlenecks: List[DecisionBottleneck]
    ) -> List[str]:
        """Generate basic insights when CEE is unavailable."""
        insights = []

        # Decision speed insight
        if metrics.avg_decision_time_days >= 7:
            insights.append(
                f"Average decision time is {metrics.avg_decision_time_days:.1f} days. "
                "Consider enabling AI assistance to accelerate deliberation."
            )
        else:
            insights.append(
                f"Decision velocity is healthy at {metrics.avg_decision_time_days:.1f} days average."
            )

        # Validation insight
        if metrics.causal_validation_success_rate > 0.8:
            insights.append(
                f"Strong causal validation rate ({metrics.causal_validation_success_rate:.0%}). "
                "Teams are building decisions on solid evidence."
            )

        # Bottleneck insight
        if bottlenecks:
            high_severity = len([b for b in bottlenecks if b.severity == "high"])
            if high_severity > 0:
                insights.append(
                    f"{high_severity} high-priority bottleneck(s) detected. "
                    "Review stuck sessions to unblock progress."
                )

        # AI usage insight
        if metrics.total_ai_options_used > 0:
            ai_rate = metrics.total_ai_options_used / max(metrics.total_options_proposed, 1)
            if ai_rate > 0.2:
                insights.append(
                    f"Teams using AI option generation ({ai_rate:.0%} adoption). "
                    "This typically correlates with faster decisions."
                )

        return insights if insights else [
            "Insufficient data for detailed insights. Continue using the platform to build analytics."
        ]
