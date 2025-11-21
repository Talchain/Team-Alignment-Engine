"""Unit tests for Phase C services."""

import pytest
from uuid import uuid4
from datetime import datetime

from src.services.ai_option_generator import AIOptionGenerator
from src.services.option_synthesizer import OptionSynthesizer
from src.services.option_tuner import OptionTuner
from src.services.assumption_testing_advisor import AssumptionTestingAdvisor
from src.services.decision_retrospective import DecisionRetrospectiveService
from src.services.session_reopener import SessionReopener
from src.models.option import ProposedOption
from src.models.concern import MinorityConcern
from src.models.validation import AssumptionStrength
from src.models.enums import (
    SessionStatus,
    AlignmentMode,
    DecisionType,
    EvidenceLevel,
    ImpactLevel,
)
from src.models.session import AlignmentSession
from src.models.decision import DecisionBrief
from src.models.phase_c_models import (
    DecisionRetrospective,
    AssumptionValidationRecord,
    OutcomeComparison,
)
from tests.fixtures.mock_clients import MockCEEClient


@pytest.mark.asyncio
class TestAIOptionGenerator:
    """Tests for AI Option Generator service."""

    async def test_generate_options_creative_synthesis(self):
        """Test AI option generation in creative synthesis mode."""
        cee = MockCEEClient()
        generator = AIOptionGenerator(cee)

        session_id = uuid4()
        profiles = [
            {"profile_id": str(uuid4()), "goal_weights": {"revenue": 0.8}}
        ]
        decision_context = "Pricing decision for new feature"
        disagreement_map = {"tension": "cost_vs_value"}

        options = await generator.generate_options(
            session_id=session_id,
            profiles=profiles,
            decision_context=decision_context,
            disagreement_map=disagreement_map,
            generation_mode="creative_synthesis",
            num_options=3,
        )

        assert len(options) == 3
        assert all(isinstance(opt, ProposedOption) for opt in options)
        assert all(opt.ai_generation_metadata is not None for opt in options)
        assert all(opt.proposed_by == "ai_assistant" for opt in options)

    async def test_generate_options_invalid_mode(self):
        """Test that invalid generation mode raises ValueError."""
        cee = MockCEEClient()
        generator = AIOptionGenerator(cee)

        with pytest.raises(ValueError, match="Invalid generation_mode"):
            await generator.generate_options(
                session_id=uuid4(),
                profiles=[],
                decision_context="Test",
                disagreement_map={},
                generation_mode="invalid_mode",
            )


@pytest.mark.asyncio
class TestOptionSynthesizer:
    """Tests for Option Synthesizer service."""

    async def test_synthesize_options(self):
        """Test option synthesis from multiple sources."""
        cee = MockCEEClient()
        synthesizer = OptionSynthesizer(cee)

        session_id = uuid4()
        source_options = [
            ProposedOption(
                option_id=uuid4(),
                session_id=session_id,
                proposed_by="user1",
                round_number=1,
                title="Option A",
                description="First option",
                expected_outcome="Outcome A",
                causal_rationale="Rationale A",
                addresses_goals=["revenue"],
                trade_offs=[],
                key_assumptions=[],
            ),
            ProposedOption(
                option_id=uuid4(),
                session_id=session_id,
                proposed_by="user2",
                round_number=1,
                title="Option B",
                description="Second option",
                expected_outcome="Outcome B",
                causal_rationale="Rationale B",
                addresses_goals=["retention"],
                trade_offs=[],
                key_assumptions=[],
            ),
        ]

        synthesized = await synthesizer.synthesize_options(
            session_id=session_id,
            source_options=source_options,
            profiles=[],
            decision_context="Test context",
            synthesis_goal="maximize consensus",
        )

        assert isinstance(synthesized, ProposedOption)
        assert synthesized.synthesis_metadata is not None
        assert len(synthesized.synthesis_metadata.source_option_ids) == 2

    async def test_calculate_compatibility_score(self):
        """Test compatibility score calculation."""
        cee = MockCEEClient()
        synthesizer = OptionSynthesizer(cee)

        session_id = uuid4()
        option_a = ProposedOption(
            option_id=uuid4(),
            session_id=session_id,
            proposed_by="user1",
            round_number=1,
            title="Option A",
            description="Test",
            expected_outcome="Test",
            causal_rationale="Test",
            addresses_goals=["revenue", "retention"],
            trade_offs=[{"dimension": "cost"}],
            key_assumptions=[],
        )
        option_b = ProposedOption(
            option_id=uuid4(),
            session_id=session_id,
            proposed_by="user2",
            round_number=1,
            title="Option B",
            description="Test",
            expected_outcome="Test",
            causal_rationale="Test",
            addresses_goals=["revenue"],
            trade_offs=[{"dimension": "timeline"}],
            key_assumptions=[],
        )

        score = await synthesizer.calculate_compatibility_score(option_a, option_b)

        assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
class TestOptionTuner:
    """Tests for Option Tuner service."""

    async def test_tune_option(self):
        """Test option tuning for minority concern."""
        cee = MockCEEClient()
        tuner = OptionTuner(cee)

        session_id = uuid4()
        option = ProposedOption(
            option_id=uuid4(),
            session_id=session_id,
            proposed_by="user1",
            round_number=1,
            title="Original Option",
            description="Original description",
            expected_outcome="Original outcome",
            causal_rationale="Original rationale",
            addresses_goals=["revenue"],
            trade_offs=[],
            key_assumptions=[],
        )

        concern = MinorityConcern(
            concern_id=uuid4(),
            option_id=option.option_id,
            raised_by=uuid4(),
            concern_text="Timeline is too aggressive",
            concern_type="timeline",
        )

        tuned = await tuner.tune_option(
            session_id=session_id,
            option=option,
            concern=concern,
            profiles=[],
            decision_context="Test context",
            preserve_elements=["budget"],
        )

        assert isinstance(tuned, ProposedOption)
        assert tuned.tuning_metadata is not None
        assert tuned.tuning_metadata.concern_addressed == concern.concern_id


