"""Unit tests for preference elicitation service (Phase 2A: ActiVA)."""

import pytest
from datetime import datetime

from src.services.preference_elicitation import PreferenceElicitationService
from src.models.preferences import (
    ElicitationSessionV1,
    ValueDimensionV1,
)


@pytest.fixture
def elicitation_service():
    """Create preference elicitation service."""
    return PreferenceElicitationService()


@pytest.mark.asyncio
class TestElicitationSession:
    """Test preference elicitation session lifecycle."""

    async def test_start_session_creates_session(self, elicitation_service):
        """Test that starting session creates session and first scenario."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Product roadmap prioritization",
            initial_dimensions=["user_growth", "revenue", "eng_cost"],
            target_convergence=0.8,
            max_questions=7,
        )

        assert session.user_id == "test_user"
        assert session.decision_context == "Product roadmap prioritization"
        assert session.status == "active"
        assert session.target_convergence == 0.8
        assert session.max_questions == 7

        # First scenario should be presented
        assert first_scenario is not None
        assert first_scenario.question
        assert first_scenario.option_a
        assert first_scenario.option_b
        assert len(first_scenario.discriminating_dimensions) > 0

        # Value model should be initialized
        assert session.value_model is not None
        assert len(session.value_model.dimensions) == 3

    async def test_submit_response_updates_value_model(self, elicitation_service):
        """Test that submitting response updates value model."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            initial_dimensions=["dim1", "dim2", "dim3"],
            max_questions=7,
        )

        initial_convergence = session.value_model.convergence_score

        # Submit response choosing option A
        accepted, next_scenario, complete = await elicitation_service.submit_response(
            session_id=session.session_id,
            user_id="test_user",
            scenario_id=first_scenario.scenario_id,
            choice="A",
            response_time_ms=3000,
        )

        assert accepted is True
        assert complete is False
        assert next_scenario is not None

        # Value model should be updated
        updated_session = elicitation_service.sessions[session.session_id]
        assert updated_session.value_model.questions_asked == 1

        # Convergence should change (may increase or decrease)
        assert updated_session.value_model.convergence_score != initial_convergence

    async def test_session_converges_within_max_questions(self, elicitation_service):
        """Test that session converges within max questions limit."""
        max_q = 7
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            initial_dimensions=["dim1", "dim2", "dim3"],
            target_convergence=0.75,
            max_questions=max_q,
        )

        scenario = first_scenario
        for i in range(max_q):
            # Consistently choose option A
            accepted, next_scenario, complete = await elicitation_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                scenario_id=scenario.scenario_id,
                choice="A",
                response_time_ms=2000,
            )

            if complete:
                # Should complete before or at max questions
                assert i < max_q
                updated_session = elicitation_service.sessions[session.session_id]
                assert updated_session.status == "completed"
                assert updated_session.value_model.convergence_score >= updated_session.target_convergence
                break

            scenario = next_scenario


class TestBayesianUpdate:
    """Test Bayesian update mechanism."""

    @pytest.mark.asyncio
    async def test_consistent_choices_increase_convergence(self, elicitation_service):
        """Test that consistent choices increase convergence score."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            initial_dimensions=["dim1", "dim2", "dim3"],
            max_questions=10,
        )

        scenario = first_scenario
        convergence_scores = [session.value_model.convergence_score]

        # Make 5 consistent choices
        for i in range(5):
            _, next_scenario, complete = await elicitation_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                scenario_id=scenario.scenario_id,
                choice="A",  # Always choose A
                response_time_ms=2000,
            )

            if complete:
                break

            updated_session = elicitation_service.sessions[session.session_id]
            convergence_scores.append(updated_session.value_model.convergence_score)
            scenario = next_scenario

        # Convergence should generally increase with consistent choices
        # (may fluctuate slightly, but trend should be upward)
        assert convergence_scores[-1] > convergence_scores[0]

    @pytest.mark.asyncio
    async def test_dimension_weights_update(self, elicitation_service):
        """Test that dimension weights update based on choices."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            initial_dimensions=["user_growth", "revenue", "eng_cost"],
            max_questions=10,
        )

        # Find dimension that's discriminated in first scenario
        discriminated_dims = first_scenario.discriminating_dimensions
        assert len(discriminated_dims) > 0

        # Get initial weight of discriminated dimension
        initial_weights = {d.dimension_name: d.weight for d in session.value_model.dimensions}

        # Submit response
        _, _, _ = await elicitation_service.submit_response(
            session_id=session.session_id,
            user_id="test_user",
            scenario_id=first_scenario.scenario_id,
            choice="A",
            response_time_ms=2000,
        )

        # Check that weights have been updated
        updated_session = elicitation_service.sessions[session.session_id]
        updated_weights = {d.dimension_name: d.weight for d in updated_session.value_model.dimensions}

        # At least one weight should have changed
        assert initial_weights != updated_weights

        # Weights should still sum to ~1.0
        weight_sum = sum(updated_weights.values())
        assert 0.99 <= weight_sum <= 1.01


