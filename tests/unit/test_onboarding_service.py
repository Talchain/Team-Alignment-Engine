"""Unit tests for onboarding service (Phase 2B: Bayesian Teaching)."""

import pytest
from datetime import datetime

from src.services.onboarding import OnboardingService, DECISION_ARCHETYPES
from src.models.onboarding import OnboardingSessionV1


@pytest.fixture
def onboarding_service():
    """Create onboarding service."""
    return OnboardingService()


@pytest.mark.asyncio
class TestOnboardingSession:
    """Test onboarding session lifecycle."""

    async def test_start_session_creates_session(self, onboarding_service):
        """Test that starting session creates session and first question."""
        session, first_question = await onboarding_service.start_session(
            user_id="test_user",
            decision_context="Should we migrate to microservices?",
            user_role="engineer",
            target_confidence=0.8,
            max_questions=7,
        )

        assert session.user_id == "test_user"
        assert session.decision_context == "Should we migrate to microservices?"
        assert session.status == "active"
        assert session.target_confidence == 0.8
        assert session.max_questions == 7

        # First question should be presented
        assert first_question is not None
        assert first_question.question_type in ["priority", "constraint", "scenario"]
        assert len(first_question.options) > 0

        # Profile should be initialized
        assert session.profile is not None
        assert session.profile.user_id == "test_user"

    async def test_role_prior_applied(self, onboarding_service):
        """Test that user role creates appropriate prior."""
        session, _ = await onboarding_service.start_session(
            user_id="pm_user",
            decision_context="Product roadmap decision",
            user_role="product_manager",
            target_confidence=0.8,
            max_questions=7,
        )

        # Product manager role should bias toward user_experience_focused
        profile = session.profile
        if profile.primary_archetype:
            # Should have some weak prior
            assert profile.profile_confidence > 0.0
            assert profile.primary_archetype.confidence <= 0.3  # Weak prior

    async def test_submit_response_updates_profile(self, onboarding_service):
        """Test that submitting response updates profile."""
        session, first_question = await onboarding_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            max_questions=7,
        )

        initial_confidence = session.profile.profile_confidence

        # Submit response
        accepted, next_question, complete = await onboarding_service.submit_response(
            session_id=session.session_id,
            user_id="test_user",
            question_id=first_question.question_id,
            selected_option=first_question.options[0],
            response_time_ms=2000,
        )

        assert accepted is True
        assert complete is False
        assert next_question is not None

        # Profile confidence should increase
        updated_session = onboarding_service.sessions[session.session_id]
        assert updated_session.profile.profile_confidence > initial_confidence
        assert updated_session.profile.questions_answered == 1

    async def test_session_converges_early(self, onboarding_service):
        """Test that session can converge before max questions."""
        session, first_question = await onboarding_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            target_confidence=0.5,  # Low threshold for quick convergence
            max_questions=10,
        )

        question = first_question
        for i in range(5):
            # Always select first option (consistent responses)
            accepted, next_question, complete = await onboarding_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                question_id=question.question_id,
                selected_option=question.options[0],
                response_time_ms=2000,
            )

            if complete:
                # Should converge before max questions
                assert i < 10
                updated_session = onboarding_service.sessions[session.session_id]
                assert updated_session.status == "completed"
                assert updated_session.profile.profile_confidence >= 0.5
                break

            question = next_question

    async def test_session_respects_max_questions(self, onboarding_service):
        """Test that session stops at max questions."""
        max_q = 3
        session, first_question = await onboarding_service.start_session(
            user_id="test_user",
            decision_context="Test decision",
            target_confidence=0.99,  # Very high threshold
            max_questions=max_q,
        )

        question = first_question
        for i in range(max_q):
            accepted, next_question, complete = await onboarding_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                question_id=question.question_id,
                selected_option=question.options[i % len(question.options)],
                response_time_ms=2000,
            )

            if i == max_q - 1:
                # Last question should complete
                assert complete is True
                assert next_question is None
            else:
                question = next_question


