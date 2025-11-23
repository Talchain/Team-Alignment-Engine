"""Unit tests for aggregation intelligence service (Phase 3: Navajas)."""

import pytest
from datetime import datetime, timedelta

from src.services.aggregation_intelligence import AggregationIntelligenceService
from src.models.deliberation import (
    DeliberationSessionV1,
    DeliberationRoundV1,
    ParticipantV1,
    TeamInputV1,
    GraphV1,
    ConvergenceCriteriaV1,
)


@pytest.fixture
def aggregation_service():
    """Create aggregation intelligence service."""
    return AggregationIntelligenceService()


@pytest.fixture
def sample_session():
    """Create sample deliberation session."""
    return DeliberationSessionV1(
        session_id="test-session-1",
        decision_context="Should we adopt microservices architecture?",
        participants=[
            ParticipantV1(user_id="user1", role="engineer"),
            ParticipantV1(user_id="user2", role="product_manager"),
            ParticipantV1(user_id="user3", role="architect"),
        ],
        convergence_criteria=ConvergenceCriteriaV1(
            min_quality_threshold=0.7,
            min_votes_agreement=0.67,
            max_rounds=5,
        ),
    )


class TestConfidenceCalibration:
    """Test confidence calibration functionality."""

    def test_calibrate_confidence_with_no_history(self, aggregation_service):
        """Test calibration with no historical data defaults to stated confidence."""
        result = aggregation_service.calibrate_confidence(
            user_id="new_user",
            stated_confidence=0.8,
            domain="software_architecture",
        )

        assert result.user_id == "new_user"
        assert result.stated_confidence == 0.8
        # With no history, calibrated should be close to stated (with some dampening)
        assert 0.6 <= result.calibrated_confidence <= 0.9
        assert result.calibration_factors.historical_accuracy == 0.5  # Default

    def test_calibrate_confidence_penalizes_overconfidence(self, aggregation_service):
        """Test that overconfident users get downweighted."""
        # Add mock history showing overconfidence
        aggregation_service._user_history["overconfident_user"] = [
            {
                "stated_confidence": 0.9,
                "was_correct": False,
                "brier_score": 0.81,  # Bad score (high = bad)
            },
            {
                "stated_confidence": 0.95,
                "was_correct": False,
                "brier_score": 0.90,
            },
        ]

        result = aggregation_service.calibrate_confidence(
            user_id="overconfident_user",
            stated_confidence=0.9,
            domain="general",
        )

        # Calibrated should be significantly lower than stated
        assert result.calibrated_confidence < result.stated_confidence
        assert result.calibration_factors.overconfidence_bias > 0.0
        assert result.recommendation == "decrease_weight"

    def test_calibrate_confidence_rewards_well_calibrated(self, aggregation_service):
        """Test that well-calibrated users get maintained or increased weight."""
        # Add mock history showing good calibration
        aggregation_service._user_history["calibrated_user"] = [
            {
                "stated_confidence": 0.7,
                "was_correct": True,
                "brier_score": 0.09,  # Good score (low = good)
            },
            {
                "stated_confidence": 0.8,
                "was_correct": True,
                "brier_score": 0.04,
            },
        ]

        result = aggregation_service.calibrate_confidence(
            user_id="calibrated_user",
            stated_confidence=0.75,
            domain="general",
        )

        # Calibrated should be maintained or slightly increased
        assert result.calibrated_confidence >= result.stated_confidence * 0.9
        assert result.calibration_factors.historical_accuracy > 0.7
        assert result.recommendation in ["unchanged", "increase_weight"]