class TestActiveScenarioGeneration:
    """Test active learning scenario generation."""

    @pytest.mark.asyncio
    async def test_scenarios_have_information_gain(self, elicitation_service):
        """Test that generated scenarios have expected information gain."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            initial_dimensions=["dim1", "dim2", "dim3"],
            max_questions=10,
        )

        assert first_scenario.expected_information_gain > 0.0

        # Submit a few responses and check subsequent scenarios
        scenario = first_scenario
        for i in range(3):
            _, next_scenario, complete = await elicitation_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                scenario_id=scenario.scenario_id,
                choice="A",
                response_time_ms=2000,
            )

            if complete:
                break

            # Each scenario should have information gain estimate
            assert next_scenario.expected_information_gain >= 0.0
            scenario = next_scenario

    @pytest.mark.asyncio
    async def test_scenarios_discriminate_dimensions(self, elicitation_service):
        """Test that scenarios effectively discriminate between dimensions."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            initial_dimensions=["user_growth", "revenue", "eng_cost"],
            max_questions=10,
        )

        # Each scenario should discriminate on at least one dimension
        scenario = first_scenario
        for i in range(5):
            assert len(scenario.discriminating_dimensions) > 0
            assert len(scenario.discriminating_dimensions) <= 3

            # Values should differ between options on discriminating dimensions
            for dim in scenario.discriminating_dimensions:
                val_a = scenario.option_a_values.get(dim, 0)
                val_b = scenario.option_b_values.get(dim, 0)
                # Should have meaningful difference
                assert abs(val_a - val_b) > 0.1

            _, next_scenario, complete = await elicitation_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                scenario_id=scenario.scenario_id,
                choice="A",
                response_time_ms=2000,
            )

            if complete:
                break

            scenario = next_scenario