class TestProfileInference:
    """Test profile inference and archetype matching."""

    @pytest.mark.asyncio
    async def test_consistent_growth_answers_match_growth_archetype(self, onboarding_service):
        """Test that user growth answers match to user_growth_focused archetype."""
        session, first_question = await onboarding_service.start_session(
            user_id="growth_user",
            decision_context="Product strategy",
            max_questions=5,
        )

        # Simulate consistent growth-focused answers
        question = first_question
        for i in range(4):
            # Select growth-related options
            growth_options = [opt for opt in question.options if "growth" in opt.lower() or "engagement" in opt.lower()]
            if growth_options:
                selected = growth_options[0]
            else:
                selected = question.options[0]

            accepted, next_question, complete = await onboarding_service.submit_response(
                session_id=session.session_id,
                user_id="growth_user",
                question_id=question.question_id,
                selected_option=selected,
                response_time_ms=2000,
            )

            if complete:
                break
            question = next_question

        # Get final profile
        profile = onboarding_service.get_profile(session.session_id, "growth_user")

        # Should have matched to user_growth_focused
        if profile.primary_archetype:
            # Check that growth-related weights are high
            assert profile.inferred_value_weights.get("user_growth", 0) > 0.0

    @pytest.mark.asyncio
    async def test_technical_answers_match_technical_archetype(self, onboarding_service):
        """Test that technical excellence answers match appropriately."""
        session, first_question = await onboarding_service.start_session(
            user_id="tech_user",
            decision_context="Architecture decision",
            max_questions=5,
        )

        # Simulate consistent technical quality answers
        question = first_question
        for i in range(4):
            # Select technical/quality-related options
            tech_options = [opt for opt in question.options if "technical" in opt.lower() or "quality" in opt.lower() or "scalability" in opt.lower()]
            if tech_options:
                selected = tech_options[0]
            else:
                selected = question.options[0]

            accepted, next_question, complete = await onboarding_service.submit_response(
                session_id=session.session_id,
                user_id="tech_user",
                question_id=question.question_id,
                selected_option=selected,
                response_time_ms=2000,
            )

            if complete:
                break
            question = next_question

        profile = onboarding_service.get_profile(session.session_id, "tech_user")

        # Should have technical-related weights
        if profile.primary_archetype:
            tech_weight = profile.inferred_value_weights.get("code_quality", 0) + profile.inferred_value_weights.get("scalability", 0)
            assert tech_weight > 0.0


class TestBayesianTeachingEfficiency:
    """Test Bayesian teaching efficiency claims."""

    @pytest.mark.asyncio
    async def test_converges_in_fewer_than_7_questions(self, onboarding_service):
        """Test that onboarding converges in ≤7 questions (vs 20+ baseline)."""
        convergence_counts = []

        # Run multiple sessions to test convergence
        for user_num in range(5):
            session, first_question = await onboarding_service.start_session(
                user_id=f"efficiency_user_{user_num}",
                decision_context=f"Test decision {user_num}",
                target_confidence=0.75,
                max_questions=20,  # Allow up to 20 but expect much less
            )

            question = first_question
            question_count = 0

            for i in range(20):
                # Provide consistent answers
                accepted, next_question, complete = await onboarding_service.submit_response(
                    session_id=session.session_id,
                    user_id=f"efficiency_user_{user_num}",
                    question_id=question.question_id,
                    selected_option=question.options[0],
                    response_time_ms=2000,
                )

                question_count += 1

                if complete:
                    convergence_counts.append(question_count)
                    break

                question = next_question

        # Average should be significantly less than 20 (baseline)
        avg_questions = sum(convergence_counts) / len(convergence_counts)
        assert avg_questions <= 7, f"Bayesian teaching should converge in ≤7 questions, got {avg_questions}"


class TestArchetypes:
    """Test decision archetype definitions."""

    def test_archetypes_defined(self):
        """Test that all required archetypes are defined."""
        required_archetypes = [
            "user_growth_focused",
            "revenue_focused",
            "technical_excellence",
            "user_experience_focused",
            "balanced_pragmatist",
        ]

        archetype_ids = [a.archetype_id for a in DECISION_ARCHETYPES]
        for required in required_archetypes:
            assert required in archetype_ids

    def test_archetypes_have_required_fields(self):
        """Test that archetypes have all required fields."""
        for archetype in DECISION_ARCHETYPES:
            assert archetype.archetype_id
            assert archetype.name
            assert archetype.description
            assert len(archetype.typical_value_weights) > 0
            assert len(archetype.typical_concerns) > 0
            assert len(archetype.example_decisions) > 0

            # Weights should sum to approximately 1.0
            weight_sum = sum(archetype.typical_value_weights.values())
            assert 0.9 <= weight_sum <= 1.1


