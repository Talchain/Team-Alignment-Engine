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