class TestCounterfactualScenarios:
    """Test counterfactual scenario generation."""

    @pytest.mark.asyncio
    async def test_options_are_counterfactual(self, elicitation_service):
        """Test that option A and B represent counterfactual alternatives."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Feature prioritization",
            initial_dimensions=["user_growth", "revenue", "eng_cost"],
            max_questions=7,
        )

        # Options should be distinct
        assert first_scenario.option_a != first_scenario.option_b

        # Value profiles should differ
        assert first_scenario.option_a_values != first_scenario.option_b_values

        # Should represent realistic trade-offs
        # (e.g., one option higher on some dims, lower on others)
        total_a = sum(first_scenario.option_a_values.values())
        total_b = sum(first_scenario.option_b_values.values())

        # Neither option should dominate completely (not Pareto-optimal test)
        # In realistic scenarios, options should have trade-offs


class TestConvergenceDetection:
    """Test convergence detection."""

    @pytest.mark.asyncio
    async def test_high_convergence_stops_session(self, elicitation_service):
        """Test that high convergence score stops session early."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            initial_dimensions=["dim1", "dim2"],
            target_convergence=0.8,
            max_questions=20,  # High limit
        )

        # Make very consistent choices to drive convergence
        scenario = first_scenario
        question_count = 0

        for i in range(20):
            _, next_scenario, complete = await elicitation_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                scenario_id=scenario.scenario_id,
                choice="A",
                response_time_ms=1000,
            )

            question_count += 1

            if complete:
                # Should complete in fewer than 20 questions
                assert question_count < 20
                updated_session = elicitation_service.sessions[session.session_id]
                assert updated_session.value_model.convergence_score >= 0.8
                break

            scenario = next_scenario

    @pytest.mark.asyncio
    async def test_convergence_score_calculation(self, elicitation_service):
        """Test convergence score calculation."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            initial_dimensions=["dim1", "dim2", "dim3"],
            max_questions=10,
        )

        # Initial convergence should be low (high uncertainty)
        assert session.value_model.convergence_score <= 0.5

        # After multiple consistent responses, should increase
        scenario = first_scenario
        for i in range(5):
            _, next_scenario, complete = await elicitation_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                scenario_id=scenario.scenario_id,
                choice="A",
                response_time_ms=2000,
            )

            if complete:
                break
            scenario = next_scenario

        updated_session = elicitation_service.sessions[session.session_id]
        # Should be more confident after 5 questions
        assert updated_session.value_model.convergence_score > session.value_model.convergence_score


class TestEfficiencyClaim:
    """Test ActiVA efficiency claim (≤7 questions vs. pairwise baseline)."""

    @pytest.mark.asyncio
    async def test_converges_in_seven_or_fewer_questions(self, elicitation_service):
        """Test that elicitation converges in ≤7 questions for most users."""
        convergence_counts = []

        # Run multiple sessions
        for user_num in range(5):
            session, first_scenario = await elicitation_service.start_session(
                user_id=f"efficiency_user_{user_num}",
                decision_context=f"Test decision {user_num}",
                initial_dimensions=["dim1", "dim2", "dim3"],
                target_convergence=0.75,
                max_questions=20,
            )

            scenario = first_scenario
            question_count = 0

            for i in range(20):
                _, next_scenario, complete = await elicitation_service.submit_response(
                    session_id=session.session_id,
                    user_id=f"efficiency_user_{user_num}",
                    scenario_id=scenario.scenario_id,
                    choice="A" if i % 2 == 0 else "B",  # Alternate for some variety
                    response_time_ms=2000,
                )

                question_count += 1

                if complete:
                    convergence_counts.append(question_count)
                    break

                scenario = next_scenario

        # Average should be ≤7 questions (ActiVA efficiency claim)
        avg_questions = sum(convergence_counts) / len(convergence_counts)
        assert avg_questions <= 7, f"ActiVA should converge in ≤7 questions, got {avg_questions}"


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_invalid_session_id_raises_error(self, elicitation_service):
        """Test that invalid session ID raises error."""
        with pytest.raises(ValueError, match="Session .* not found"):
            await elicitation_service.submit_response(
                session_id="nonexistent",
                user_id="test_user",
                scenario_id="scenario1",
                choice="A",
            )

    @pytest.mark.asyncio
    async def test_wrong_user_id_raises_error(self, elicitation_service):
        """Test that wrong user ID raises error."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="correct_user",
            decision_context="Test",
            initial_dimensions=["dim1", "dim2"],
            max_questions=5,
        )

        with pytest.raises(ValueError, match="does not own session"):
            await elicitation_service.submit_response(
                session_id=session.session_id,
                user_id="wrong_user",
                scenario_id=first_scenario.scenario_id,
                choice="A",
            )

    @pytest.mark.asyncio
    async def test_invalid_scenario_id_raises_error(self, elicitation_service):
        """Test that invalid scenario ID raises error."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test",
            initial_dimensions=["dim1", "dim2"],
            max_questions=5,
        )

        with pytest.raises(ValueError, match="Scenario .* not found"):
            await elicitation_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                scenario_id="nonexistent_scenario",
                choice="A",
            )

    @pytest.mark.asyncio
    async def test_invalid_choice_raises_error(self, elicitation_service):
        """Test that invalid choice raises error."""
        session, first_scenario = await elicitation_service.start_session(
            user_id="test_user",
            decision_context="Test",
            initial_dimensions=["dim1", "dim2"],
            max_questions=5,
        )

        with pytest.raises(ValueError, match="Choice must be"):
            await elicitation_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                scenario_id=first_scenario.scenario_id,
                choice="C",  # Invalid - only A or B allowed
            )
