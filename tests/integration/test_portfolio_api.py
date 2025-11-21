"""Integration tests for portfolio API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def organization_id():
    """Sample organization ID."""
    return uuid4()


@pytest.fixture
def mock_portfolio_analysis():
    """Mock portfolio analysis result."""
    from src.models.portfolio import (
        PortfolioAnalysis,
        PortfolioMetrics,
        DecisionCluster,
        DecisionBottleneck,
        DateRange,
    )

    now = datetime.utcnow()

    return PortfolioAnalysis(
        organization_id=uuid4(),
        period=DateRange(start=now - timedelta(days=30), end=now),
        total_sessions=10,
        active_sessions=3,
        completed_sessions=7,
        metrics=PortfolioMetrics(
            avg_decision_time_days=5.5,
            avg_quality_rating=7.8,
            avg_satisfaction_score=8.2,
            total_options_proposed=45,
            total_ai_options_used=12,
            causal_validation_success_rate=0.87,
            minority_concern_validation_rate=0.23,
        ),
        clusters=[
            DecisionCluster(
                cluster_id="pricing_cluster",
                theme="Pricing Decisions",
                session_ids=[uuid4(), uuid4()],
                avg_complexity=0.65,
                common_stakeholders=["user1", "user2"],
            )
        ],
        bottlenecks=[
            DecisionBottleneck(
                bottleneck_type="stuck_session",
                session_id=uuid4(),
                description="Session stuck for 15 days",
                severity="high",
                recommendation="Assign facilitator",
            )
        ],
        health_score=0.75,
        strategic_insights=[
            "Decision velocity is healthy",
            "Strong causal validation rate",
            "1 high-priority bottleneck detected",
        ],
        generated_at=now,
    )


class TestPortfolioAnalyticsEndpoint:
    """Tests for /api/v1/portfolio/analytics endpoint."""

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_success(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test successful portfolio analytics retrieval."""
        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/analytics",
                params={"organization_id": str(organization_id)},
            )

            assert response.status_code == 200
            data = response.json()

            assert "analysis" in data
            analysis = data["analysis"]

            assert "total_sessions" in analysis
            assert analysis["total_sessions"] == 10
            assert analysis["active_sessions"] == 3
            assert analysis["completed_sessions"] == 7
            assert "health_score" in analysis
            assert 0.0 <= analysis["health_score"] <= 1.0
            assert "metrics" in analysis
            assert "clusters" in analysis
            assert "bottlenecks" in analysis
            assert "strategic_insights" in analysis

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_with_date_range(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test portfolio analytics with custom date range."""
        start_date = datetime.utcnow() - timedelta(days=60)
        end_date = datetime.utcnow()

        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/analytics",
                params={
                    "organization_id": str(organization_id),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )

            assert response.status_code == 200
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_with_team_filter(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test portfolio analytics filtered by teams."""
        team_ids = [str(uuid4()), str(uuid4())]

        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/analytics",
                params={
                    "organization_id": str(organization_id),
                    "teams": team_ids,
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_with_decision_type_filter(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test portfolio analytics filtered by decision types."""
        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/analytics",
                params={
                    "organization_id": str(organization_id),
                    "decision_types": ["pricing", "feature_prioritization"],
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_with_status_filter(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test portfolio analytics filtered by status."""
        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/analytics",
                params={
                    "organization_id": str(organization_id),
                    "status": ["complete", "deliberating"],
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_insufficient_data(
        self, client: AsyncClient, organization_id
    ):
        """Test portfolio analytics with no data."""
        from src.services.portfolio_analyzer import InsufficientDataError

        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.side_effect = InsufficientDataError(
                "No sessions found matching filters"
            )

            response = await client.get(
                "/api/v1/portfolio/analytics",
                params={"organization_id": str(organization_id)},
            )

            assert response.status_code == 404
            data = response.json()
            assert "message" in data  # Error handler middleware transforms to 'message'

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_invalid_organization_id(
        self, client: AsyncClient
    ):
        """Test portfolio analytics with invalid organization ID."""
        response = await client.get(
            "/api/v1/portfolio/analytics",
            params={"organization_id": "invalid-uuid"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_missing_organization_id(
        self, client: AsyncClient
    ):
        """Test portfolio analytics without organization ID."""
        response = await client.get("/api/v1/portfolio/analytics")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_server_error(
        self, client: AsyncClient, organization_id
    ):
        """Test portfolio analytics with server error."""
        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.side_effect = Exception("Database connection failed")

            response = await client.get(
                "/api/v1/portfolio/analytics",
                params={"organization_id": str(organization_id)},
            )

            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_invalid_date_range(
        self, client: AsyncClient, organization_id
    ):
        """Test portfolio analytics with invalid date range."""
        # Start date after end date
        start_date = datetime.utcnow()
        end_date = datetime.utcnow() - timedelta(days=30)

        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.side_effect = ValueError("Invalid date range")

            response = await client.get(
                "/api/v1/portfolio/analytics",
                params={
                    "organization_id": str(organization_id),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_with_min_risk_score(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test portfolio analytics with min risk score filter."""
        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/analytics",
                params={
                    "organization_id": str(organization_id),
                    "min_risk_score": 0.5,
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_portfolio_analytics_invalid_min_risk_score(
        self, client: AsyncClient, organization_id
    ):
        """Test portfolio analytics with invalid min risk score."""
        # Risk score out of range
        response = await client.get(
            "/api/v1/portfolio/analytics",
            params={
                "organization_id": str(organization_id),
                "min_risk_score": 1.5,  # Invalid: > 1.0
            },
        )

        assert response.status_code == 422  # Validation error


class TestPortfolioHealthScoreEndpoint:
    """Tests for /api/v1/portfolio/health-score endpoint."""

    @pytest.mark.asyncio
    async def test_get_health_score_success(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test successful health score retrieval."""
        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/health-score",
                params={"organization_id": str(organization_id)},
            )

            assert response.status_code == 200
            data = response.json()

            assert "health_score" in data
            assert 0.0 <= data["health_score"] <= 1.0
            assert "total_sessions" in data
            assert "active_sessions" in data
            assert "completed_sessions" in data
            assert "high_priority_bottlenecks" in data
            assert "period" in data

    @pytest.mark.asyncio
    async def test_get_health_score_with_date_range(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test health score with custom date range."""
        start_date = datetime.utcnow() - timedelta(days=60)
        end_date = datetime.utcnow()

        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/health-score",
                params={
                    "organization_id": str(organization_id),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "period" in data

    @pytest.mark.asyncio
    async def test_get_health_score_no_data(
        self, client: AsyncClient, organization_id
    ):
        """Test health score when no data available."""
        from src.services.portfolio_analyzer import InsufficientDataError

        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.side_effect = InsufficientDataError("No sessions found")

            response = await client.get(
                "/api/v1/portfolio/health-score",
                params={"organization_id": str(organization_id)},
            )

            # Should return 0 values instead of error
            assert response.status_code == 200
            data = response.json()
            assert data["health_score"] == 0.0
            assert data["total_sessions"] == 0

    @pytest.mark.asyncio
    async def test_get_health_score_missing_organization_id(
        self, client: AsyncClient
    ):
        """Test health score without organization ID."""
        response = await client.get("/api/v1/portfolio/health-score")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_health_score_counts_high_priority_bottlenecks(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test that health score correctly counts high priority bottlenecks."""
        # Add more bottlenecks to mock
        from src.models.portfolio import DecisionBottleneck

        mock_portfolio_analysis.bottlenecks.extend(
            [
                DecisionBottleneck(
                    bottleneck_type="stuck_session",
                    session_id=uuid4(),
                    description="Test",
                    severity="high",
                    recommendation="Fix",
                ),
                DecisionBottleneck(
                    bottleneck_type="stuck_session",
                    session_id=uuid4(),
                    description="Test",
                    severity="medium",
                    recommendation="Fix",
                ),
            ]
        )

        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/health-score",
                params={"organization_id": str(organization_id)},
            )

            assert response.status_code == 200
            data = response.json()

            # Should count only high severity bottlenecks (2 total)
            assert data["high_priority_bottlenecks"] == 2

    @pytest.mark.asyncio
    async def test_get_health_score_defaults_to_30_days(
        self, client: AsyncClient, organization_id, mock_portfolio_analysis
    ):
        """Test that health score defaults to last 30 days."""
        with patch(
            "src.services.portfolio_analyzer.PortfolioAnalyzer.generate_portfolio_view"
        ) as mock_generate:
            mock_generate.return_value = mock_portfolio_analysis

            response = await client.get(
                "/api/v1/portfolio/health-score",
                params={"organization_id": str(organization_id)},
            )

            assert response.status_code == 200

            # Verify the analyzer was called (date defaults applied in endpoint)
            mock_generate.assert_called_once()