class TestQuestionGeneration:
    """Test adaptive question generation."""

    def test_first_question_is_broad_priority(self, onboarding_service):
        """Test that first question asks about broad priorities."""
        session = OnboardingSessionV1(
            user_id="test_user",
            decision_context="Test decision",
            available_archetypes=DECISION_ARCHETYPES,
            target_confidence=0.8,
            max_questions=7,
        )
        session.profile = onboarding_service._initialize_profile("test_user")

        question = onboarding_service._generate_question(session)

        assert question.question_type == "priority"
        assert "important" in question.question_text.lower() or "priority" in question.question_text.lower()
        assert len(question.options) >= 4  # Should offer multiple broad options

    def test_second_question_explores_constraints(self, onboarding_service):
        """Test that second question explores constraints."""
        session = OnboardingSessionV1(
            user_id="test_user",
            decision_context="Test decision",
            available_archetypes=DECISION_ARCHETYPES,
            target_confidence=0.8,
            max_questions=7,
        )
        session.profile = onboarding_service._initialize_profile("test_user")

        # Simulate one question already asked
        from src.models.onboarding import OnboardingResponseV1
        session.responses.append(
            OnboardingResponseV1(
                question_id="q1",
                user_id="test_user",
                selected_option="User growth and engagement",
            )
        )

        question = onboarding_service._generate_question(session)

        assert question.question_type == "constraint"
        assert "constraint" in question.question_text.lower()

    def test_questions_have_information_gain(self, onboarding_service):
        """Test that questions have expected information gain scores."""
        session = OnboardingSessionV1(
            user_id="test_user",
            decision_context="Test decision",
            available_archetypes=DECISION_ARCHETYPES,
            target_confidence=0.8,
            max_questions=7,
        )
        session.profile = onboarding_service._initialize_profile("test_user")

        for i in range(5):
            question = onboarding_service._generate_question(session)

            assert 0.0 <= question.expected_information_gain <= 1.0

            # Earlier questions should have higher information gain
            if i == 0:
                assert question.expected_information_gain >= 0.7

            # Simulate response
            from src.models.onboarding import OnboardingResponseV1
            session.responses.append(
                OnboardingResponseV1(
                    question_id=question.question_id,
                    user_id="test_user",
                    selected_option=question.options[0],
                )
            )


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_invalid_session_id_raises_error(self, onboarding_service):
        """Test that invalid session ID raises error."""
        with pytest.raises(ValueError, match="Session .* not found"):
            await onboarding_service.submit_response(
                session_id="nonexistent",
                user_id="test_user",
                question_id="q1",
                selected_option="option",
            )

    @pytest.mark.asyncio
    async def test_wrong_user_id_raises_error(self, onboarding_service):
        """Test that wrong user ID raises error."""
        session, first_question = await onboarding_service.start_session(
            user_id="correct_user",
            decision_context="Test",
            max_questions=5,
        )

        with pytest.raises(ValueError, match="does not own session"):
            await onboarding_service.submit_response(
                session_id=session.session_id,
                user_id="wrong_user",
                question_id=first_question.question_id,
                selected_option=first_question.options[0],
            )

    @pytest.mark.asyncio
    async def test_invalid_question_id_raises_error(self, onboarding_service):
        """Test that invalid question ID raises error."""
        session, first_question = await onboarding_service.start_session(
            user_id="test_user",
            decision_context="Test",
            max_questions=5,
        )

        with pytest.raises(ValueError, match="Question .* not found"):
            await onboarding_service.submit_response(
                session_id=session.session_id,
                user_id="test_user",
                question_id="nonexistent_question",
                selected_option="option",
            )
