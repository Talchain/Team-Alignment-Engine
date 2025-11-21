"""Unit tests for OrchestrationService (PLoT integration)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import datetime

from src.services.orchestration import OrchestrationService
from src.models.plot import (
    TaeTeamAlignmentPayload,
    AlignmentData,
    SharedGroundData,
    DisagreementData,
    DisagreementAxis,
    DecisionQualityMetrics,
    SimilarDecision,
    DecisionDependency,
)
from src.models.session import AlignmentSession
from src.models.enums import SessionStatus


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_session_manager():
    """Create mock session manager."""
    return AsyncMock()


@pytest.fixture
def mock_dependency_manager():
    """Create mock dependency manager."""
    return AsyncMock()


@pytest.fixture
def mock_pattern_analyzer():
    """Create mock pattern analyzer."""
    return AsyncMock()


@pytest.fixture
def orchestration_service(
    mock_db,
    mock_session_manager,
    mock_dependency_manager,
    mock_pattern_analyzer,
):
    """Create orchestration service with mocked dependencies."""
    return OrchestrationService(
        db=mock_db,
        session_manager=mock_session_manager,
        dependency_manager=mock_dependency_manager,
        pattern_analyzer=mock_pattern_analyzer,
    )


@pytest.fixture
def sample_session():
    """Create sample alignment session."""
    session_id = uuid4()
    return AlignmentSession(
        session_id=session_id,
        team_id=uuid4(),
        decision_topic="Test Decision",
        decision_context="Test context",
        decision_type="custom",
        alignment_mode="evidence_backed",
        stakeholders=[
            {"user_id": str(uuid4()), "role": "PM", "name": "Alice"},
            {"user_id": str(uuid4()), "role": "Designer", "name": "Bob"},
            {"user_id": str(uuid4()), "role": "Engineer", "name": "Charlie"},
        ],
        created_by=uuid4(),
        status=SessionStatus.DELIBERATING,
        shared_ground={
            "summary": "All stakeholders prioritize user experience",
            "goal_weights": {"user_satisfaction": 0.9, "performance": 0.8},
            "common_priorities": ["Fast load times", "Mobile support"],
        },
        disagreement_map={
            "summary": "Disagreement on implementation timeline",
            "axes": [
                {
                    "dimension": "feasibility",
                    "stakeholders": ["PM", "Engineer"],
                    "severity": 0.6,
                    "description": "PM wants 2 weeks, Engineer needs 4 weeks",
                }
            ],
        },
    )


# =============================================================================
# TEST D1: CORE ALIGNMENT
# =============================================================================


@pytest.mark.asyncio
async def test_get_core_alignment_success(
    orchestration_service, mock_session_manager, sample_session
):
    """Test successful core alignment data retrieval (D1)."""
    # Setup
    mock_session_manager.get.return_value = sample_session

    # Execute
    result = await orchestration_service._get_core_alignment(
        str(sample_session.session_id)
    )

    # Assert
    assert result is not None
    assert isinstance(result, AlignmentData)
    assert result.session_state == "deliberating"
    assert result.stakeholder_count == 3
    assert result.perspectives_collected == 3
    assert 0.0 <= result.consensus_level <= 1.0

    # Verify shared ground
    assert result.shared_ground is not None
    assert "user experience" in result.shared_ground.summary.lower()
    assert len(result.shared_ground.aligned_priorities) == 2

    # Verify disagreements
    assert result.disagreements is not None
    assert len(result.disagreements.axes) == 1
    assert result.disagreements.axes[0].dimension == "feasibility"
    assert result.disagreements.axes[0].severity_score == 0.6

    # Verify session manager was called
    mock_session_manager.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_core_alignment_session_not_found(
    orchestration_service, mock_session_manager
):
    """Test core alignment when session doesn't exist."""
    # Setup
    mock_session_manager.get.return_value = None

    # Execute
    result = await orchestration_service._get_core_alignment("nonexistent-session")

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_core_alignment_no_shared_ground(
    orchestration_service, mock_session_manager
):
    """Test core alignment with session that has no shared ground yet."""
    # Setup - session without shared_ground
    session = AlignmentSession(
        session_id=uuid4(),
        team_id=uuid4(),
        decision_topic="Test",
        decision_context="Test",
        decision_type="custom",
        alignment_mode="quick",
        stakeholders=[{"user_id": str(uuid4()), "role": "PM", "name": "Test"}],
        created_by=uuid4(),
        status=SessionStatus.COLLECTING,
    )
    mock_session_manager.get.return_value = session

    # Execute
    result = await orchestration_service._get_core_alignment(str(session.session_id))

    # Assert
    assert result is not None
    assert result.shared_ground.summary == "Shared ground analysis pending"
    assert result.disagreements.summary == "Disagreement analysis pending"


