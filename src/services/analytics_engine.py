"""Advanced analytics engine service for Phase D5."""

import logging
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
from scipy import stats
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.portfolio import (
    TrendAnalysis,
    ComparativeBenchmark,
)
from src.models.session import AlignmentSession
from src.models.enums import SessionStatus, DecisionType
from src.utils.profiling import profile_async

logger = logging.getLogger(__name__)


class AdvancedAnalyticsEngine:
    """Advanced analytics for trend analysis and forecasting."""

    def __init__(self, db: AsyncSession):
        """
        Initialize analytics engine.

        Args:
            db: Database session
        """
        self.db = db

    @profile_async("d5_analyze_trends", capability="d5")
    async def analyze_trends(
        self,
        organization_id: UUID,
        metric_name: str,
        lookback_days: int = 90,
    ) -> TrendAnalysis:
        """
        Analyze trends for a specific metric.

        Args:
            organization_id: Organization ID
            metric_name: Metric to analyze (e.g., 'decision_time', 'quality_score')
            lookback_days: Days of history to analyze

        Returns:
            Trend analysis with forecasts
        """
        try:
            # Get completed sessions
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

            query = select(AlignmentSession).where(
                and_(
                    AlignmentSession.status == SessionStatus.COMPLETE,
                    AlignmentSession.completed_at >= cutoff_date,
                )
            )
            result = await self.db.execute(query)
            sessions = list(result.scalars().all())

            if len(sessions) < 5:
                raise ValueError(
                    f"Insufficient data for trend analysis: {len(sessions)} sessions"
                )

            # Extract time series data
            data_points = self._extract_time_series(sessions, metric_name)

            # Calculate trend direction and strength
            trend_direction, trend_strength = self._calculate_trend(data_points)

            # Calculate moving average
            moving_avg = self._calculate_moving_average(data_points, window=7)

            # Generate forecast
            forecast_values = self._forecast(data_points, periods=30)

            # Detect changepoints
            changepoints = self._detect_changepoints(data_points)

            # Calculate confidence intervals
            confidence_intervals = self._calculate_confidence_intervals(
                data_points, forecast_values
            )

            return TrendAnalysis(
                organization_id=organization_id,
                metric_name=metric_name,
                time_period_days=lookback_days,
                data_points=data_points,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                moving_average=moving_avg,
                forecast_30days=forecast_values,
                changepoints=changepoints,
                confidence_intervals=confidence_intervals,
                generated_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(
                "failed_to_analyze_trends",
                extra={
                    "organization_id": str(organization_id),
                    "metric_name": metric_name,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def _extract_time_series(
        self, sessions: List[AlignmentSession], metric_name: str
    ) -> List[Dict[str, float]]:
        """
        Extract time series data for metric.

        Args:
            sessions: List of sessions
            metric_name: Metric to extract

        Returns:
            List of {timestamp, value} dicts
        """
        data_points = []

        for session in sessions:
            if not session.completed_at:
                continue

            value: Optional[float] = None

            if metric_name == "decision_time":
                # Decision time in days
                value = (session.completed_at - session.created_at).days
            elif metric_name == "stakeholder_count":
                # Number of stakeholders
                value = float(len(session.stakeholders))
            elif metric_name == "quality_score":
                # Placeholder - would use actual retrospective ratings
                value = 7.5
            elif metric_name == "satisfaction_score":
                # Placeholder - would use actual retrospective ratings
                value = 8.0

            if value is not None:
                data_points.append(
                    {
                        "timestamp": session.completed_at.timestamp(),
                        "value": value,
                    }
                )

        # Sort by timestamp
        data_points.sort(key=lambda x: x["timestamp"])

        return data_points

    def _calculate_trend(
        self, data_points: List[Dict[str, float]]
    ) -> Tuple[str, float]:
        """
        Calculate trend direction and strength using linear regression.

        Args:
            data_points: Time series data

        Returns:
            Tuple of (direction, strength)
        """
        if len(data_points) < 2:
            return "stable", 0.0

        # Extract values
        x = np.array([p["timestamp"] for p in data_points])
        y = np.array([p["value"] for p in data_points])

        # Normalize x to avoid numerical issues
        x_normalized = (x - x.min()) / (x.max() - x.min() + 1e-10)

        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            x_normalized, y
        )

        # Determine direction
        if abs(slope) < 0.1:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        # Strength is R-squared
        strength = r_value ** 2

        return direction, float(strength)

    def _calculate_moving_average(
        self, data_points: List[Dict[str, float]], window: int = 7
    ) -> List[Dict[str, float]]:
        """
        Calculate moving average.

        Args:
            data_points: Time series data
            window: Window size

        Returns:
            Moving average values
        """
        if len(data_points) < window:
            return data_points

        values = [p["value"] for p in data_points]
        ma_values = []

        for i in range(len(values)):
            if i < window - 1:
                # Not enough data yet, use available
                window_values = values[: i + 1]
            else:
                window_values = values[i - window + 1 : i + 1]

            ma_values.append(
                {
                    "timestamp": data_points[i]["timestamp"],
                    "value": float(np.mean(window_values)),
                }
            )

        return ma_values

    def _forecast(
        self, data_points: List[Dict[str, float]], periods: int = 30
    ) -> List[Dict[str, float]]:
        """
        Forecast future values using linear regression.

        Args:
            data_points: Historical data
            periods: Number of periods to forecast

        Returns:
            Forecasted values
        """
        if len(data_points) < 2:
            return []

        # Extract values
        x = np.array([p["timestamp"] for p in data_points])
        y = np.array([p["value"] for p in data_points])

        # Normalize
        x_normalized = (x - x.min()) / (x.max() - x.min() + 1e-10)

        # Linear regression
        slope, intercept, _, _, _ = stats.linregress(x_normalized, y)

        # Generate forecast timestamps (daily intervals)
        last_timestamp = x[-1]
        day_seconds = 86400
        forecast_timestamps = [
            last_timestamp + (i + 1) * day_seconds for i in range(periods)
        ]

        # Forecast values
        forecasts = []
        x_range = x.max() - x.min()

        for ts in forecast_timestamps:
            x_norm = (ts - x.min()) / (x_range + 1e-10)
            predicted_value = slope * x_norm + intercept
            forecasts.append({"timestamp": ts, "value": float(predicted_value)})

        return forecasts

    def _detect_changepoints(
        self, data_points: List[Dict[str, float]]
    ) -> List[datetime]:
        """
        Detect significant changepoints in the time series.

        Args:
            data_points: Time series data

        Returns:
            List of changepoint timestamps
        """
        if len(data_points) < 10:
            return []

        changepoints = []
        values = [p["value"] for p in data_points]

        # Simple changepoint detection: find points where trend changes significantly
        window = 5
        for i in range(window, len(values) - window):
            before = values[i - window : i]
            after = values[i : i + window]

            # Test if means are significantly different
            t_stat, p_value = stats.ttest_ind(before, after)

            if p_value < 0.05:  # Significant change
                changepoints.append(
                    datetime.fromtimestamp(data_points[i]["timestamp"])
                )

        return changepoints

    def _calculate_confidence_intervals(
        self,
        data_points: List[Dict[str, float]],
        forecast_values: List[Dict[str, float]],
    ) -> List[Dict[str, float]]:
        """
        Calculate confidence intervals for forecasts.

        Args:
            data_points: Historical data
            forecast_values: Forecasted values

        Returns:
            Confidence intervals
        """
        if not data_points or not forecast_values:
            return []

        # Calculate standard deviation of residuals
        values = [p["value"] for p in data_points]
        std_dev = float(np.std(values))

        # 95% confidence interval (±1.96 std devs)
        intervals = []
        for forecast in forecast_values:
            intervals.append(
                {
                    "timestamp": forecast["timestamp"],
                    "lower": forecast["value"] - 1.96 * std_dev,
                    "upper": forecast["value"] + 1.96 * std_dev,
                }
            )

        return intervals

    async def compare_benchmarks(
        self,
        organization_id: UUID,
        decision_type: str,
        lookback_days: int = 90,
    ) -> ComparativeBenchmark:
        """
        Generate comparative benchmarks.

        Args:
            organization_id: Organization ID
            decision_type: Decision type to benchmark
            lookback_days: Days of history

        Returns:
            Comparative benchmark analysis
        """
        try:
            # Get sessions of this decision type
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

            query = select(AlignmentSession).where(
                and_(
                    AlignmentSession.status == SessionStatus.COMPLETE,
                    AlignmentSession.completed_at >= cutoff_date,
                    AlignmentSession.decision_type == decision_type,
                )
            )
            result = await self.db.execute(query)
            sessions = list(result.scalars().all())

            if len(sessions) < 3:
                raise ValueError(
                    f"Insufficient data for benchmarking: {len(sessions)} sessions"
                )

            # Calculate organization metrics
            org_metrics = self._calculate_benchmark_metrics(sessions)

            # Calculate percentile rankings
            # In production, would compare against industry/peer data
            # For now, use internal distribution
            percentile_rankings = self._calculate_percentiles(sessions, org_metrics)

            # Identify strengths and improvements
            strengths, improvements = self._identify_strengths_improvements(
                percentile_rankings
            )

            return ComparativeBenchmark(
                organization_id=organization_id,
                decision_type=decision_type,
                sample_size=len(sessions),
                organization_metrics=org_metrics,
                industry_average={
                    "decision_time_days": 10.0,
                    "quality_score": 7.0,
                    "satisfaction_score": 7.5,
                    "stakeholder_count": 5.0,
                },
                percentile_rankings=percentile_rankings,
                strengths=strengths,
                improvement_areas=improvements,
                generated_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(
                "failed_to_compare_benchmarks",
                extra={
                    "organization_id": str(organization_id),
                    "decision_type": decision_type,
                    "error": str(e)},
                exc_info=True,
            )
            raise

    def _calculate_benchmark_metrics(
        self, sessions: List[AlignmentSession]
    ) -> Dict[str, float]:
        """Calculate aggregate metrics for benchmarking."""
        decision_times = [
            (s.completed_at - s.created_at).days
            for s in sessions
            if s.completed_at
        ]
        stakeholder_counts = [len(s.stakeholders) for s in sessions]

        return {
            "decision_time_days": float(np.mean(decision_times)),
            "quality_score": 7.5,  # Placeholder
            "satisfaction_score": 8.0,  # Placeholder
            "stakeholder_count": float(np.mean(stakeholder_counts)),
        }

    def _calculate_percentiles(
        self, sessions: List[AlignmentSession], org_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate percentile rankings."""
        # In production, compare against industry data
        # For now, use simple comparison against industry average

        industry_avg = {
            "decision_time_days": 10.0,
            "quality_score": 7.0,
            "satisfaction_score": 7.5,
            "stakeholder_count": 5.0,
        }

        percentiles = {}
        for metric, org_value in org_metrics.items():
            industry_value = industry_avg.get(metric, org_value)

            # Lower is better for decision time
            if metric == "decision_time_days":
                if org_value < industry_value:
                    percentiles[metric] = 75.0  # Better than average
                else:
                    percentiles[metric] = 35.0  # Worse than average
            else:
                # Higher is better for quality, satisfaction
                if org_value > industry_value:
                    percentiles[metric] = 75.0
                else:
                    percentiles[metric] = 35.0

        return percentiles

    def _identify_strengths_improvements(
        self, percentile_rankings: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """Identify strengths and areas for improvement."""
        strengths = []
        improvements = []

        for metric, percentile in percentile_rankings.items():
            metric_display = metric.replace("_", " ").title()

            if percentile >= 75:
                strengths.append(f"{metric_display} in top quartile")
            elif percentile <= 25:
                improvements.append(f"{metric_display} below industry average")

        return strengths, improvements