class TestStrategicBehaviorDetection:
    """Test strategic behavior detection."""

    def test_detect_anchoring(self, aggregation_service, sample_session):
        """Test detection of anchoring bias."""
        # Create round with submissions showing anchoring
        round1 = DeliberationRoundV1(
            session_id=sample_session.session_id,
            round_number=1,
            round_type="submission",
        )

        # First submission (anchor)
        first_submission = TeamInputV1(
            user_id="user1",
            graph=GraphV1(
                nodes=["microservices", "scalability", "complexity"],
                edges=[
                    {"source": "microservices", "target": "scalability"},
                    {"source": "microservices", "target": "complexity"},
                ],
            ),
            reasoning="Microservices dramatically improve scalability but increase operational complexity.",
        )
        round1.submissions.append(first_submission)

        # Subsequent submissions using very similar language (anchored)
        for i in range(2, 4):
            anchored_submission = TeamInputV1(
                user_id=f"user{i}",
                graph=GraphV1(
                    nodes=["microservices", "scalability", "complexity"],
                    edges=[
                        {"source": "microservices", "target": "scalability"},
                    ],
                ),
                reasoning=f"Microservices improve scalability but add complexity to operations.",
            )
            round1.submissions.append(anchored_submission)

        sample_session.rounds.append(round1)

        result = aggregation_service.detect_strategic_behavior(sample_session)

        assert result.session_id == sample_session.session_id
        # Should detect anchoring pattern
        anchoring_patterns = [p for p in result.detected_patterns if p.pattern_type == "anchoring"]
        assert len(anchoring_patterns) > 0
        assert anchoring_patterns[0].confidence > 0.5

    def test_detect_conformity(self, aggregation_service, sample_session):
        """Test detection of conformity pressure."""
        # Create multiple rounds with increasing agreement
        for round_num in range(1, 4):
            round_obj = DeliberationRoundV1(
                session_id=sample_session.session_id,
                round_number=round_num,
                round_type="submission",
            )

            # All submissions converge to same graph
            for user in sample_session.participants:
                submission = TeamInputV1(
                    user_id=user.user_id,
                    graph=GraphV1(
                        nodes=["option_a", "outcome"],
                        edges=[{"source": "option_a", "target": "outcome"}],
                    ),
                    reasoning=f"Option A is clearly the best choice (round {round_num}).",
                )
                round_obj.submissions.append(submission)

            sample_session.rounds.append(round_obj)

        result = aggregation_service.detect_strategic_behavior(sample_session)

        # Should detect conformity
        conformity_patterns = [p for p in result.detected_patterns if p.pattern_type == "conformity"]
        assert len(conformity_patterns) > 0

    def test_no_strategic_behavior_with_diverse_input(self, aggregation_service, sample_session):
        """Test that diverse, authentic input doesn't trigger false positives."""
        round1 = DeliberationRoundV1(
            session_id=sample_session.session_id,
            round_number=1,
            round_type="submission",
        )

        # Create diverse submissions
        submissions = [
            TeamInputV1(
                user_id="user1",
                graph=GraphV1(
                    nodes=["microservices", "scalability"],
                    edges=[{"source": "microservices", "target": "scalability"}],
                ),
                reasoning="Microservices enable independent scaling of components.",
            ),
            TeamInputV1(
                user_id="user2",
                graph=GraphV1(
                    nodes=["user_experience", "feature_velocity"],
                    edges=[{"source": "feature_velocity", "target": "user_experience"}],
                ),
                reasoning="Faster feature delivery improves user satisfaction.",
            ),
            TeamInputV1(
                user_id="user3",
                graph=GraphV1(
                    nodes=["monolith", "simplicity", "deployment"],
                    edges=[
                        {"source": "monolith", "target": "simplicity"},
                        {"source": "simplicity", "target": "deployment"},
                    ],
                ),
                reasoning="Monolithic architecture keeps deployment simple and reliable.",
            ),
        ]
        round1.submissions = submissions
        sample_session.rounds.append(round1)

        result = aggregation_service.detect_strategic_behavior(sample_session)

        # With diverse input, should have low confidence in strategic patterns
        for pattern in result.detected_patterns:
            assert pattern.confidence < 0.5


class TestTeamSizeAnalysis:
    """Test team size analysis."""

    def test_recommends_adding_members_for_small_team(self, aggregation_service, sample_session):
        """Test recommendation to add members for team <3."""
        # Reduce to 2 participants
        sample_session.participants = sample_session.participants[:2]

        result = aggregation_service.analyze_team_size(
            sample_session,
            decision_type="strategic",
        )

        assert result.current_team_size == 2
        assert result.recommendation == "add_members"
        assert result.optimal_range["min"] == 3
        assert result.optimal_range["max"] == 5

    def test_recognizes_optimal_team_size(self, aggregation_service, sample_session):
        """Test recognition of optimal 3-5 person team."""
        # Session already has 3 participants (optimal)
        result = aggregation_service.analyze_team_size(
            sample_session,
            decision_type="tactical",
        )

        assert result.current_team_size == 3
        assert 3 <= result.current_team_size <= 5
        # With good diversity, should be optimal
        assert result.analysis.diversity_score > 0.0

    def test_recommends_splitting_large_team(self, aggregation_service, sample_session):
        """Test recommendation to split team >7 with low diversity."""
        # Add many participants
        for i in range(4, 11):
            sample_session.participants.append(
                ParticipantV1(user_id=f"user{i}", role="engineer")
            )

        result = aggregation_service.analyze_team_size(
            sample_session,
            decision_type="operational",
        )

        assert result.current_team_size == 10
        # Should recommend reduction or smaller groups
        assert result.recommendation in ["reduce_size", "run_smaller_groups"]