@pytest.mark.asyncio
async def test_get_core_alignment_feature_flag_disabled(
    orchestration_service, mock_session_manager
):
    """Test core alignment when D1 feature flag is disabled."""
    # Setup
    with patch("src.services.orchestration.settings") as mock_settings:
        mock_settings.feature_portfolio_analytics_enabled = False

        # Execute
        result = await orchestration_service._get_core_alignment("session-123")

        # Assert
        assert result is None
        # Session manager should not be called if feature disabled
        mock_session_manager.get.assert_not_called()


# =============================================================================
# TEST D3: DEPENDENCIES
# =============================================================================


@pytest.mark.asyncio
async def test_get_dependencies_success(
    orchestration_service, mock_dependency_manager
):
    """Test successful dependency retrieval (D3)."""
    # Setup - mock dependency data
    mock_dep1 = MagicMock()
    mock_dep1.target_session_id = uuid4()
    mock_dep1.dependency_type = "blocks"
    mock_dep1.description = "Waiting for API design"
    mock_dep1.resolved_at = None

    mock_dep2 = MagicMock()
    mock_dep2.target_session_id = uuid4()
    mock_dep2.dependency_type = "informs"
    mock_dep2.description = "Related to user research findings"
    mock_dep2.resolved_at = datetime.utcnow()

    mock_dependency_manager.get_dependencies_for_session.return_value = [
        mock_dep1,
        mock_dep2,
    ]

    # Execute
    session_id = str(uuid4())
    result = await orchestration_service._get_dependencies(session_id)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2

    # Check first dependency (blocking)
    assert result[0].dependency_type == "blocks"
    assert result[0].status == "pending"

    # Check second dependency (resolved)
    assert result[1].dependency_type == "informs"
    assert result[1].status == "resolved"

    # Verify dependency manager was called
    mock_dependency_manager.get_dependencies_for_session.assert_called_once()


@pytest.mark.asyncio
async def test_get_dependencies_no_session(orchestration_service):
    """Test dependencies with no session ID."""
    # Execute
    result = await orchestration_service._get_dependencies(None)

    # Assert
    assert result == []


@pytest.mark.asyncio
async def test_get_dependencies_feature_flag_disabled(
    orchestration_service, mock_dependency_manager
):
    """Test dependencies when D3 feature flag is disabled."""
    # Setup
    with patch("src.services.orchestration.settings") as mock_settings:
        mock_settings.feature_decision_dependencies_enabled = False

        # Execute
        result = await orchestration_service._get_dependencies("session-123")

        # Assert
        assert result == []
        mock_dependency_manager.get_dependencies_for_session.assert_not_called()


@pytest.mark.asyncio
async def test_get_dependencies_error_handling(
    orchestration_service, mock_dependency_manager
):
    """Test dependency retrieval with error."""
    # Setup - mock error with valid UUID
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    mock_dependency_manager.get_dependencies_for_session.side_effect = Exception(
        "Database error"
    )

    # Execute & Assert
    with pytest.raises(Exception, match="Database error"):
        await orchestration_service._get_dependencies(test_uuid)


# =============================================================================
# TEST D4: PATTERNS
# =============================================================================


@pytest.mark.asyncio
async def test_get_patterns_success(orchestration_service, mock_pattern_analyzer):
    """Test successful pattern retrieval (D4)."""
    # Setup - mock pattern data
    mock_pattern1 = MagicMock()
    mock_pattern1.pattern_id = "pattern-1"
    mock_pattern1.pattern_type = "success_pattern"
    mock_pattern1.confidence = 0.87
    mock_pattern1.recommended_actions = [
        "Early prototyping saved time",
        "Clear requirements helped",
        "Daily standups improved alignment",
    ]

    mock_pattern2 = MagicMock()
    mock_pattern2.pattern_id = "pattern-2"
    mock_pattern2.pattern_type = "anti_pattern"
    mock_pattern2.confidence = 0.72
    mock_pattern2.recommended_actions = [
        "Avoid analysis paralysis",
        "Set clear deadlines",
    ]

    mock_pattern_analyzer.extract_patterns.return_value = [
        mock_pattern1,
        mock_pattern2,
    ]

    # Execute
    session_id = str(uuid4())
    org_id = str(uuid4())
    result = await orchestration_service._get_patterns(session_id, org_id)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2

    # Check first pattern (success)
    assert isinstance(result[0], SimilarDecision)
    assert result[0].outcome == "success"
    assert result[0].similarity == 0.87
    assert len(result[0].key_lessons) == 3

    # Check second pattern (anti-pattern maps to neutral)
    assert result[1].outcome == "neutral"
    assert result[1].similarity == 0.72

    # Verify pattern analyzer was called
    mock_pattern_analyzer.extract_patterns.assert_called_once()


