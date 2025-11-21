"""Unit tests for PortfolioAnalyzer service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from src.models.portfolio import (
    PortfolioFilters,
    DateRange,
    PortfolioMetrics,
    DecisionCluster,
    DecisionBottleneck,
)
from src.models.enums import SessionStatus, DecisionType
from src.services.portfolio_analyzer import PortfolioAnalyzer, InsufficientDataError


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_cee_client():
    """Mock CEE client."""
    client = MagicMock()
    client.client = AsyncMock()
    client.base_url = "http://test-cee"
    client.api_key = "test-key"
    return client


@pytest.fixture
def sample_sessions():
    """Create sample sessions for testing."""
    from src.models.session import AlignmentSession

    now = datetime.utcnow()
    org_id = uuid4()
    team_id = uuid4()

    sessions = []

    # Completed session
    user1_id = uuid4()
    sessions.append(
        AlignmentSession(
            session_id=uuid4(),
            team_id=team_id,
            decision_topic="Pricing Strategy",
            decision_type=DecisionType.PRICING,
            status=SessionStatus.COMPLETE,
            stakeholders=[
                {"user_id": "user1", "role": "owner"},
                {"user_id": "user2", "role": "contributor"},
            ],
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=3),
            completed_at=now - timedelta(days=3),
            decision_context="Test context",
            alignment_mode="evidence_backed",
            created_by=user1_id,
        )
    )

    # Active deliberating session
    sessions.append(
        AlignmentSession(
            session_id=uuid4(),
            team_id=team_id,
            decision_topic="Feature Prioritization",
            decision_type=DecisionType.FEATURE_PRIORITIZATION,
            status=SessionStatus.DELIBERATING,
            stakeholders=[
                {"user_id": "user1", "role": "owner"},
                {"user_id": "user3", "role": "contributor"},
            ],
            created_at=now - timedelta(days=8),
            updated_at=now,
            completed_at=None,
            decision_context="Test context",
            alignment_mode="evidence_backed",
            created_by=user1_id,
        )
    )

    # Stuck session (deliberating >12 days)
    sessions.append(
        AlignmentSession(
            session_id=uuid4(),
            team_id=team_id,
            decision_topic="GTM Strategy",
            decision_type=DecisionType.GTM_STRATEGY,
            status=SessionStatus.DELIBERATING,
            stakeholders=[
                {"user_id": "user1", "role": "owner"},
                {"user_id": "user2", "role": "contributor"},
            ],
            created_at=now - timedelta(days=15),
            updated_at=now,
            completed_at=None,
            decision_context="Test context",
            alignment_mode="evidence_backed",
            created_by=user1_id,
        )
    )

    # Another completed session of same type as first
    sessions.append(
        AlignmentSession(
            session_id=uuid4(),
            team_id=team_id,
            decision_topic="Pricing Revision",
            decision_type=DecisionType.PRICING,
            status=SessionStatus.COMPLETE,
            stakeholders=[
                {"user_id": "user1", "role": "owner"},
                {"user_id": "user2", "role": "contributor"},
                {"user_id": "user4", "role": "contributor"},
            ],
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=1),
            completed_at=now - timedelta(days=1),
            decision_context="Test context",
            alignment_mode="evidence_backed",
            created_by=user1_id,
        )
    )

    return sessions


@pytest.fixture
def portfolio_filters():
    """Create default portfolio filters."""
    now = datetime.utcnow()
    return PortfolioFilters(
        organization_id=uuid4(),
        date_range=DateRange(start=now - timedelta(days=30), end=now)
    )


class TestPortfolioAnalyzer:
    """Tests for PortfolioAnalyzer service."""

    @pytest.mark.asyncio
    async def test_generate_portfolio_view_success(
        self, mock_db, mock_cee_client, sample_sessions, portfolio_filters
    ):
        """Test successful portfolio view generation."""
        org_id = uuid4()

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = sample_sessions
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock CEE response
        mock_cee_client.client.post = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=lambda: {
                    "insights": [
                        "Strong decision velocity",
                        "Some bottlenecks detected",
                    ]
                },
            )
        )

        analyzer = PortfolioAnalyzer(db=mock_db, cee_client=mock_cee_client)
        analysis = await analyzer.generate_portfolio_view(org_id, portfolio_filters)

        assert analysis.organization_id == org_id
        assert analysis.total_sessions == 4
        assert analysis.completed_sessions == 2
        assert analysis.active_sessions == 2
        assert 0.0 <= analysis.health_score <= 1.0
        assert len(analysis.strategic_insights) > 0

    @pytest.mark.asyncio
    async def test_generate_portfolio_view_no_sessions(
        self, mock_db, mock_cee_client, portfolio_filters
    ):
        """Test portfolio view with no sessions."""
        org_id = uuid4()

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        analyzer = PortfolioAnalyzer(db=mock_db, cee_client=mock_cee_client)

        with pytest.raises(InsufficientDataError):
            await analyzer.generate_portfolio_view(org_id, portfolio_filters)

    @pytest.mark.asyncio
    async def test_aggregate_metrics_completed_sessions(
        self, mock_db, sample_sessions
    ):
        """Test metrics aggregation for completed sessions."""
        analyzer = PortfolioAnalyzer(db=mock_db)
        metrics = await analyzer._aggregate_metrics(sample_sessions)

        assert isinstance(metrics, PortfolioMetrics)
        assert metrics.avg_decision_time_days >= 0
        assert 0.0 <= metrics.avg_quality_rating <= 10.0
        assert 0.0 <= metrics.causal_validation_success_rate <= 1.0

    @pytest.mark.asyncio
    async def test_aggregate_metrics_no_completed(self, mock_db):
        """Test metrics aggregation with no completed sessions."""
        from src.models.session import AlignmentSession

        user1_id = uuid4()
        # Create only non-completed sessions
        sessions = [
            AlignmentSession(
                session_id=uuid4(),
                team_id=uuid4(),
                decision_topic="Test",
                decision_type=DecisionType.CUSTOM,
                status=SessionStatus.COLLECTING,
                stakeholders=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                completed_at=None,
                decision_context="Test",
                alignment_mode="quick",
                created_by=user1_id,
            )
        ]

        analyzer = PortfolioAnalyzer(db=mock_db)
        metrics = await analyzer._aggregate_metrics(sessions)

        # Should return default values
        assert metrics.avg_decision_time_days == 0.0
        assert metrics.total_options_proposed == 0

    def test_identify_clusters(self, mock_db, sample_sessions):
        """Test decision clustering."""
        analyzer = PortfolioAnalyzer(db=mock_db)
        clusters = analyzer._identify_clusters(sample_sessions)

        # Should have at least one cluster (PRICING with 2 sessions)
        assert len(clusters) >= 1

        # Check cluster structure
        pricing_cluster = next(
            (c for c in clusters if "Pricing" in c.theme), None
        )
        assert pricing_cluster is not None
        assert len(pricing_cluster.session_ids) >= 2

        # Common stakeholders should include user1 and user2 (appear in both PRICING sessions)
        assert "user1" in pricing_cluster.common_stakeholders or "user2" in pricing_cluster.common_stakeholders

    def test_identify_clusters_no_duplicates(self, mock_db):
        """Test clustering with no duplicate decision types."""
        from src.models.session import AlignmentSession

        user1_id = uuid4()
        # Create sessions with unique decision types
        sessions = [
            AlignmentSession(
                session_id=uuid4(),
                team_id=uuid4(),
                decision_topic=f"Decision {i}",
                decision_type=DecisionType.CUSTOM,
                status=SessionStatus.COMPLETE,
                stakeholders=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                decision_context="Test",
                alignment_mode="quick",
                created_by=user1_id,
            )
            for i in range(3)
        ]

        analyzer = PortfolioAnalyzer(db=mock_db)
        clusters = analyzer._identify_clusters(sessions)

        # Should create one cluster for CUSTOM type (3 sessions)
        assert len(clusters) >= 1

    def test_detect_bottlenecks(self, mock_db, sample_sessions):
        """Test bottleneck detection."""
        analyzer = PortfolioAnalyzer(db=mock_db)
        bottlenecks = analyzer._detect_bottlenecks(sample_sessions)

        # Should detect at least one bottleneck (stuck session >12 days)
        assert len(bottlenecks) > 0

        # Check for high severity bottleneck
        high_severity = [b for b in bottlenecks if b.severity == "high"]
        assert len(high_severity) > 0

    def test_detect_bottlenecks_no_issues(self, mock_db):
        """Test bottleneck detection with healthy sessions."""
        from src.models.session import AlignmentSession

        user1_id = uuid4()
        # Create only recently completed sessions
        sessions = [
            AlignmentSession(
                session_id=uuid4(),
                team_id=uuid4(),
                decision_topic="Test",
                decision_type=DecisionType.CUSTOM,
                status=SessionStatus.COMPLETE,
                stakeholders=[],
                created_at=datetime.utcnow() - timedelta(days=2),
                updated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                decision_context="Test",
                alignment_mode="quick",
                created_by=user1_id,
            )
        ]

        analyzer = PortfolioAnalyzer(db=mock_db)
        bottlenecks = analyzer._detect_bottlenecks(sessions)

        # Should have no bottlenecks
        assert len(bottlenecks) == 0

    def test_calculate_health_high_score(self, mock_db):
        """Test health calculation with good metrics."""
        metrics = PortfolioMetrics(
            avg_decision_time_days=3.0,  # Fast decisions
            avg_quality_rating=8.5,
            avg_satisfaction_score=8.0,
            total_options_proposed=100,
            total_ai_options_used=20,
            causal_validation_success_rate=0.9,  # High validation
            minority_concern_validation_rate=0.25,
        )

        analyzer = PortfolioAnalyzer(db=mock_db)
        health = analyzer._calculate_health(metrics, [], 2)

        # Should have high health score
        assert health >= 0.8

    def test_calculate_health_low_score(self, mock_db):
        """Test health calculation with poor metrics."""
        metrics = PortfolioMetrics(
            avg_decision_time_days=20.0,  # Slow decisions
            avg_quality_rating=5.0,
            avg_satisfaction_score=6.0,
            total_options_proposed=50,
            total_ai_options_used=5,
            causal_validation_success_rate=0.6,  # Low validation
            minority_concern_validation_rate=0.1,
        )

        # Create high severity bottlenecks
        bottlenecks = [
            DecisionBottleneck(
                bottleneck_type="stuck_session",
                session_id=uuid4(),
                description="Test",
                severity="high",
                recommendation="Fix it",
            )
            for _ in range(3)
        ]

        analyzer = PortfolioAnalyzer(db=mock_db)
        health = analyzer._calculate_health(metrics, bottlenecks, 5)

        # Should have low health score
        assert health < 0.6

    @pytest.mark.asyncio
    async def test_generate_insights_cee_success(self, mock_db, mock_cee_client):
        """Test insights generation via CEE."""
        mock_cee_client.client.post = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=lambda: {
                    "insights": ["Insight 1", "Insight 2", "Insight 3"]
                },
            )
        )

        analyzer = PortfolioAnalyzer(db=mock_db, cee_client=mock_cee_client)

        metrics = PortfolioMetrics(
            avg_decision_time_days=5.0,
            avg_quality_rating=7.5,
            avg_satisfaction_score=8.0,
            total_options_proposed=100,
            total_ai_options_used=25,
            causal_validation_success_rate=0.85,
            minority_concern_validation_rate=0.20,
        )

        insights = await analyzer._generate_insights(
            sessions_count=10,
            metrics=metrics,
            clusters=[],
            bottlenecks=[],
            health_score=0.75,
        )

        assert len(insights) == 3
        assert "Insight 1" in insights

    @pytest.mark.asyncio
    async def test_generate_insights_cee_failure_fallback(
        self, mock_db, mock_cee_client
    ):
        """Test insights generation falls back when CEE fails."""
        # Mock CEE failure
        mock_cee_client.client.post = AsyncMock(
            return_value=MagicMock(status_code=500)
        )

        analyzer = PortfolioAnalyzer(db=mock_db, cee_client=mock_cee_client)

        metrics = PortfolioMetrics(
            avg_decision_time_days=10.0,
            avg_quality_rating=7.5,
            avg_satisfaction_score=8.0,
            total_options_proposed=100,
            total_ai_options_used=25,
            causal_validation_success_rate=0.85,
            minority_concern_validation_rate=0.20,
        )

        insights = await analyzer._generate_insights(
            sessions_count=10,
            metrics=metrics,
            clusters=[],
            bottlenecks=[],
            health_score=0.65,
        )

        # Should return fallback insights
        assert len(insights) > 0
        assert any("decision time" in i.lower() for i in insights)

    def test_generate_fallback_insights_fast_decisions(self, mock_db):
        """Test fallback insights for fast decisions."""
        metrics = PortfolioMetrics(
            avg_decision_time_days=3.0,
            avg_quality_rating=7.5,
            avg_satisfaction_score=8.0,
            total_options_proposed=100,
            total_ai_options_used=25,
            causal_validation_success_rate=0.85,
            minority_concern_validation_rate=0.20,
        )

        analyzer = PortfolioAnalyzer(db=mock_db)
        insights = analyzer._generate_fallback_insights(metrics, [])

        assert len(insights) > 0
        assert any("healthy" in i.lower() or "velocity" in i.lower() for i in insights)

    def test_generate_fallback_insights_with_bottlenecks(self, mock_db):
        """Test fallback insights when bottlenecks exist."""
        metrics = PortfolioMetrics(
            avg_decision_time_days=5.0,
            avg_quality_rating=7.5,
            avg_satisfaction_score=8.0,
            total_options_proposed=100,
            total_ai_options_used=25,
            causal_validation_success_rate=0.85,
            minority_concern_validation_rate=0.20,
        )

        bottlenecks = [
            DecisionBottleneck(
                bottleneck_type="stuck_session",
                session_id=uuid4(),
                description="Test",
                severity="high",
                recommendation="Fix it",
            ),
            DecisionBottleneck(
                bottleneck_type="stuck_session",
                session_id=uuid4(),
                description="Test",
                severity="high",
                recommendation="Fix it",
            ),
        ]

        analyzer = PortfolioAnalyzer(db=mock_db)
        insights = analyzer._generate_fallback_insights(metrics, bottlenecks)

        assert len(insights) > 0
        assert any("bottleneck" in i.lower() for i in insights)
