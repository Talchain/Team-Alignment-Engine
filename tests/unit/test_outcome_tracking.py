"""Unit tests for Phase 5 outcome tracking service."""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.services.outcome_tracking import OutcomeTrackingService
from src.models.outcomes import (
    DecisionOutcomeV1,
    PredictedOutcomeV1,
    ActualOutcomeV1,
    TrackDecisionOutcomeRequestV1,
    RecordActualOutcomeRequestV1,
    OutcomeAnalysisResponseV1,
)
from src.models.consensus import SynthesisOptionV1


@pytest.fixture
def mock_repository():
    """Create mock outcome repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def outcome_service(mock_repository):
    """Create outcome tracking service with mock repository."""
    return OutcomeTrackingService(repository=mock_repository)


@pytest.fixture
def sample_synthesis_option():
    """Create sample synthesis option."""
    return SynthesisOptionV1(
        option_id="option-1",
        title="Launch Feature X",
        description="New AI-powered feature for users",
        causal_rationale="Based on user demand and market analysis",
        source_user_ids=["user1", "user2"],
        support_score=0.85,
    )


@pytest.fixture
def sample_predicted_outcomes():
    """Create sample predicted outcomes."""
    return [
        PredictedOutcomeV1(
            metric="revenue",
            predicted_value=100000.0,
            confidence_interval={"lower": 80000.0, "upper": 120000.0},
            time_horizon="90 days",
        ),
        PredictedOutcomeV1(
            metric="user_adoption",
            predicted_value=0.25,
            confidence_interval={"lower": 0.20, "upper": 0.30},
            time_horizon="30 days",
        ),
    ]


# =============================================================================
# TRACK DECISION OUTCOME TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_track_decision_outcome_success(
    outcome_service, mock_repository, sample_synthesis_option, sample_predicted_outcomes
):
    """Test tracking a decision outcome with predictions."""
    request = TrackDecisionOutcomeRequestV1(
        session_id="session-123",
        selected_option=sample_synthesis_option,
        predicted_outcomes=sample_predicted_outcomes,
        measurement_schedule=[
            {"metric": "revenue", "measure_at": "2025-04-01"},
            {"metric": "user_adoption", "measure_at": "2025-03-01"},
        ],
    )

    # Mock repository response
    mock_repository.create_outcome.return_value = DecisionOutcomeV1(
        outcome_id=uuid4(),
        session_id=request.session_id,
        decision={"selected_option": sample_synthesis_option.model_dump()},
        predicted_outcomes=sample_predicted_outcomes,
        actual_outcomes=None,
        status="predicted",
        created_at=datetime.utcnow(),
        measured_at=None,
    )

    # Track outcome
    response = await outcome_service.track_decision_outcome(request)

    # Assertions
    assert response.status == "predicted"
    assert response.outcome_id is not None
    assert response.next_measurement_date == "2025-03-01"  # Earliest date

    # Verify repository was called
    mock_repository.create_outcome.assert_called_once()
    call_args = mock_repository.create_outcome.call_args[0][0]
    assert call_args.session_id == request.session_id
    assert len(call_args.predicted_outcomes) == 2


@pytest.mark.asyncio
async def test_track_decision_outcome_no_schedule(
    outcome_service, mock_repository, sample_synthesis_option, sample_predicted_outcomes
):
    """Test tracking outcome without measurement schedule."""
    request = TrackDecisionOutcomeRequestV1(
        session_id="session-123",
        selected_option=sample_synthesis_option,
        predicted_outcomes=sample_predicted_outcomes,
        measurement_schedule=[],  # Empty schedule
    )

    mock_repository.create_outcome.return_value = DecisionOutcomeV1(
        outcome_id=uuid4(),
        session_id=request.session_id,
        decision={},
        predicted_outcomes=sample_predicted_outcomes,
        actual_outcomes=None,
        status="predicted",
        created_at=datetime.utcnow(),
        measured_at=None,
    )

    response = await outcome_service.track_decision_outcome(request)

    assert response.next_measurement_date is None  # No schedule


# =============================================================================
# RECORD ACTUAL OUTCOME TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_record_actual_outcome_success(outcome_service, mock_repository, sample_predicted_outcomes):
    """Test recording actual outcomes."""
    outcome_id = uuid4()

    # Mock existing outcome
    mock_repository.get_outcome.return_value = DecisionOutcomeV1(
        outcome_id=outcome_id,
        session_id="session-123",
        decision={},
        predicted_outcomes=sample_predicted_outcomes,
        actual_outcomes=None,
        status="predicted",
        created_at=datetime.utcnow(),
        measured_at=None,
    )

    # Mock measurement creation
    mock_repository.create_measurement.return_value = MagicMock()

    # Record actual outcomes
    actual_outcomes = [
        ActualOutcomeV1(
            metric="revenue",
            actual_value=95000.0,
            measured_at=datetime.utcnow(),
            variance_from_prediction=-0.05,  # 5% under
        ),
        ActualOutcomeV1(
            metric="user_adoption",
            actual_value=0.27,
            measured_at=datetime.utcnow(),
            variance_from_prediction=0.08,  # 8% over
        ),
    ]

    request = RecordActualOutcomeRequestV1(
        outcome_id=outcome_id,
        actual_outcomes=actual_outcomes,
        notes="Q1 measurement complete",
    )

    response = await outcome_service.record_actual_outcome(request)

    # Assertions
    assert response.outcome_id == outcome_id
    assert response.measurements_recorded == 2
    assert response.status == "measured"

    # Verify repository calls
    mock_repository.get_outcome.assert_called_once_with(outcome_id)
    assert mock_repository.create_measurement.call_count == 2
    mock_repository.update_outcome_status.assert_called_once()


@pytest.mark.asyncio
async def test_record_actual_outcome_not_found(outcome_service, mock_repository):
    """Test recording actual outcome for non-existent outcome."""
    outcome_id = uuid4()
    mock_repository.get_outcome.return_value = None

    request = RecordActualOutcomeRequestV1(
        outcome_id=outcome_id,
        actual_outcomes=[],
    )

    with pytest.raises(ValueError, match="not found"):
        await outcome_service.record_actual_outcome(request)


@pytest.mark.asyncio
async def test_record_actual_outcome_no_matching_predictions(
    outcome_service, mock_repository, sample_predicted_outcomes
):
    """Test recording outcomes with metrics not in predictions."""
    outcome_id = uuid4()

    mock_repository.get_outcome.return_value = DecisionOutcomeV1(
        outcome_id=outcome_id,
        session_id="session-123",
        decision={},
        predicted_outcomes=sample_predicted_outcomes,  # revenue, user_adoption
        actual_outcomes=None,
        status="predicted",
        created_at=datetime.utcnow(),
        measured_at=None,
    )

    # Metric not in predictions
    actual_outcomes = [
        ActualOutcomeV1(
            metric="customer_satisfaction",  # NOT predicted
            actual_value=4.5,
            measured_at=datetime.utcnow(),
            variance_from_prediction=0.0,
        ),
    ]

    request = RecordActualOutcomeRequestV1(
        outcome_id=outcome_id,
        actual_outcomes=actual_outcomes,
    )

    response = await outcome_service.record_actual_outcome(request)

    # Should skip unpredicted metrics
    assert response.measurements_recorded == 0
    assert mock_repository.create_measurement.call_count == 0


# =============================================================================
# ANALYZE OUTCOME TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_analyze_outcome_success(outcome_service, mock_repository, sample_predicted_outcomes):
    """Test analyzing outcome accuracy."""
    outcome_id = uuid4()

    actual_outcomes = [
        ActualOutcomeV1(
            metric="revenue",
            actual_value=95000.0,
            measured_at=datetime.utcnow(),
            variance_from_prediction=-0.05,  # 5% under - EXCELLENT
        ),
        ActualOutcomeV1(
            metric="user_adoption",
            actual_value=0.27,
            measured_at=datetime.utcnow(),
            variance_from_prediction=0.08,  # 8% over - EXCELLENT
        ),
    ]

    mock_repository.get_outcome.return_value = DecisionOutcomeV1(
        outcome_id=outcome_id,
        session_id="session-123",
        decision={"key_assumptions": [{"assumption_id": "a1", "description": "Test"}]},
        predicted_outcomes=sample_predicted_outcomes,
        actual_outcomes=actual_outcomes,
        status="measured",
        created_at=datetime.utcnow(),
        measured_at=datetime.utcnow(),
    )

    response = await outcome_service.analyze_outcome(outcome_id)

    # Assertions
    assert len(response.accuracy_analysis) == 2

    # Check accuracy grading
    revenue_analysis = next(a for a in response.accuracy_analysis if a.metric == "revenue")
    assert revenue_analysis.prediction_error == 0.05
    assert revenue_analysis.accuracy_grade == "excellent"  # < 10% error

    # Check assumption validation
    assert len(response.assumption_validation) == 1
    assert response.assumption_validation[0].validated  # Good accuracy means assumptions held

    # Verify status updated to analyzed
    mock_repository.update_outcome_status.assert_called_once_with(
        outcome_id=outcome_id,
        status="analyzed",
    )


@pytest.mark.asyncio
async def test_analyze_outcome_not_measured(outcome_service, mock_repository, sample_predicted_outcomes):
    """Test analyzing outcome that hasn't been measured yet."""
    outcome_id = uuid4()

    mock_repository.get_outcome.return_value = DecisionOutcomeV1(
        outcome_id=outcome_id,
        session_id="session-123",
        decision={},
        predicted_outcomes=sample_predicted_outcomes,
        actual_outcomes=None,  # Not measured yet
        status="predicted",
        created_at=datetime.utcnow(),
        measured_at=None,
    )

    with pytest.raises(ValueError, match="has not been measured"):
        await outcome_service.analyze_outcome(outcome_id)