@pytest.mark.asyncio
async def test_get_patterns_limits_to_top_5(
    orchestration_service, mock_pattern_analyzer
):
    """Test pattern retrieval limits to top 5 patterns."""
    # Setup - mock 10 patterns with valid UUIDs
    test_session_uuid = "550e8400-e29b-41d4-a716-446655440000"
    test_org_uuid = "650e8400-e29b-41d4-a716-446655440001"
    mock_patterns = [
        MagicMock(
            pattern_id=f"pattern-{i}",
            pattern_type="success_pattern",
            confidence=0.9 - (i * 0.05),
            recommended_actions=[f"Lesson {i}"],
        )
        for i in range(10)
    ]
    mock_pattern_analyzer.extract_patterns.return_value = mock_patterns

    # Execute
    result = await orchestration_service._get_patterns(test_session_uuid, test_org_uuid)

    # Assert
    assert len(result) == 5  # Should limit to top 5


@pytest.mark.asyncio
async def test_get_patterns_no_session(orchestration_service):
    """Test patterns with no session ID."""
    # Execute
    result = await orchestration_service._get_patterns(None, "org-123")

    # Assert
    assert result == []


@pytest.mark.asyncio
async def test_get_patterns_feature_flag_disabled(
    orchestration_service, mock_pattern_analyzer
):
    """Test patterns when D4 feature flag is disabled."""
    # Setup
    with patch("src.services.orchestration.settings") as mock_settings:
        mock_settings.feature_organizational_patterns_enabled = False

        # Execute
        result = await orchestration_service._get_patterns("session-123", "org-456")

        # Assert
        assert result == []
        mock_pattern_analyzer.extract_patterns.assert_not_called()


# =============================================================================
# TEST FULL ORCHESTRATION
# =============================================================================


@pytest.mark.asyncio
async def test_build_alignment_payload_all_capabilities_success(
    orchestration_service,
    mock_session_manager,
    mock_dependency_manager,
    mock_pattern_analyzer,
    sample_session,
):
    """Test building full payload with all capabilities succeeding."""
    # Setup
    test_org_uuid = "650e8400-e29b-41d4-a716-446655440001"
    mock_session_manager.get.return_value = sample_session
    mock_dependency_manager.get_dependencies_for_session.return_value = []
    mock_pattern_analyzer.extract_patterns.return_value = []

    # Execute
    payload = await orchestration_service.build_alignment_payload(
        session_id=str(sample_session.session_id),
        organization_id=test_org_uuid,
        capabilities=["core_alignment", "d3_dependencies", "d4_patterns"],
        context={},
        request_id="plot-run-test-001",
    )

    # Assert
    assert isinstance(payload, TaeTeamAlignmentPayload)
    assert payload.session_id == str(sample_session.session_id)
    assert payload.organization_id == test_org_uuid
    assert payload.request_id == "plot-run-test-001"
    # Version comes from settings.service_version
    assert payload.version is not None
    assert isinstance(payload.version, str)

    # Verify alignment data present
    assert payload.alignment is not None
    assert payload.alignment.stakeholder_count == 3

    # Verify decision quality present
    assert payload.decision_quality is not None
    assert 0.0 <= payload.decision_quality.health_score <= 1.0

    # Verify organizational context present
    assert payload.organizational_context is not None
    assert payload.organizational_context.dependencies == []
    assert payload.organizational_context.similar_decisions == []

    # Verify availability
    assert payload.availability.tae_available is True
    assert payload.availability.capabilities.d1_portfolio_analytics is True
    assert payload.availability.capabilities.d3_decision_dependencies is True
    assert payload.availability.capabilities.d4_organizational_patterns is True
    assert payload.availability.degraded is False


