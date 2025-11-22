"""Pattern analyzer service for Phase D4."""

import logging
import json
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.portfolio import (
    DecisionPattern,
    OrganizationalPatterns,
)
from src.models.session import AlignmentSession
from src.models.enums import SessionStatus, DecisionType
from src.clients.cee_client import CEEClient
from src.storage.cache import get_cache
from src.utils.profiling import profile_block

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """Analyze decision patterns to identify organizational learning opportunities."""

    def __init__(self, db: AsyncSession, cee_client: Optional[CEEClient] = None, cache=None):
        """
        Initialize pattern analyzer.

        Args:
            db: Database session
            cee_client: Optional CEE client for pattern analysis
            cache: Optional Redis cache instance (default: get_cache())
        """
        self.db = db
        self.cee_client = cee_client or CEEClient()
        self.cache = cache or get_cache()
        self._cache_ttl = 86400  # 24 hours (patterns change slowly)

    async def extract_patterns(
        self,
        organization_id: UUID,
        lookback_days: int = 90,
        min_sample_size: int = 3,
    ) -> OrganizationalPatterns:
        """
        Extract decision patterns from historical data.

        Implements Redis caching with 24-hour TTL to avoid recomputing
        expensive pattern analysis on every request.

        Args:
            organization_id: Organization ID
            lookback_days: Days of history to analyze
            min_sample_size: Minimum sessions per pattern

        Returns:
            Organizational patterns with success/failure insights
        """
        try:
            # Build cache key
            cache_key = f"tae:patterns:{organization_id}:lookback_{lookback_days}"

            # 1. Check cache first
            async with profile_block("d4_cache_lookup", capability="d4", cache_hit=None):
                cached_data = await self.cache.get(cache_key)

            if cached_data:
                async with profile_block("d4_cache_deserialize", capability="d4", cache_hit=True):
                    try:
                        data = json.loads(cached_data)
                        logger.info(
                            "pattern_cache_hit",
                            extra={
                                "organization_id": str(organization_id),
                                "cache_key": cache_key,
                            },
                        )
                        # Reconstruct OrganizationalPatterns from cached data
                        return OrganizationalPatterns(
                            organization_id=UUID(data["organization_id"]),
                            analysis_period_days=data["analysis_period_days"],
                            total_sessions_analyzed=data["total_sessions_analyzed"],
                            patterns=[
                                DecisionPattern(**p) for p in data["patterns"]
                            ],
                            success_factors=data["success_factors"],
                            failure_indicators=data["failure_indicators"],
                            recommendations=data["recommendations"],
                            generated_at=datetime.fromisoformat(data["generated_at"]),
                        )
                    except Exception as e:
                        logger.warning(
                            "pattern_cache_deserialize_failed",
                            extra={"error": str(e)},
                        )
                        # Fall through to recompute

            # 2. Cache miss - compute patterns
            logger.info(
                "pattern_cache_miss",
                extra={
                    "organization_id": str(organization_id),
                    "cache_key": cache_key,
                },
            )

            async with profile_block("d4_pattern_extraction", capability="d4", cache_hit=False):
                # Get completed sessions in lookback period
                cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

                query = select(AlignmentSession).where(
                    and_(
                        AlignmentSession.status == SessionStatus.COMPLETE,
                        AlignmentSession.completed_at >= cutoff_date,
                    )
                )
                result = await self.db.execute(query)
                sessions = list(result.scalars().all())

                if len(sessions) < min_sample_size:
                    logger.warning(
                        "insufficient_sessions_for_patterns",
                        extra={
                            "organization_id": str(organization_id),
                            "session_count": len(sessions),
                            "min_required": min_sample_size,
                        },
                    )

                # Extract patterns by decision type
                patterns = await self._identify_patterns(sessions, min_sample_size)

                # Identify success factors
                success_factors = self._identify_success_factors(sessions, patterns)

                # Identify failure indicators
                failure_indicators = self._identify_failure_indicators(sessions, patterns)

                # Generate recommendations via CEE
                recommendations = await self._generate_recommendations(
                    patterns, success_factors, failure_indicators
                )

                result_obj = OrganizationalPatterns(
                    organization_id=organization_id,
                    analysis_period_days=lookback_days,
                    total_sessions_analyzed=len(sessions),
                    patterns=patterns,
                    success_factors=success_factors,
                    failure_indicators=failure_indicators,
                    recommendations=recommendations,
                    generated_at=datetime.utcnow(),
                )

            # 3. Store in cache
            async with profile_block("d4_cache_store", capability="d4", cache_hit=False):
                try:
                    # Serialize to JSON
                    cache_data = {
                        "organization_id": str(result_obj.organization_id),
                        "analysis_period_days": result_obj.analysis_period_days,
                        "total_sessions_analyzed": result_obj.total_sessions_analyzed,
                        "patterns": [
                            {
                                "pattern_id": p.pattern_id,
                                "pattern_type": p.pattern_type,
                                "decision_type": p.decision_type,
                                "sample_size": p.sample_size,
                                "description": p.description,
                                "common_characteristics": p.common_characteristics,
                                "avg_metrics": p.avg_metrics,
                                "confidence": p.confidence,
                                "recommendations": p.recommendations,
                            }
                            for p in result_obj.patterns
                        ],
                        "success_factors": result_obj.success_factors,
                        "failure_indicators": result_obj.failure_indicators,
                        "recommendations": result_obj.recommendations,
                        "generated_at": result_obj.generated_at.isoformat(),
                    }

                    await self.cache.setex(
                        cache_key,
                        self._cache_ttl,
                        json.dumps(cache_data),
                    )

                    logger.info(
                        "pattern_cached",
                        extra={
                            "organization_id": str(organization_id),
                            "cache_key": cache_key,
                            "ttl": self._cache_ttl,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        "failed_to_cache_patterns",
                        extra={"error": str(e)},
                    )
                    # Non-fatal - return computed result anyway

            return result_obj

        except Exception as e:
            logger.error(
                "failed_to_extract_patterns",
                extra={
                    "organization_id": str(organization_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def _identify_patterns(
        self, sessions: List[AlignmentSession], min_sample_size: int
    ) -> List[DecisionPattern]:
        """
        Identify patterns by decision type.

        Args:
            sessions: List of completed sessions
            min_sample_size: Minimum sessions per pattern

        Returns:
            List of identified patterns
        """
        patterns = []

        # Group sessions by decision type
        by_type: Dict[str, List[AlignmentSession]] = defaultdict(list)
        for session in sessions:
            by_type[session.decision_type].append(session)

        # Analyze each decision type
        for decision_type, type_sessions in by_type.items():
            if len(type_sessions) < min_sample_size:
                continue

            # Calculate success metrics (using placeholder values until retrospective data available)
            # In production, would query actual retrospective ratings
            avg_time_days = sum(
                (s.completed_at - s.created_at).days
                for s in type_sessions
                if s.completed_at
            ) / len(type_sessions)

            # Classify as success/failure based on decision time
            # Fast decisions (< 7 days) = success, slow (> 14 days) = failure
            pattern_type = (
                "success" if avg_time_days < 7
                else "failure" if avg_time_days > 14
                else "neutral"
            )

            # Identify common characteristics
            characteristics = self._extract_characteristics(type_sessions)

            # Calculate confidence based on sample size
            confidence = min(0.95, 0.5 + (len(type_sessions) / 50) * 0.45)

            # Generate recommendations
            recommendations = self._generate_pattern_recommendations(
                decision_type, pattern_type, characteristics, avg_time_days
            )

            patterns.append(
                DecisionPattern(
                    pattern_id=f"{decision_type}_{pattern_type}",
                    pattern_type=pattern_type,
                    decision_type=decision_type,
                    sample_size=len(type_sessions),
                    description=f"{decision_type} decisions typically take {avg_time_days:.1f} days",
                    common_characteristics=characteristics,
                    avg_metrics={
                        "avg_time_days": avg_time_days,
                        "avg_stakeholders": sum(
                            len(s.stakeholders) for s in type_sessions
                        )
                        / len(type_sessions),
                        # Placeholder metrics - would use actual retrospective data
                        "avg_quality": 7.5 if pattern_type == "success" else 6.0,
                        "avg_satisfaction": 8.0 if pattern_type == "success" else 6.5,
                    },
                    confidence=confidence,
                    recommendations=recommendations,
                )
            )

        return patterns

    def _extract_characteristics(
        self, sessions: List[AlignmentSession]
    ) -> List[str]:
        """
        Extract common characteristics from sessions.

        Args:
            sessions: List of sessions

        Returns:
            List of characteristic descriptions
        """
        characteristics = []

        # Analyze stakeholder count
        avg_stakeholders = sum(len(s.stakeholders) for s in sessions) / len(sessions)
        if avg_stakeholders < 4:
            characteristics.append("Small team size (< 4 stakeholders)")
        elif avg_stakeholders > 8:
            characteristics.append("Large team size (> 8 stakeholders)")

        # Analyze alignment mode distribution
        mode_counts = defaultdict(int)
        for session in sessions:
            mode_counts[session.alignment_mode] += 1

        dominant_mode = max(mode_counts.items(), key=lambda x: x[1])[0]
        if mode_counts[dominant_mode] / len(sessions) > 0.7:
            characteristics.append(f"Predominantly {dominant_mode} mode")

        # Analyze decision timeline
        avg_time = sum(
            (s.completed_at - s.created_at).days
            for s in sessions
            if s.completed_at
        ) / len(sessions)

        if avg_time < 3:
            characteristics.append("Rapid decision cycle (< 3 days)")
        elif avg_time > 14:
            characteristics.append("Extended deliberation period (> 14 days)")

        return characteristics

    def _identify_success_factors(
        self,
        sessions: List[AlignmentSession],
        patterns: List[DecisionPattern],
    ) -> List[str]:
        """
        Identify factors correlated with success.

        Args:
            sessions: All sessions
            patterns: Identified patterns

        Returns:
            List of success factors
        """
        success_factors = []

        # Find success patterns
        success_patterns = [p for p in patterns if p.pattern_type == "success"]

        if success_patterns:
            # Fast decision-making
            fast_decisions = sum(
                1 for p in success_patterns if p.avg_metrics["avg_time_days"] < 5
            )
            if fast_decisions / len(success_patterns) > 0.5:
                success_factors.append(
                    "Fast decision cycles (< 5 days) correlate with positive outcomes"
                )

            # Right-sized teams
            optimal_team = sum(
                1
                for p in success_patterns
                if 4 <= p.avg_metrics["avg_stakeholders"] <= 7
            )
            if optimal_team / len(success_patterns) > 0.5:
                success_factors.append(
                    "Optimal team size (4-7 stakeholders) improves decision quality"
                )

        # Generic success factors
        if not success_factors:
            success_factors = [
                "Clear decision context and objectives",
                "Engaged stakeholder participation",
                "Evidence-based option evaluation",
            ]

        return success_factors

    def _identify_failure_indicators(
        self,
        sessions: List[AlignmentSession],
        patterns: List[DecisionPattern],
    ) -> List[str]:
        """
        Identify indicators correlated with poor outcomes.

        Args:
            sessions: All sessions
            patterns: Identified patterns

        Returns:
            List of failure indicators
        """
        failure_indicators = []

        # Find failure patterns
        failure_patterns = [p for p in patterns if p.pattern_type == "failure"]

        if failure_patterns:
            # Prolonged deliberation
            slow_decisions = sum(
                1 for p in failure_patterns if p.avg_metrics["avg_time_days"] > 14
            )
            if slow_decisions / len(failure_patterns) > 0.5:
                failure_indicators.append(
                    "Extended deliberation (> 14 days) correlates with decision fatigue"
                )

            # Large teams
            large_teams = sum(
                1 for p in failure_patterns if p.avg_metrics["avg_stakeholders"] > 10
            )
            if large_teams / len(failure_patterns) > 0.5:
                failure_indicators.append(
                    "Large stakeholder groups (> 10) slow consensus building"
                )

        # Generic failure indicators
        if not failure_indicators:
            failure_indicators = [
                "Lack of clear decision criteria",
                "Insufficient stakeholder engagement",
                "Analysis paralysis from too many options",
            ]

        return failure_indicators

    def _generate_pattern_recommendations(
        self,
        decision_type: str,
        pattern_type: str,
        characteristics: List[str],
        avg_time_days: float,
    ) -> List[str]:
        """
        Generate recommendations for a pattern.

        Args:
            decision_type: Type of decision
            pattern_type: Success/failure/neutral
            characteristics: Pattern characteristics
            avg_time_days: Average decision time

        Returns:
            List of recommendations
        """
        recommendations = []

        if pattern_type == "success":
            recommendations.append(
                f"Continue current approach for {decision_type} decisions"
            )
            if avg_time_days < 5:
                recommendations.append("Fast cycle time is a strength - maintain urgency")
        elif pattern_type == "failure":
            if avg_time_days > 14:
                recommendations.append(
                    "Implement time-boxing to prevent extended deliberation"
                )
                recommendations.append("Consider assigning dedicated facilitators")
            recommendations.append(
                f"Review and refine {decision_type} decision process"
            )
        else:  # neutral
            recommendations.append(
                f"Standardize best practices for {decision_type} decisions"
            )

        return recommendations

    async def _generate_recommendations(
        self,
        patterns: List[DecisionPattern],
        success_factors: List[str],
        failure_indicators: List[str],
    ) -> List[str]:
        """
        Generate organizational recommendations via CEE.

        Args:
            patterns: Identified patterns
            success_factors: Success factors
            failure_indicators: Failure indicators

        Returns:
            List of recommendations
        """
        try:
            # Build request for CEE
            request_payload = {
                "task": "generate_pattern_recommendations",
                "patterns": [
                    {
                        "type": p.pattern_type,
                        "decision_type": p.decision_type,
                        "sample_size": p.sample_size,
                        "characteristics": p.common_characteristics,
                    }
                    for p in patterns[:5]  # Top 5 patterns
                ],
                "success_factors": success_factors,
                "failure_indicators": failure_indicators,
            }

            response = await self.cee_client.client.post(
                f"{self.cee_client.base_url}/assist/v1/generate-insights",
                json=request_payload,
                headers={
                    "X-API-Key": self.cee_client.api_key,
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("insights", self._generate_fallback_recommendations())
            else:
                return self._generate_fallback_recommendations()

        except Exception as e:
            logger.error(
                "failed_to_generate_cee_recommendations",
                extra={"error": str(e)},
                exc_info=True,
            )
            return self._generate_fallback_recommendations()

    def _generate_fallback_recommendations(self) -> List[str]:
        """Generate fallback recommendations when CEE unavailable."""
        return [
            "Document and share successful decision patterns across teams",
            "Implement decision playbooks for common decision types",
            "Provide decision-making training focused on identified success factors",
            "Establish early warning systems for failure indicators",
            "Conduct retrospectives to continuously refine decision processes",
        ]

    async def invalidate_pattern_cache(
        self,
        organization_id: UUID,
        lookback_days: Optional[int] = None,
    ) -> None:
        """
        Invalidate cached pattern analysis for an organization.

        Should be called when:
        - A new retrospective is added
        - Session completion data is updated
        - Pattern analysis parameters change

        Args:
            organization_id: Organization ID
            lookback_days: Specific lookback period to invalidate (None = all)
        """
        try:
            if lookback_days is not None:
                # Invalidate specific lookback period
                cache_key = f"tae:patterns:{organization_id}:lookback_{lookback_days}"
                await self.cache.delete(cache_key)
                logger.info(
                    "pattern_cache_invalidated",
                    extra={
                        "organization_id": str(organization_id),
                        "cache_key": cache_key,
                    },
                )
            else:
                # Invalidate all lookback periods (scan for matching keys)
                pattern = f"tae:patterns:{organization_id}:*"
                # Use Redis SCAN to find and delete all matching keys
                cursor = 0
                deleted_count = 0
                while True:
                    cursor, keys = await self.cache.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await self.cache.delete(*keys)
                        deleted_count += len(keys)
                    if cursor == 0:
                        break

                logger.info(
                    "pattern_cache_invalidated_all",
                    extra={
                        "organization_id": str(organization_id),
                        "keys_deleted": deleted_count,
                    },
                )

        except Exception as e:
            logger.warning(
                "failed_to_invalidate_pattern_cache",
                extra={
                    "organization_id": str(organization_id),
                    "error": str(e),
                },
            )
            # Non-fatal - cache will expire naturally after TTL