@pytest.mark.asyncio
async def test_analyze_outcome_poor_accuracy(outcome_service, mock_repository, sample_predicted_outcomes):
    """Test analyzing outcome with poor prediction accuracy."""
    outcome_id = uuid4()

    actual_outcomes = [
        ActualOutcomeV1(
            metric="revenue",
            actual_value=60000.0,  # 40% under prediction
            measured_at=datetime.utcnow(),
            variance_from_prediction=-0.40,
        ),
    ]

    mock_repository.get_outcome.return_value = DecisionOutcomeV1(
        outcome_id=outcome_id,
        session_id="session-123",
        decision={"key_assumptions": [{"assumption_id": "a1", "description": "Test"}]},
        predicted_outcomes=sample_predicted_outcomes,
        actual_outcomes=actual_outcomes,
        status="measured",
        created_at=datetime.utcnow(),
        measured_at=datetime.utcnow(),
    )

    response = await outcome_service.analyze_outcome(outcome_id)

    # Check poor accuracy grade
    revenue_analysis = next(a for a in response.accuracy_analysis if a.metric == "revenue")
    assert revenue_analysis.prediction_error == 0.40
    assert revenue_analysis.accuracy_grade == "poor"  # >= 20% error

    # Poor accuracy means assumptions didn't hold
    assert not response.assumption_validation[0].validated


# =============================================================================
# GET OUTCOMES TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_outcomes_for_session(outcome_service, mock_repository):
    """Test retrieving outcomes for a session."""
    session_id = "session-123"
    outcomes = [
        DecisionOutcomeV1(
            outcome_id=uuid4(),
            session_id=session_id,
            decision={},
            predicted_outcomes=[],
            actual_outcomes=None,
            status="predicted",
            created_at=datetime.utcnow(),
            measured_at=None,
        ),
        DecisionOutcomeV1(
            outcome_id=uuid4(),
            session_id=session_id,
            decision={},
            predicted_outcomes=[],
            actual_outcomes=[],
            status="measured",
            created_at=datetime.utcnow(),
            measured_at=datetime.utcnow(),
        ),
    ]

    mock_repository.get_outcomes_for_session.return_value = outcomes

    result = await outcome_service.get_outcomes_for_session(session_id)

    assert len(result) == 2
    assert all(o.session_id == session_id for o in result)
    mock_repository.get_outcomes_for_session.assert_called_once_with(session_id)