@pytest.mark.asyncio
async def test_build_alignment_payload_capability_filtering(
    orchestration_service,
    mock_session_manager,
    mock_dependency_manager,
    sample_session,
):
    """Test capability filtering - only requested capabilities are executed."""
    # Setup
    mock_session_manager.get.return_value = sample_session
    mock_dependency_manager.get_dependencies_for_session.return_value = []

    # Execute - only request D1 and D3, not D4
    payload = await orchestration_service.build_alignment_payload(
        session_id=str(sample_session.session_id),
        organization_id="org-123",
        capabilities=["core_alignment", "d3_dependencies"],  # No D4
        context={},
        request_id="plot-run-test-002",
    )

    # Assert
    assert payload.alignment is not None  # D1 requested
    assert payload.organizational_context.dependencies == []  # D3 requested
    assert payload.organizational_context.similar_decisions == []  # D4 not requested

    # Verify D3 was called
    mock_dependency_manager.get_dependencies_for_session.assert_called_once()


@pytest.mark.asyncio
async def test_build_alignment_payload_partial_failure(
    orchestration_service,
    mock_session_manager,
    mock_dependency_manager,
    mock_pattern_analyzer,
    sample_session,
):
    """Test graceful degradation with partial capability failure."""
    # Setup - D1 succeeds, D3 succeeds, D4 fails
    test_org_uuid = "650e8400-e29b-41d4-a716-446655440001"
    mock_session_manager.get.return_value = sample_session
    mock_dependency_manager.get_dependencies_for_session.return_value = []
    mock_pattern_analyzer.extract_patterns.side_effect = Exception(
        "Pattern analyzer timeout"
    )

    # Execute
    payload = await orchestration_service.build_alignment_payload(
        session_id=str(sample_session.session_id),
        organization_id=test_org_uuid,
        capabilities=["core_alignment", "d3_dependencies", "d4_patterns"],
        context={},
        request_id="plot-run-test-003",
    )

    # Assert - should return partial success
    assert isinstance(payload, TaeTeamAlignmentPayload)

    # D1 and D3 should have data
    assert payload.alignment is not None
    assert payload.organizational_context.dependencies == []

    # D4 should be empty (failed)
    assert payload.organizational_context.similar_decisions == []

    # Availability should show D4 unavailable
    assert payload.availability.capabilities.d1_portfolio_analytics is True
    assert payload.availability.capabilities.d3_decision_dependencies is True
    assert payload.availability.capabilities.d4_organizational_patterns is False

    # Should be marked as degraded
    assert payload.availability.degraded is True
    assert "d4_patterns" in payload.availability.degradation_reason


@pytest.mark.asyncio
async def test_build_alignment_payload_all_capabilities_fail(
    orchestration_service,
    mock_session_manager,
    mock_dependency_manager,
    mock_pattern_analyzer,
):
    """Test complete failure when all capabilities fail."""
    # Setup - all capabilities fail with valid UUIDs
    test_session_uuid = "550e8400-e29b-41d4-a716-446655440000"
    test_org_uuid = "650e8400-e29b-41d4-a716-446655440001"
    mock_session_manager.get.side_effect = Exception("Session manager error")
    mock_dependency_manager.get_dependencies_for_session.side_effect = Exception(
        "Dependency error"
    )
    mock_pattern_analyzer.extract_patterns.side_effect = Exception("Pattern error")

    # Execute
    payload = await orchestration_service.build_alignment_payload(
        session_id=test_session_uuid,
        organization_id=test_org_uuid,
        capabilities=["core_alignment", "d3_dependencies", "d4_patterns"],
        context={},
        request_id="plot-run-test-004",
    )

    # Assert
    assert isinstance(payload, TaeTeamAlignmentPayload)

    # No data should be present
    assert payload.alignment is None
    assert payload.decision_quality is None

    # All capabilities should be unavailable
    assert payload.availability.capabilities.d1_portfolio_analytics is False
    assert payload.availability.capabilities.d3_decision_dependencies is False
    assert payload.availability.capabilities.d4_organizational_patterns is False

    # Should be degraded
    assert payload.availability.degraded is True
    assert payload.availability.tae_available is True  # Service is up, capabilities failed


@pytest.mark.asyncio
async def test_build_alignment_payload_no_session_id(orchestration_service):
    """Test building payload without session ID (portfolio query)."""
    # Execute
    payload = await orchestration_service.build_alignment_payload(
        session_id=None,  # No session
        organization_id="org-123",
        capabilities=["d4_patterns"],  # Only org-level capability
        context={},
        request_id="plot-run-test-005",
    )

    # Assert
    assert payload.session_id is None
    assert payload.alignment is None  # No session-specific data
    assert payload.decision_quality is None


# =============================================================================
# TEST DECISION QUALITY METRICS
# =============================================================================