class TestCommunicationPatternAnalysis:
    """Test communication pattern analysis."""

    def test_analyzes_public_debate_pattern(self, aggregation_service, sample_session):
        """Test analysis of public debate communication."""
        result = aggregation_service.analyze_communication_patterns(sample_session)

        assert result.session_id == sample_session.session_id
        assert len(result.patterns) > 0

        # Should have recommendations
        assert "structure" in result.recommendation
        assert "reasoning" in result.recommendation

    def test_recommends_anonymous_voting_for_conformity(self, aggregation_service, sample_session):
        """Test that high conformity triggers anonymous voting recommendation."""
        # Create session with high conformity
        for round_num in range(1, 3):
            round_obj = DeliberationRoundV1(
                session_id=sample_session.session_id,
                round_number=round_num,
                round_type="submission",
            )

            # All same submission (high conformity)
            for user in sample_session.participants:
                submission = TeamInputV1(
                    user_id=user.user_id,
                    graph=GraphV1(nodes=["a"], edges=[]),
                    reasoning="Same reasoning",
                )
                round_obj.submissions.append(submission)

            sample_session.rounds.append(round_obj)

        # First detect strategic behavior to confirm conformity
        strategy_detection = aggregation_service.detect_strategic_behavior(sample_session)

        # Then analyze communication patterns
        result = aggregation_service.analyze_communication_patterns(sample_session)

        # With conformity, should recommend anonymous voting
        recommendation_text = result.recommendation.get("structure", "").lower()
        assert "anonymous" in recommendation_text or "private" in recommendation_text


class TestSmartWeighting:
    """Test smart weight computation."""

    def test_compute_smart_weights(self, aggregation_service, sample_session):
        """Test computation of smart aggregation weights."""
        # Create mock inputs
        causal_weights = {
            "user1": 0.8,  # High causal quality
            "user2": 0.6,
            "user3": 0.7,
        }

        value_weights = {
            "user1": 0.7,
            "user2": 0.9,  # High value alignment
            "user3": 0.6,
        }

        strategy_detection = aggregation_service.detect_strategic_behavior(sample_session)

        result = aggregation_service.compute_smart_weights(
            session=sample_session,
            causal_weights=causal_weights,
            value_weights=value_weights,
            strategy_detection=strategy_detection,
        )

        assert len(result) == 3

        # Check that weights are normalized
        total_weight = sum(w.final_weight for w in result)
        assert 0.99 <= total_weight <= 1.01  # Allow small floating point error

        # Verify breakdown components present
        for weight_obj in result:
            assert 0.0 <= weight_obj.final_weight <= 1.0
            assert weight_obj.weight_breakdown.causal_quality >= 0.0
            assert weight_obj.weight_breakdown.value_alignment >= 0.0

    def test_strategic_penalty_reduces_weight(self, aggregation_service, sample_session):
        """Test that strategic behavior reduces user weight."""
        # Mock strategic behavior (e.g., conformity)
        from src.models.aggregation import (
            StrategyDetectionV1,
            DetectedPatternV1,
        )

        strategy_detection = StrategyDetectionV1(
            session_id=sample_session.session_id,
            detected_patterns=[
                DetectedPatternV1(
                    pattern_type="conformity",
                    affected_users=["user2"],
                    confidence=0.8,
                    evidence=["Rapidly changed position to match majority"],
                ),
            ],
        )

        causal_weights = {"user1": 0.7, "user2": 0.7, "user3": 0.7}
        value_weights = {"user1": 0.7, "user2": 0.7, "user3": 0.7}

        result = aggregation_service.compute_smart_weights(
            session=sample_session,
            causal_weights=causal_weights,
            value_weights=value_weights,
            strategy_detection=strategy_detection,
        )

        # user2 should have lower final weight due to strategic penalty
        user2_weight = next(w for w in result if w.user_id == "user2")
        user1_weight = next(w for w in result if w.user_id == "user1")

        assert user2_weight.final_weight < user1_weight.final_weight
        assert user2_weight.weight_breakdown.strategy_penalty > 0.0


class TestAggregationQuality:
    """Test aggregation quality metrics."""

    def test_compute_aggregation_quality(self, aggregation_service, sample_session):
        """Test computation of aggregation quality metrics."""
        diversity = aggregation_service._measure_diversity(sample_session)

        result = aggregation_service.compute_aggregation_quality(
            sample_session,
            diversity,
        )

        assert 0.0 <= result.collective_intelligence_score <= 1.0
        assert result.diversity_bonus >= 0.0
        assert result.coordination_cost >= 0.0

    def test_diversity_bonus_increases_quality(self, aggregation_service, sample_session):
        """Test that higher diversity increases quality score."""
        # High diversity mock
        high_diversity = 0.9

        result_high = aggregation_service.compute_aggregation_quality(
            sample_session,
            high_diversity,
        )

        # Low diversity mock
        low_diversity = 0.2

        result_low = aggregation_service.compute_aggregation_quality(
            sample_session,
            low_diversity,
        )

        assert result_high.diversity_bonus > result_low.diversity_bonus
        assert result_high.collective_intelligence_score > result_low.collective_intelligence_score
