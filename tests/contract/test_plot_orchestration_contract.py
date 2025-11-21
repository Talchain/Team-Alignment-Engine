"""Contract tests for PLoT orchestration endpoint.

These tests validate that the API contract matches the expected schema
and that responses conform to golden fixtures for cross-team testing.
"""

import pytest
import json
from pathlib import Path
from typing import Dict, Any
from pydantic import ValidationError

from src.models.plot import (
    PlotAlignmentRequest,
    TaeTeamAlignmentPayload,
    AlignmentData,
    DecisionQualityMetrics,
    OrganizationalContext,
    AvailabilityStatus,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fixtures_dir() -> Path:
    """Get fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def golden_full_response(fixtures_dir) -> Dict[str, Any]:
    """Load golden fixture for full response."""
    with open(fixtures_dir / "golden_full_response.json") as f:
        return json.load(f)


@pytest.fixture
def golden_partial_d1d3(fixtures_dir) -> Dict[str, Any]:
    """Load golden fixture for partial request (D1+D3 only)."""
    with open(fixtures_dir / "golden_partial_d1d3.json") as f:
        return json.load(f)


@pytest.fixture
def golden_partial_failure(fixtures_dir) -> Dict[str, Any]:
    """Load golden fixture for partial failure (D4 fails)."""
    with open(fixtures_dir / "golden_partial_failure.json") as f:
        return json.load(f)


@pytest.fixture
def golden_error_response(fixtures_dir) -> Dict[str, Any]:
    """Load golden fixture for complete failure."""
    with open(fixtures_dir / "golden_error_response.json") as f:
        return json.load(f)


@pytest.fixture
def golden_full_with_d2_d5_d6(fixtures_dir) -> Dict[str, Any]:
    """Load golden fixture for full response with D2/D5/D6."""
    with open(fixtures_dir / "golden_full_with_d2_d5_d6.json") as f:
        return json.load(f)


@pytest.fixture
def golden_d5_analytics_only(fixtures_dir) -> Dict[str, Any]:
    """Load golden fixture for D5 analytics only."""
    with open(fixtures_dir / "golden_d5_analytics_only.json") as f:
        return json.load(f)


@pytest.fixture
def golden_d6_conflicts_only(fixtures_dir) -> Dict[str, Any]:
    """Load golden fixture for D6 conflicts only."""
    with open(fixtures_dir / "golden_d6_conflicts_only.json") as f:
        return json.load(f)


@pytest.fixture
def golden_d2_collaboration_only(fixtures_dir) -> Dict[str, Any]:
    """Load golden fixture for D2 collaboration only."""
    with open(fixtures_dir / "golden_d2_collaboration_only.json") as f:
        return json.load(f)


@pytest.fixture
def golden_partial_d5_d6_failure(fixtures_dir) -> Dict[str, Any]:
    """Load golden fixture for D5/D6 partial failure."""
    with open(fixtures_dir / "golden_partial_d5_d6_failure.json") as f:
        return json.load(f)


# =============================================================================
# SCHEMA VALIDATION TESTS
# =============================================================================


def test_tae_team_alignment_payload_schema():
    """Test TaeTeamAlignmentPayload schema definition."""
    # Verify Pydantic model exists and has correct fields
    schema = TaeTeamAlignmentPayload.model_json_schema()

    # Required fields (timestamp has default_factory, so not required)
    required_fields = schema.get("required", [])
    assert "organization_id" in required_fields
    assert "version" in required_fields
    assert "availability" in required_fields

    # All fields should be in properties
    properties = schema.get("properties", {})
    assert "session_id" in properties
    assert "timestamp" in properties  # Has default, but in properties
    assert "organizational_context" in properties
    assert "alignment" in properties
    assert "decision_quality" in properties
    assert "collaboration" in properties


def test_plot_alignment_request_schema():
    """Test PlotAlignmentRequest schema definition."""
    schema = PlotAlignmentRequest.model_json_schema()

    # Required fields
    required_fields = schema.get("required", [])
    assert "organization_id" in required_fields

    # Optional fields
    properties = schema.get("properties", {})
    assert "session_id" in properties
    assert "capabilities" in properties
    assert "context" in properties


def test_availability_status_schema():
    """Test AvailabilityStatus schema definition."""
    schema = AvailabilityStatus.model_json_schema()

    # Required fields (capabilities has default_factory, so not required)
    required_fields = schema.get("required", [])
    assert "tae_available" in required_fields
    assert "degraded" in required_fields

    # All fields should be in properties
    properties = schema.get("properties", {})
    assert "capabilities" in properties  # Has default, but in properties
    assert "degradation_reason" in properties


# =============================================================================
# GOLDEN FIXTURE VALIDATION
# =============================================================================


def test_golden_full_response_validates(golden_full_response):
    """Test golden full response conforms to TaeTeamAlignmentPayload schema."""
    # Should not raise ValidationError
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    # Verify key fields
    assert payload.session_id == "550e8400-e29b-41d4-a716-446655440000"
    assert payload.organization_id == "org-123"
    assert payload.version == "2.0.0"
    assert payload.request_id == "plot-run-abc123"

    # Verify alignment data present
    assert payload.alignment is not None
    assert payload.alignment.stakeholder_count == 3
    assert payload.alignment.session_state == "deliberating"

    # Verify decision quality
    assert payload.decision_quality is not None
    assert 0.0 <= payload.decision_quality.health_score <= 1.0

    # Verify organizational context
    assert len(payload.organizational_context.similar_decisions) == 2
    assert len(payload.organizational_context.dependencies) == 1

    # Verify availability
    assert payload.availability.tae_available is True
    assert payload.availability.capabilities.d1_portfolio_analytics is True
    assert payload.availability.capabilities.d3_decision_dependencies is True
    assert payload.availability.capabilities.d4_organizational_patterns is True
    assert payload.availability.degraded is False


def test_golden_partial_d1d3_validates(golden_partial_d1d3):
    """Test golden partial request (D1+D3) conforms to schema."""
    payload = TaeTeamAlignmentPayload(**golden_partial_d1d3)

    # Verify alignment data present
    assert payload.alignment is not None
    assert payload.alignment.session_state == "proposing_options"

    # Verify dependencies present
    assert len(payload.organizational_context.dependencies) == 1

    # Verify patterns not present (not requested)
    assert len(payload.organizational_context.similar_decisions) == 0

    # Verify availability
    assert payload.availability.degraded is False


def test_golden_partial_failure_validates(golden_partial_failure):
    """Test golden partial failure (D4 fails) conforms to schema."""
    payload = TaeTeamAlignmentPayload(**golden_partial_failure)

    # Verify alignment data present (D1 succeeded)
    assert payload.alignment is not None

    # Verify patterns not present (D4 failed)
    assert len(payload.organizational_context.similar_decisions) == 0

    # Verify availability reflects failure
    assert payload.availability.capabilities.d1_portfolio_analytics is True
    assert payload.availability.capabilities.d3_decision_dependencies is True
    assert payload.availability.capabilities.d4_organizational_patterns is False
    assert payload.availability.degraded is True
    assert "d4_patterns" in payload.availability.degradation_reason


def test_golden_error_response_validates(golden_error_response):
    """Test golden error response (complete failure) conforms to schema."""
    payload = TaeTeamAlignmentPayload(**golden_error_response)

    # Verify no data present
    assert payload.alignment is None
    assert payload.decision_quality is None

    # Verify all capabilities unavailable
    assert payload.availability.capabilities.d1_portfolio_analytics is False
    assert payload.availability.capabilities.d3_decision_dependencies is False
    assert payload.availability.capabilities.d4_organizational_patterns is False
    assert payload.availability.degraded is True


# =============================================================================
# RESPONSE STRUCTURE TESTS
# =============================================================================


def test_response_has_metadata_fields(golden_full_response):
    """Test response contains required metadata fields."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    # Metadata fields must be present
    assert payload.session_id is not None
    assert payload.organization_id is not None
    assert payload.timestamp is not None
    assert payload.version is not None
    assert payload.request_id is not None


def test_response_has_availability_status(golden_full_response):
    """Test response contains availability status."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    # Availability must be present
    assert payload.availability is not None
    assert payload.availability.tae_available is not None
    assert payload.availability.capabilities is not None
    assert payload.availability.degraded is not None


def test_alignment_data_structure(golden_full_response):
    """Test alignment data has correct structure."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    assert payload.alignment is not None
    assert hasattr(payload.alignment, "session_state")
    assert hasattr(payload.alignment, "stakeholder_count")
    assert hasattr(payload.alignment, "perspectives_collected")
    assert hasattr(payload.alignment, "options_proposed")
    assert hasattr(payload.alignment, "consensus_level")
    assert hasattr(payload.alignment, "shared_ground")
    assert hasattr(payload.alignment, "disagreements")


def test_decision_quality_structure(golden_full_response):
    """Test decision quality has correct structure."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    assert payload.decision_quality is not None
    assert hasattr(payload.decision_quality, "health_score")
    assert hasattr(payload.decision_quality, "risk_flags")
    assert hasattr(payload.decision_quality, "causally_validated")
    assert hasattr(payload.decision_quality, "assumption_strength")
    assert hasattr(payload.decision_quality, "minority_concerns")


def test_organizational_context_structure(golden_full_response):
    """Test organizational context has correct structure."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    assert payload.organizational_context is not None
    assert hasattr(payload.organizational_context, "similar_decisions")
    assert hasattr(payload.organizational_context, "dependencies")
    assert hasattr(payload.organizational_context, "trend_insights")
    assert hasattr(payload.organizational_context, "conflicts")


# =============================================================================
# DATA VALIDATION TESTS
# =============================================================================


def test_consensus_level_range(golden_full_response):
    """Test consensus level is within valid range."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    assert payload.alignment is not None
    assert 0.0 <= payload.alignment.consensus_level <= 1.0


def test_health_score_range(golden_full_response):
    """Test health score is within valid range."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    assert payload.decision_quality is not None
    assert 0.0 <= payload.decision_quality.health_score <= 1.0


def test_similarity_score_range(golden_full_response):
    """Test pattern similarity scores are within valid range."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    for pattern in payload.organizational_context.similar_decisions:
        assert 0.0 <= pattern.similarity <= 1.0


def test_disagreement_severity_range(golden_full_response):
    """Test disagreement severity scores are within valid range."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    if payload.alignment and payload.alignment.disagreements:
        for axis in payload.alignment.disagreements.axes:
            assert 0.0 <= axis.severity_score <= 1.0


# =============================================================================
# CAPABILITY FLAGS TESTS
# =============================================================================


def test_poc_v02_capability_flags(golden_full_response):
    """Test capability flags match POC v02 priorities."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    # D1/D3/D4 should be enabled for POC v02
    assert payload.availability.capabilities.d1_portfolio_analytics is True
    assert payload.availability.capabilities.d3_decision_dependencies is True
    assert payload.availability.capabilities.d4_organizational_patterns is True

    # D2/D5/D6 should be disabled for POC v02
    assert payload.availability.capabilities.d2_realtime_collaboration is False
    assert payload.availability.capabilities.d5_advanced_analytics is False
    assert payload.availability.capabilities.d6_cross_team_coordination is False


def test_deferred_capabilities_null(golden_full_response):
    """Test deferred capabilities (D2/D5/D6) are null."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    # D2: Real-time collaboration deferred
    assert payload.collaboration is None

    # D5: Advanced analytics deferred
    assert payload.organizational_context.trend_insights is None

    # D6: Cross-team coordination deferred
    assert len(payload.organizational_context.conflicts) == 0


# =============================================================================
# JSON SERIALIZATION TESTS
# =============================================================================


def test_payload_serializes_to_json(golden_full_response):
    """Test payload can be serialized to JSON."""
    payload = TaeTeamAlignmentPayload(**golden_full_response)

    # Should serialize without errors
    json_str = payload.model_dump_json()
    assert isinstance(json_str, str)

    # Should deserialize back
    json_dict = json.loads(json_str)
    payload2 = TaeTeamAlignmentPayload(**json_dict)
    assert payload2.session_id == payload.session_id


def test_all_golden_fixtures_serialize():
    """Test all golden fixtures can be serialized/deserialized."""
    fixtures_dir = Path(__file__).parent / "fixtures"

    for fixture_file in fixtures_dir.glob("golden_*.json"):
        with open(fixture_file) as f:
            data = json.load(f)

        # Should validate
        payload = TaeTeamAlignmentPayload(**data)

        # Should serialize
        json_str = payload.model_dump_json()

        # Should deserialize
        payload2 = TaeTeamAlignmentPayload.model_validate_json(json_str)
        assert payload2.organization_id == payload.organization_id


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


def test_session_id_accepts_any_string():
    """Test session_id accepts any string (no UUID validation)."""
    # session_id is Optional[str], so any string is valid
    payload = TaeTeamAlignmentPayload(
        session_id="not-a-uuid",  # Any string is valid
        organization_id="org-123",
        timestamp="2025-11-21T12:00:00Z",
        version="2.0.0",
        request_id="plot-run-test",
        alignment=None,
        decision_quality=None,
        organizational_context={
            "similar_decisions": [],
            "dependencies": [],
            "conflicts": [],
        },
        collaboration=None,
        availability={
            "tae_available": True,
            "capabilities": {
                "d1_portfolio_analytics": True,
                "d2_realtime_collaboration": False,
                "d3_decision_dependencies": True,
                "d4_organizational_patterns": True,
                "d5_advanced_analytics": False,
                "d6_cross_team_coordination": False,
            },
            "degraded": False,
            "degradation_reason": None,
        },
    )

    assert payload.session_id == "not-a-uuid"


def test_missing_required_fields_rejected():
    """Test missing required fields are rejected."""
    with pytest.raises(ValidationError):
        TaeTeamAlignmentPayload(
            # Missing organization_id (required)
            session_id="550e8400-e29b-41d4-a716-446655440000",
            timestamp="2025-11-21T12:00:00Z",
            version="2.0.0",
        )


def test_invalid_consensus_level_rejected():
    """Test consensus level outside 0-1 range is rejected."""
    with pytest.raises(ValidationError):
        AlignmentData(
            session_state="deliberating",
            stakeholder_count=3,
            perspectives_collected=3,
            options_proposed=2,
            consensus_level=1.5,  # Invalid: > 1.0
            shared_ground={
                "summary": "Test",
                "common_goal_weights": {},
                "aligned_priorities": [],
            },
            disagreements={"summary": "Test", "axes": []},
        )


# =============================================================================
# D2/D5/D6 GOLDEN FIXTURE TESTS (Phase 3)
# =============================================================================


def test_golden_full_with_d2_d5_d6_validates(golden_full_with_d2_d5_d6):
    """Test golden fixture with all D2/D5/D6 capabilities validates."""
    payload = TaeTeamAlignmentPayload(**golden_full_with_d2_d5_d6)

    # Verify metadata
    assert payload.session_id == "550e8400-e29b-41d4-a716-446655440000"
    assert payload.organization_id == "org-456"
    assert payload.request_id == "plot-run-d2d5d6-001"

    # Verify D1 (core alignment) present
    assert payload.alignment is not None
    assert payload.alignment.stakeholder_count == 4

    # Verify D5 (analytics) present
    assert payload.organizational_context.trend_insights is not None
    assert "baseline" in payload.organizational_context.trend_insights.organization_decision_velocity
    assert payload.organizational_context.trend_insights.quality_trend in ["improving", "declining", "stable"]
    assert payload.organizational_context.trend_insights.forecast is not None

    # Verify D6 (conflicts) present
    assert len(payload.organizational_context.conflicts) == 2
    assert payload.organizational_context.conflicts[0].conflict_type in ["resource", "temporal", "scope"]
    assert payload.organizational_context.conflicts[0].severity in ["low", "medium", "high"]

    # Verify D2 (collaboration) present
    assert payload.collaboration is not None
    assert len(payload.collaboration.active_stakeholders) == 4
    assert len(payload.collaboration.recent_actions) == 4
    assert payload.collaboration.recent_actions[0].action_type in [
        "vote_cast", "concern_raised", "option_proposed", "perspective_added"
    ]

    # Verify all capabilities enabled
    assert payload.availability.capabilities.d1_portfolio_analytics is True
    assert payload.availability.capabilities.d2_realtime_collaboration is True
    assert payload.availability.capabilities.d3_decision_dependencies is True
    assert payload.availability.capabilities.d4_organizational_patterns is True
    assert payload.availability.capabilities.d5_advanced_analytics is True
    assert payload.availability.capabilities.d6_cross_team_coordination is True
    assert payload.availability.degraded is False


def test_golden_d5_analytics_only_validates(golden_d5_analytics_only):
    """Test golden fixture for D5 analytics only validates."""
    payload = TaeTeamAlignmentPayload(**golden_d5_analytics_only)

    # Verify no session-level data (portfolio query)
    assert payload.session_id is None
    assert payload.alignment is None
    assert payload.decision_quality is None

    # Verify D5 analytics present
    assert payload.organizational_context.trend_insights is not None
    assert payload.organizational_context.trend_insights.organization_decision_velocity is not None
    assert payload.organizational_context.trend_insights.quality_trend in ["improving", "declining", "stable"]

    # Verify forecast data structure
    assert "velocity_forecast" in payload.organizational_context.trend_insights.forecast
    assert "quality_forecast" in payload.organizational_context.trend_insights.forecast
    assert "confidence_intervals" in payload.organizational_context.trend_insights.forecast
    assert "trend_strength" in payload.organizational_context.trend_insights.forecast

    # Verify only D5 enabled
    assert payload.availability.capabilities.d5_advanced_analytics is True
    assert payload.availability.capabilities.d1_portfolio_analytics is False
    assert payload.availability.capabilities.d2_realtime_collaboration is False
    assert payload.availability.capabilities.d3_decision_dependencies is False
    assert payload.availability.capabilities.d4_organizational_patterns is False
    assert payload.availability.capabilities.d6_cross_team_coordination is False


def test_golden_d6_conflicts_only_validates(golden_d6_conflicts_only):
    """Test golden fixture for D6 conflicts only validates."""
    payload = TaeTeamAlignmentPayload(**golden_d6_conflicts_only)

    # Verify conflicts present
    assert len(payload.organizational_context.conflicts) == 3

    # Verify conflict structure
    for conflict in payload.organizational_context.conflicts:
        assert conflict.conflicting_session_id is not None
        assert conflict.conflict_type in ["resource", "temporal", "scope"]
        assert conflict.severity in ["low", "medium", "high"]
        assert conflict.resolution_suggestion is not None

    # Verify severity levels present
    severities = [c.severity for c in payload.organizational_context.conflicts]
    assert "high" in severities
    assert "medium" in severities
    assert "low" in severities

    # Verify only D6 enabled
    assert payload.availability.capabilities.d6_cross_team_coordination is True
    assert payload.availability.capabilities.d1_portfolio_analytics is False
    assert payload.availability.capabilities.d2_realtime_collaboration is False
    assert payload.availability.capabilities.d3_decision_dependencies is False
    assert payload.availability.capabilities.d4_organizational_patterns is False
    assert payload.availability.capabilities.d5_advanced_analytics is False


def test_golden_d2_collaboration_only_validates(golden_d2_collaboration_only):
    """Test golden fixture for D2 collaboration only validates."""
    payload = TaeTeamAlignmentPayload(**golden_d2_collaboration_only)

    # Verify collaboration present
    assert payload.collaboration is not None
    assert len(payload.collaboration.active_stakeholders) == 3
    assert len(payload.collaboration.recent_actions) == 4

    # Verify action types
    action_types = [a.action_type for a in payload.collaboration.recent_actions]
    assert "vote_cast" in action_types
    assert "concern_raised" in action_types
    assert "perspective_added" in action_types
    assert "option_proposed" in action_types

    # Verify action structure
    for action in payload.collaboration.recent_actions:
        assert action.user_id is not None
        assert action.action_type in [
            "vote_cast", "concern_raised", "option_proposed", "perspective_added"
        ]
        assert action.timestamp is not None
        assert action.metadata is not None

    # Verify only D2 enabled
    assert payload.availability.capabilities.d2_realtime_collaboration is True
    assert payload.availability.capabilities.d1_portfolio_analytics is False
    assert payload.availability.capabilities.d3_decision_dependencies is False
    assert payload.availability.capabilities.d4_organizational_patterns is False
    assert payload.availability.capabilities.d5_advanced_analytics is False
    assert payload.availability.capabilities.d6_cross_team_coordination is False


def test_golden_partial_d5_d6_failure_validates(golden_partial_d5_d6_failure):
    """Test golden fixture for D5/D6 partial failure validates."""
    payload = TaeTeamAlignmentPayload(**golden_partial_d5_d6_failure)

    # Verify D1/D3/D4/D2 succeeded
    assert payload.alignment is not None
    assert len(payload.organizational_context.similar_decisions) > 0
    assert payload.collaboration is not None

    # Verify D5/D6 failed (null or empty)
    assert payload.organizational_context.trend_insights is None
    assert len(payload.organizational_context.conflicts) == 0

    # Verify degraded status
    assert payload.availability.degraded is True
    assert "d5_analytics" in payload.availability.degradation_reason
    assert "d6_coordination" in payload.availability.degradation_reason

    # Verify capability flags reflect failure
    assert payload.availability.capabilities.d1_portfolio_analytics is True
    assert payload.availability.capabilities.d2_realtime_collaboration is True
    assert payload.availability.capabilities.d3_decision_dependencies is True
    assert payload.availability.capabilities.d4_organizational_patterns is True
    assert payload.availability.capabilities.d5_advanced_analytics is False
    assert payload.availability.capabilities.d6_cross_team_coordination is False


# =============================================================================
# D2/D5/D6 DATA VALIDATION TESTS
# =============================================================================


def test_trend_insights_structure(golden_full_with_d2_d5_d6):
    """Test trend insights (D5) have correct structure."""
    payload = TaeTeamAlignmentPayload(**golden_full_with_d2_d5_d6)

    assert payload.organizational_context.trend_insights is not None
    trend = payload.organizational_context.trend_insights

    # Verify required fields
    assert hasattr(trend, "organization_decision_velocity")
    assert hasattr(trend, "quality_trend")
    assert hasattr(trend, "forecast")

    # Verify forecast structure
    assert "velocity_forecast" in trend.forecast
    assert "quality_forecast" in trend.forecast
    assert "confidence_intervals" in trend.forecast
    assert "trend_strength" in trend.forecast

    # Verify trend strength is 0-1
    assert 0.0 <= trend.forecast["trend_strength"] <= 1.0


def test_conflicts_structure(golden_full_with_d2_d5_d6):
    """Test conflicts (D6) have correct structure."""
    payload = TaeTeamAlignmentPayload(**golden_full_with_d2_d5_d6)

    for conflict in payload.organizational_context.conflicts:
        assert hasattr(conflict, "conflicting_session_id")
        assert hasattr(conflict, "conflict_type")
        assert hasattr(conflict, "severity")
        assert hasattr(conflict, "resolution_suggestion")

        # Verify enum values
        assert conflict.conflict_type in ["resource", "temporal", "scope"]
        assert conflict.severity in ["low", "medium", "high"]


def test_collaboration_structure(golden_full_with_d2_d5_d6):
    """Test collaboration (D2) has correct structure."""
    payload = TaeTeamAlignmentPayload(**golden_full_with_d2_d5_d6)

    assert payload.collaboration is not None
    collab = payload.collaboration

    # Verify required fields
    assert hasattr(collab, "active_stakeholders")
    assert hasattr(collab, "recent_actions")

    # Verify action structure
    for action in collab.recent_actions:
        assert hasattr(action, "user_id")
        assert hasattr(action, "action_type")
        assert hasattr(action, "timestamp")
        assert hasattr(action, "metadata")

        # Verify action type enum
        assert action.action_type in [
            "vote_cast", "concern_raised", "option_proposed", "perspective_added"
        ]


def test_all_d2_d5_d6_fixtures_serialize():
    """Test all D2/D5/D6 golden fixtures serialize correctly."""
    fixtures_dir = Path(__file__).parent / "fixtures"

    d2_d5_d6_fixtures = [
        "golden_full_with_d2_d5_d6.json",
        "golden_d5_analytics_only.json",
        "golden_d6_conflicts_only.json",
        "golden_d2_collaboration_only.json",
        "golden_partial_d5_d6_failure.json",
    ]

    for fixture_name in d2_d5_d6_fixtures:
        fixture_path = fixtures_dir / fixture_name
        with open(fixture_path) as f:
            data = json.load(f)

        # Should validate
        payload = TaeTeamAlignmentPayload(**data)

        # Should serialize
        json_str = payload.model_dump_json()

        # Should deserialize
        payload2 = TaeTeamAlignmentPayload.model_validate_json(json_str)
        assert payload2.organization_id == payload.organization_id