@pytest.mark.asyncio
async def test_build_decision_quality_high_consensus(orchestration_service):
    """Test decision quality with high consensus."""
    # Setup
    alignment_data = AlignmentData(
        session_state="deliberating",
        stakeholder_count=5,
        perspectives_collected=5,
        options_proposed=3,
        consensus_level=0.9,  # High consensus
        shared_ground=SharedGroundData(
            summary="Strong agreement", common_goal_weights={}, aligned_priorities=[]
        ),
        disagreements=DisagreementData(
            summary="Minor disagreements",
            axes=[
                DisagreementAxis(
                    dimension="timeline",
                    stakeholders_involved=["PM"],
                    severity_score=0.2,  # Low severity
                    description="Minor timing concern",
                )
            ],
        ),
    )

    # Execute
    quality = orchestration_service._build_decision_quality(alignment_data)

    # Assert
    assert isinstance(quality, DecisionQualityMetrics)
    assert quality.health_score >= 0.8  # High health score
    assert len(quality.risk_flags) == 0  # No risk flags


@pytest.mark.asyncio
async def test_build_decision_quality_low_consensus(orchestration_service):
    """Test decision quality with low consensus."""
    # Setup
    alignment_data = AlignmentData(
        session_state="deliberating",
        stakeholder_count=5,
        perspectives_collected=5,
        options_proposed=3,
        consensus_level=0.3,  # Low consensus
        shared_ground=SharedGroundData(
            summary="Limited agreement", common_goal_weights={}, aligned_priorities=[]
        ),
        disagreements=DisagreementData(
            summary="Significant disagreements",
            axes=[
                DisagreementAxis(
                    dimension="feasibility",
                    stakeholders_involved=["PM", "Engineer"],
                    severity_score=0.8,
                    description="Major feasibility concern",
                ),
                DisagreementAxis(
                    dimension="timeline",
                    stakeholders_involved=["PM", "Designer"],
                    severity_score=0.7,
                    description="Timeline conflict",
                ),
                DisagreementAxis(
                    dimension="scope",
                    stakeholders_involved=["All"],
                    severity_score=0.6,
                    description="Scope disagreement",
                ),
                DisagreementAxis(
                    dimension="priority",
                    stakeholders_involved=["PM", "Designer"],
                    severity_score=0.5,
                    description="Priority mismatch",
                ),
            ],
        ),
    )

    # Execute
    quality = orchestration_service._build_decision_quality(alignment_data)

    # Assert
    assert isinstance(quality, DecisionQualityMetrics)
    assert quality.health_score < 0.5  # Low health score
    assert "Low consensus" in quality.risk_flags
    assert "Multiple disagreement axes" in quality.risk_flags


# =============================================================================
# TEST SESSION STATUS MAPPING
# =============================================================================


def test_map_session_status(orchestration_service):
    """Test session status mapping."""
    # Test all status mappings with SessionStatus enum
    assert (
        orchestration_service._map_session_status(SessionStatus.COLLECTING)
        == "collecting_perspectives"
    )
    assert (
        orchestration_service._map_session_status(SessionStatus.ANALYZING)
        == "proposing_options"
    )
    assert (
        orchestration_service._map_session_status(SessionStatus.DELIBERATING)
        == "deliberating"
    )
    assert (
        orchestration_service._map_session_status(SessionStatus.COMPLETE) == "decided"
    )
    # Test unknown status
    assert orchestration_service._map_session_status("unknown_status") == "unknown"


# =============================================================================
# TEST CONSENSUS CALCULATION
# =============================================================================


def test_calculate_consensus_with_shared_ground(orchestration_service):
    """Test consensus calculation with shared ground."""
    # Setup - session with strong shared ground
    session = MagicMock()
    session.shared_ground = {
        "common_priorities": ["Priority 1", "Priority 2", "Priority 3", "Priority 4"]
    }

    # Execute
    consensus = orchestration_service._calculate_consensus(session)

    # Assert
    assert consensus == 0.8  # 4+ priorities = 0.8


def test_calculate_consensus_moderate_shared_ground(orchestration_service):
    """Test consensus calculation with moderate shared ground."""
    # Setup
    session = MagicMock()
    session.shared_ground = {"common_priorities": ["Priority 1", "Priority 2"]}

    # Execute
    consensus = orchestration_service._calculate_consensus(session)

    # Assert
    assert consensus == 0.6  # 1-2 priorities = 0.6


def test_calculate_consensus_no_shared_ground(orchestration_service):
    """Test consensus calculation without shared ground."""
    # Setup
    session = MagicMock()
    session.shared_ground = None

    # Execute
    consensus = orchestration_service._calculate_consensus(session)

    # Assert
    assert consensus == 0.5  # Default
