"""Onboarding service (Phase 2B: Bayesian Teaching).

Efficient team onboarding using decision archetypes and adaptive questioning.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from src.models.onboarding import (
    OnboardingSessionV1,
    OnboardingQuestionV1,
    OnboardingResponseV1,
    OnboardingProfileV1,
    DecisionArchetypeV1,
    ArchetypeMatchV1,
)

logger = logging.getLogger(__name__)


# Predefined decision archetypes
DECISION_ARCHETYPES = [
    DecisionArchetypeV1(
        archetype_id="user_growth_focused",
        name="User Growth Focused",
        description="Prioritizes user acquisition and engagement over short-term revenue",
        typical_value_weights={
            "user_growth": 0.5,
            "user_engagement": 0.3,
            "revenue": 0.1,
            "eng_cost": 0.1,
        },
        typical_concerns=["Churn rate", "Activation funnel", "Viral coefficient"],
        typical_constraints=["Must not harm user experience", "Sustainable growth rate"],
        example_decisions=[
            "Invest in free tier expansion",
            "Prioritize viral features",
        ],
    ),
    DecisionArchetypeV1(
        archetype_id="revenue_focused",
        name="Revenue Focused",
        description="Prioritizes monetization and profitability",
        typical_value_weights={
            "revenue": 0.5,
            "profit_margin": 0.3,
            "user_growth": 0.1,
            "eng_cost": 0.1,
        },
        typical_concerns=["ARPU", "Conversion rate", "LTV/CAC ratio"],
        typical_constraints=["Positive ROI required", "Payback period < 12 months"],
        example_decisions=[
            "Focus on premium tier features",
            "Optimize pricing strategy",
        ],
    ),
    DecisionArchetypeV1(
        archetype_id="technical_excellence",
        name="Technical Excellence",
        description="Prioritizes engineering quality, scalability, and tech debt reduction",
        typical_value_weights={
            "code_quality": 0.4,
            "scalability": 0.3,
            "eng_velocity": 0.2,
            "user_experience": 0.1,
        },
        typical_concerns=["Tech debt", "System reliability", "Developer productivity"],
        typical_constraints=["Must improve code quality", "No shortcuts"],
        example_decisions=[
            "Invest in refactoring",
            "Build proper testing infrastructure",
        ],
    ),
    DecisionArchetypeV1(
        archetype_id="user_experience_focused",
        name="User Experience Focused",
        description="Prioritizes user satisfaction and product delight",
        typical_value_weights={
            "user_satisfaction": 0.5,
            "usability": 0.3,
            "user_engagement": 0.1,
            "eng_cost": 0.1,
        },
        typical_concerns=["NPS", "User feedback", "Usability issues"],
        typical_constraints=["Must improve user satisfaction", "Accessible to all users"],
        example_decisions=[
            "Invest in UX research",
            "Prioritize polish over features",
        ],
    ),
    DecisionArchetypeV1(
        archetype_id="balanced_pragmatist",
        name="Balanced Pragmatist",
        description="Balances multiple concerns with practical trade-offs",
        typical_value_weights={
            "user_growth": 0.25,
            "revenue": 0.25,
            "user_satisfaction": 0.25,
            "eng_cost": 0.25,
        },
        typical_concerns=["Sustainable growth", "Team capacity", "Market dynamics"],
        typical_constraints=["Must be feasible with current resources", "Low risk preferred"],
        example_decisions=[
            "Iterative approach with checkpoints",
            "Validate assumptions before scaling",
        ],
    ),
]


class OnboardingService:
    """Service for onboarding users with decision archetypes."""

    def __init__(self):
        """Initialize onboarding service."""
        self.archetypes = DECISION_ARCHETYPES

        # In-memory storage (in production, use database)
        self.sessions: Dict[str, OnboardingSessionV1] = {}

    async def start_session(
        self,
        user_id: str,
        decision_context: str,
        user_role: Optional[str] = None,
        target_confidence: float = 0.8,
        max_questions: int = 7,
    ) -> Tuple[OnboardingSessionV1, OnboardingQuestionV1]:
        """Start new onboarding session.

        Args:
            user_id: User ID
            decision_context: Decision context
            user_role: User's role (for initial archetype matching)
            target_confidence: Target confidence score
            max_questions: Maximum questions to ask

        Returns:
            Tuple of (session, first_question)
        """
        logger.info(
            f"Starting onboarding for user {user_id}",
            extra={"decision_context": decision_context[:100], "user_role": user_role},
        )

        # Create session
        session = OnboardingSessionV1(
            user_id=user_id,
            decision_context=decision_context,
            available_archetypes=self.archetypes,
            target_confidence=target_confidence,
            max_questions=max_questions,
        )

        # Initialize profile with uniform prior
        session.profile = self._initialize_profile(user_id)

        # Apply role-based prior if provided
        if user_role:
            self._apply_role_prior(session.profile, user_role)

        # Generate first question
        first_question = self._generate_question(session)
        session.questions_presented.append(first_question)

        # Store session
        self.sessions[session.session_id] = session

        logger.info(f"Session {session.session_id} started with first question")

        return session, first_question

    async def submit_response(
        self,
        session_id: str,
        user_id: str,
        question_id: str,
        selected_option: str,
        response_time_ms: Optional[int] = None,
    ) -> Tuple[bool, Optional[OnboardingQuestionV1], bool]:
        """Submit response to a question.

        Args:
            session_id: Session ID
            user_id: User ID
            question_id: Question ID
            selected_option: Selected option
            response_time_ms: Response time

        Returns:
            Tuple of (accepted, next_question, session_complete)
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.user_id != user_id:
            raise ValueError(f"User {user_id} does not own session {session_id}")

        # Find question
        question = next(
            (q for q in session.questions_presented if q.question_id == question_id),
            None,
        )
        if not question:
            raise ValueError(f"Question {question_id} not found")

        # Create response
        response = OnboardingResponseV1(
            question_id=question_id,
            user_id=user_id,
            selected_option=selected_option,
            response_time_ms=response_time_ms,
        )
        session.responses.append(response)

        # Update profile using Bayesian update
        self._update_profile(session, question, response)

        # Check convergence
        converged = session.profile.profile_confidence >= session.target_confidence
        max_reached = len(session.responses) >= session.max_questions

        if converged or max_reached:
            # Session complete
            session.status = "completed"
            session.completed_at = datetime.utcnow().isoformat() + "Z"

            # Finalize profile with archetype matching
            self._finalize_profile(session.profile)

            logger.info(
                f"Session {session_id} completed",
                extra={
                    "converged": converged,
                    "questions_asked": len(session.responses),
                    "confidence": session.profile.profile_confidence,
                },
            )

            return True, None, True

        # Generate next question using Bayesian teaching
        next_question = self._generate_question(session)
        session.questions_presented.append(next_question)

        logger.info(
            f"Response submitted for question {question_id}",
            extra={
                "questions_asked": len(session.responses),
                "confidence": session.profile.profile_confidence,
            },
        )

        return True, next_question, False

    def get_profile(
        self,
        session_id: str,
        user_id: str,
    ) -> OnboardingProfileV1:
        """Get current profile for a session.

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            Current profile
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.user_id != user_id:
            raise ValueError(f"User {user_id} does not own session {session_id}")

        return session.profile

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================

    def _initialize_profile(
        self,
        user_id: str,
    ) -> OnboardingProfileV1:
        """Initialize profile with uniform prior.

        Args:
            user_id: User ID

        Returns:
            Initial profile
        """
        return OnboardingProfileV1(
            user_id=user_id,
            primary_archetype=None,
            profile_confidence=0.0,
            questions_answered=0,
        )

    def _apply_role_prior(
        self,
        profile: OnboardingProfileV1,
        user_role: str,
    ) -> None:
        """Apply role-based prior to profile.

        Args:
            profile: Profile to update
            user_role: User's role
        """
        # Simple role-to-archetype mapping
        role_priors = {
            "product_manager": "user_experience_focused",
            "engineer": "technical_excellence",
            "growth": "user_growth_focused",
            "finance": "revenue_focused",
            "executive": "balanced_pragmatist",
        }

        role_lower = user_role.lower()
        for role_key, archetype_id in role_priors.items():
            if role_key in role_lower:
                # Weak prior (confidence 0.3)
                archetype = next(
                    (a for a in self.archetypes if a.archetype_id == archetype_id),
                    None,
                )
                if archetype:
                    profile.primary_archetype = ArchetypeMatchV1(
                        archetype=archetype,
                        confidence=0.3,
                        evidence=[f"Role: {user_role}"],
                    )
                    profile.profile_confidence = 0.3
                break

    def _generate_question(
        self,
        session: OnboardingSessionV1,
    ) -> OnboardingQuestionV1:
        """Generate next question using Bayesian teaching.

        Args:
            session: Onboarding session

        Returns:
            Next question
        """
        questions_asked = len(session.responses)

        # Question templates
        if questions_asked == 0:
            # First question: broad priority
            return OnboardingQuestionV1(
                question_text="What's most important for this decision?",
                question_type="priority",
                options=[
                    "User growth and engagement",
                    "Revenue and profitability",
                    "Technical quality and scalability",
                    "User experience and satisfaction",
                    "Balanced trade-offs",
                ],
                expected_information_gain=0.8,
                discriminates_archetypes=[a.archetype_id for a in self.archetypes],
            )

        elif questions_asked == 1:
            # Second question: constraint type
            return OnboardingQuestionV1(
                question_text="What's your biggest constraint?",
                question_type="constraint",
                options=[
                    "Limited engineering capacity",
                    "Tight budget / cost concerns",
                    "Market timing / competitive pressure",
                    "User expectations / quality standards",
                    "No major constraints",
                ],
                expected_information_gain=0.7,
                discriminates_archetypes=[a.archetype_id for a in self.archetypes],
            )

        elif questions_asked == 2:
            # Third question: scenario-based
            return OnboardingQuestionV1(
                question_text="Feature A grows users 20% but delays revenue features. Feature B increases revenue 15% but slower user growth. Which do you choose?",
                question_type="scenario",
                options=[
                    "Feature A (prioritize user growth)",
                    "Feature B (prioritize revenue)",
                    "Split resources and do both partially",
                    "Need more data to decide",
                ],
                expected_information_gain=0.6,
                discriminates_archetypes=["user_growth_focused", "revenue_focused", "balanced_pragmatist"],
            )

        else:
            # Adaptive questions based on current uncertainty
            # For simplicity, ask about specific concerns
            return OnboardingQuestionV1(
                question_text=f"How concerned are you about technical debt in this decision? (Question {questions_asked + 1})",
                question_type="priority",
                options=[
                    "Very concerned - it's a top priority",
                    "Somewhat concerned - should address it",
                    "Slightly concerned - can defer",
                    "Not concerned - other things more important",
                ],
                expected_information_gain=0.5,
                discriminates_archetypes=["technical_excellence"],
            )

    def _update_profile(
        self,
        session: OnboardingSessionV1,
        question: OnboardingQuestionV1,
        response: OnboardingResponseV1,
    ) -> None:
        """Update profile using Bayesian update.

        Args:
            session: Onboarding session
            question: Question user responded to
            response: User's response
        """
        profile = session.profile

        # Simplified Bayesian update based on response
        # In full implementation, would use proper Bayesian network

        selected = response.selected_option.lower()

        # Update inferred values based on response
        if "user growth" in selected or "engagement" in selected:
            profile.inferred_value_weights["user_growth"] = profile.inferred_value_weights.get("user_growth", 0.2) + 0.3
            profile.inferred_value_weights["user_engagement"] = profile.inferred_value_weights.get("user_engagement", 0.1) + 0.2

        if "revenue" in selected or "profitability" in selected:
            profile.inferred_value_weights["revenue"] = profile.inferred_value_weights.get("revenue", 0.2) + 0.3
            profile.inferred_value_weights["profit_margin"] = profile.inferred_value_weights.get("profit_margin", 0.1) + 0.2

        if "technical" in selected or "quality" in selected or "scalability" in selected:
            profile.inferred_value_weights["code_quality"] = profile.inferred_value_weights.get("code_quality", 0.2) + 0.3
            profile.inferred_value_weights["scalability"] = profile.inferred_value_weights.get("scalability", 0.1) + 0.2

        if "experience" in selected or "satisfaction" in selected:
            profile.inferred_value_weights["user_satisfaction"] = profile.inferred_value_weights.get("user_satisfaction", 0.2) + 0.3
            profile.inferred_value_weights["usability"] = profile.inferred_value_weights.get("usability", 0.1) + 0.2

        if "balanced" in selected or "both" in selected:
            # Balanced approach
            for key in ["user_growth", "revenue", "user_satisfaction", "eng_cost"]:
                profile.inferred_value_weights[key] = profile.inferred_value_weights.get(key, 0.15) + 0.15

        # Normalize weights
        total = sum(profile.inferred_value_weights.values())
        if total > 0:
            for key in profile.inferred_value_weights:
                profile.inferred_value_weights[key] /= total

        # Update confidence (increases with each question)
        profile.questions_answered += 1
        profile.profile_confidence = min(
            1.0,
            profile.profile_confidence + 0.15 * question.expected_information_gain,
        )

    def _finalize_profile(
        self,
        profile: OnboardingProfileV1,
    ) -> None:
        """Finalize profile by matching to archetypes.

        Args:
            profile: Profile to finalize
        """
        # Find best archetype match based on inferred weights
        best_match = None
        best_score = 0.0

        for archetype in self.archetypes:
            # Compute similarity between inferred weights and archetype weights
            score = 0.0
            count = 0

            for dim, weight in archetype.typical_value_weights.items():
                if dim in profile.inferred_value_weights:
                    # Cosine similarity component
                    score += weight * profile.inferred_value_weights[dim]
                    count += 1

            if count > 0:
                score /= count

            if score > best_score:
                best_score = score
                best_match = archetype

        if best_match and best_score > 0.3:
            profile.primary_archetype = ArchetypeMatchV1(
                archetype=best_match,
                confidence=min(1.0, best_score * 1.5),
                evidence=[
                    f"Inferred weights match {best_match.name} pattern",
                    f"Similarity score: {best_score:.2f}",
                ],
            )

            # Copy archetype's typical concerns and constraints
            profile.inferred_concerns = best_match.typical_concerns.copy()
            profile.inferred_constraints = best_match.typical_constraints.copy()

        logger.info(
            f"Finalized profile for {profile.user_id}",
            extra={
                "archetype": best_match.name if best_match else "none",
                "confidence": profile.profile_confidence,
            },
        )