@pytest.mark.asyncio
class TestAssumptionTestingAdvisor:
    """Tests for Assumption Testing Advisor service."""

    async def test_prioritize_assumptions(self):
        """Test assumption prioritization logic."""
        cee = MockCEEClient()
        advisor = AssumptionTestingAdvisor(cee)

        assumptions = [
            AssumptionStrength(
                assumption_id="low_priority",
                assumption_text="Low impact, strong evidence",
                evidence_strength=EvidenceLevel.STRONG,
                impact_if_wrong=ImpactLevel.LOW,
                source="test",
            ),
            AssumptionStrength(
                assumption_id="high_priority",
                assumption_text="High impact, weak evidence",
                evidence_strength=EvidenceLevel.WEAK,
                impact_if_wrong=ImpactLevel.CRITICAL,
                source="test",
            ),
            AssumptionStrength(
                assumption_id="medium_priority",
                assumption_text="Medium impact, medium evidence",
                evidence_strength=EvidenceLevel.MEDIUM,
                impact_if_wrong=ImpactLevel.MEDIUM,
                source="test",
            ),
        ]

        prioritized = await advisor.prioritize_assumptions(assumptions)

        # High priority should be first
        assert prioritized[0].assumption_id == "high_priority"
        # Low priority should be last
        assert prioritized[-1].assumption_id == "low_priority"


@pytest.mark.asyncio
class TestDecisionRetrospective:
    """Tests for Decision Retrospective service."""

    async def test_create_retrospective(self):
        """Test retrospective creation."""
        cee = MockCEEClient()
        service = DecisionRetrospectiveService(cee)

        session_id = uuid4()
        brief = DecisionBrief(
            brief_id=uuid4(),
            session_id=session_id,
            chosen_option={
                "title": "Chosen Option",
                "description": "Test option",
            },
            decision_rationale="Best fit",
            stakeholder_support=[],
            consensus_strength=0.8,
            validated_outcomes={
                "revenue_growth": {"p50": 0.15, "p10": 0.10, "p90": 0.20}
            },
            accepted_assumptions=[
                {"assumption_id": "a1", "assumption_text": "Market stays stable"}
            ],
            monitored_risks=[],
            minority_concerns_raised=[],
            minority_concerns_addressed=[],
            review_date=datetime.utcnow(),
            success_criteria=[],
            monitoring_plan=[],
            participants=[],
        )

        actual_outcomes = {"revenue_growth": 0.12}
        validations = [
            AssumptionValidationRecord(
                assumption_id="a1",
                session_id=session_id,
                validation_method="a_b_test",
                validation_result="confirmed",
                validation_notes="Test passed",
                validated_at=datetime.utcnow(),
                validated_by=uuid4(),
            )
        ]

        retrospective = await service.create_retrospective(
            session_id=session_id,
            brief=brief,
            actual_outcomes=actual_outcomes,
            assumption_validations=validations,
            decision_context="Test decision",
            recorded_by=uuid4(),
        )

        assert isinstance(retrospective, DecisionRetrospective)
        assert retrospective.session_id == session_id
        assert len(retrospective.lessons_learned) > 0


@pytest.mark.asyncio
class TestSessionReopener:
    """Tests for Session Reopener service."""

    async def test_should_reopen_session_low_accuracy(self):
        """Test reopen assessment when accuracy is low."""
        reopener = SessionReopener()

        retrospective = DecisionRetrospective(
            retrospective_id=uuid4(),
            session_id=uuid4(),
            brief_id=uuid4(),
            actual_outcomes={},
            outcome_comparison={
                "overall_accuracy": 0.5,  # Below threshold
                "comparisons": [],
            },
            assumption_results=[],
            assumption_analysis={
                "num_validated": 5,
                "num_rejected": 1,
            },
            narrative="Test narrative",
            lessons_learned=[],
        )

        assessment = await reopener.should_reopen_session(
            retrospective, threshold=0.7
        )

        assert assessment["should_reopen"] is True
        assert assessment["priority"] == "high"

    async def test_reopen_session(self):
        """Test session reopening."""
        reopener = SessionReopener()

        original_session = AlignmentSession(
            session_id=uuid4(),
            team_id=uuid4(),
            decision_topic="Original Decision",
            decision_context="Original context",
            decision_type=DecisionType.PRICING,
            alignment_mode=AlignmentMode.EVIDENCE_BACKED,
            status=SessionStatus.DECIDED,
            stakeholders=[],
            created_by=uuid4(),
            chain_depth=0,
        )

        retrospective = DecisionRetrospective(
            retrospective_id=uuid4(),
            session_id=original_session.session_id,
            brief_id=uuid4(),
            actual_outcomes={},
            outcome_comparison={"overall_accuracy": 0.5},
            assumption_results=[],
            assumption_analysis={},
            narrative="Test",
            lessons_learned=[],
        )

        new_session = await reopener.reopen_session(
            original_session=original_session,
            retrospective=retrospective,
            reopen_rationale="Assumptions failed",
            created_by=uuid4(),
        )

        assert new_session.parent_session_id == original_session.session_id
        assert new_session.chain_depth == 1
        assert new_session.status == SessionStatus.COLLECTING
