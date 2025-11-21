"""Session Reopener service (Phase C: C6).

Enables multi-round deliberation when assumptions fail.
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime

from src.models.session import AlignmentSession
from src.models.decision import DecisionBrief
from src.models.phase_c_models import (
    DecisionRetrospective,
    SessionChainLink,
    AssumptionValidationRecord,
)
from src.models.enums import SessionStatus, AlignmentMode

logger = logging.getLogger(__name__)


class SessionReopener:
    """Service for reopening sessions for multi-round deliberation."""

    async def should_reopen_session(
        self,
        retrospective: DecisionRetrospective,
        threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Determine if a session should be reopened based on retrospective.

        Reopen criteria:
        1. Low outcome accuracy (< threshold)
        2. Critical assumptions rejected
        3. Major shifts in context

        Args:
            retrospective: Decision retrospective
            threshold: Minimum acceptable outcome accuracy (default 0.7)

        Returns:
            Assessment dict with:
            - should_reopen (bool)
            - reasons (List[str]): Why session should/shouldn't reopen
            - priority (str): "high", "medium", "low"
            - recommended_changes (List[str]): What to change in round 2
        """
        should_reopen = False
        reasons = []
        recommended_changes = []

        # Check outcome accuracy
        outcome_accuracy = retrospective.outcome_comparison.get("overall_accuracy", 1.0)
        if outcome_accuracy < threshold:
            should_reopen = True
            reasons.append(
                f"Outcome accuracy ({outcome_accuracy:.1%}) below threshold ({threshold:.1%})"
            )
            recommended_changes.append("Re-validate assumptions with actual data")
            recommended_changes.append("Adjust outcome predictions based on learnings")

        # Check assumption results
        assumption_analysis = retrospective.assumption_analysis
        num_rejected = assumption_analysis.get("num_rejected", 0)
        num_validated = assumption_analysis.get("num_validated", 1)
        rejection_rate = num_rejected / num_validated if num_validated > 0 else 0.0

        if rejection_rate > 0.3:  # More than 30% assumptions rejected
            should_reopen = True
            reasons.append(
                f"{num_rejected} critical assumptions rejected ({rejection_rate:.1%} of validated)"
            )
            recommended_changes.append("Propose new options with corrected assumptions")

        # Determine priority
        if outcome_accuracy < 0.5 or rejection_rate > 0.5:
            priority = "high"
        elif outcome_accuracy < threshold or rejection_rate > 0.3:
            priority = "medium"
        else:
            priority = "low"

        if not should_reopen:
            reasons.append("Outcome accuracy acceptable and assumptions held")
            reasons.append("No need to reopen session")

        logger.info(
            "Assessed reopen criteria",
            extra={
                "retrospective_id": str(retrospective.retrospective_id),
                "should_reopen": should_reopen,
                "priority": priority,
                "outcome_accuracy": outcome_accuracy,
                "rejection_rate": rejection_rate,
            },
        )

        return {
            "should_reopen": should_reopen,
            "reasons": reasons,
            "priority": priority,
            "recommended_changes": recommended_changes,
        }

    async def reopen_session(
        self,
        original_session: AlignmentSession,
        retrospective: DecisionRetrospective,
        reopen_rationale: str,
        created_by: UUID,
    ) -> AlignmentSession:
        """
        Reopen a session for a new round of deliberation.

        Args:
            original_session: Original session to reopen
            retrospective: Retrospective that triggered reopening
            reopen_rationale: Why session is being reopened
            created_by: User reopening the session

        Returns:
            New AlignmentSession linked to original

        Raises:
            ValueError: If original session is not completed
        """
        if original_session.status != SessionStatus.DECIDED:
            raise ValueError(
                f"Can only reopen DECIDED sessions, got status: {original_session.status}"
            )

        # Calculate chain depth
        new_chain_depth = (original_session.chain_depth or 0) + 1

        logger.info(
            "Reopening session",
            extra={
                "original_session_id": str(original_session.session_id),
                "retrospective_id": str(retrospective.retrospective_id),
                "new_chain_depth": new_chain_depth,
            },
        )

        # Create new session
        new_session = AlignmentSession(
            session_id=uuid4(),
            team_id=original_session.team_id,
            decision_topic=f"{original_session.decision_topic} (Round {new_chain_depth + 1})",
            decision_context=(
                f"{original_session.decision_context}\n\n"
                f"ROUND {new_chain_depth + 1} CONTEXT:\n{reopen_rationale}"
            ),
            decision_type=original_session.decision_type,
            alignment_mode=original_session.alignment_mode,
            status=SessionStatus.COLLECTING,
            stakeholders=original_session.stakeholders.copy(),
            scenario_model_id=original_session.scenario_model_id,
            # Phase C: Session chaining
            parent_session_id=original_session.session_id,
            reopened_from_id=original_session.session_id,
            chain_depth=new_chain_depth,
            created_by=created_by,
            created_at=datetime.utcnow(),
        )

        logger.info(
            "Session reopened successfully",
            extra={
                "new_session_id": str(new_session.session_id),
                "parent_session_id": str(new_session.parent_session_id),
                "chain_depth": new_session.chain_depth,
            },
        )

        return new_session

    async def build_session_chain(
        self, session_id: UUID, all_sessions: List[AlignmentSession]
    ) -> List[SessionChainLink]:
        """
        Build the full session chain for a given session.

        Args:
            session_id: Session to build chain for
            all_sessions: All sessions in database (to resolve relationships)

        Returns:
            List of SessionChainLink objects representing the chain

        Raises:
            ValueError: If session not found in all_sessions
        """
        # Create lookup dict
        session_lookup = {s.session_id: s for s in all_sessions}

        if session_id not in session_lookup:
            raise ValueError(f"Session {session_id} not found in provided sessions")

        # Build chain by following parent_session_id backwards
        chain = []
        current_id = session_id

        while current_id is not None:
            current_session = session_lookup.get(current_id)
            if current_session is None:
                logger.warning(
                    "Broken session chain",
                    extra={"missing_session_id": str(current_id)},
                )
                break

            # Create chain link
            link = SessionChainLink(
                session_id=current_session.session_id,
                decision_topic=current_session.decision_topic,
                status=current_session.status,
                created_at=current_session.created_at,
                completed_at=current_session.completed_at,
                parent_session_id=current_session.parent_session_id,
                chain_depth=current_session.chain_depth or 0,
            )

            chain.append(link)

            # Move to parent
            current_id = current_session.parent_session_id

        # Reverse to get chronological order (oldest first)
        chain.reverse()

        logger.info(
            "Built session chain",
            extra={
                "session_id": str(session_id),
                "chain_length": len(chain),
            },
        )

        return chain

    async def get_chain_context(
        self,
        current_session: AlignmentSession,
        chain: List[SessionChainLink],
        retrospectives: Optional[List[DecisionRetrospective]] = None,
    ) -> str:
        """
        Generate context summary for multi-round deliberation.

        Args:
            current_session: Current session
            chain: Full session chain
            retrospectives: Optional retrospectives from previous rounds

        Returns:
            Human-readable context summary
        """
        if len(chain) <= 1:
            return "This is the first round of deliberation for this decision."

        context_parts = [
            f"MULTI-ROUND DELIBERATION (Round {current_session.chain_depth + 1})",
            "",
            "PREVIOUS ROUNDS:",
        ]

        for i, link in enumerate(chain[:-1]):  # Exclude current session
            context_parts.append(
                f"\nRound {i + 1}: {link.decision_topic}"
            )
            context_parts.append(f"  Status: {link.status.value}")
            context_parts.append(
                f"  Completed: {link.completed_at.strftime('%Y-%m-%d') if link.completed_at else 'N/A'}"
            )

        # Add retrospective insights if available
        if retrospectives:
            context_parts.append("\nKEY LEARNINGS FROM PREVIOUS ROUNDS:")
            for retro in retrospectives:
                for lesson in retro.lessons_learned[:3]:  # Top 3 lessons
                    lesson_text = lesson.get("lesson", "") if isinstance(lesson, dict) else str(lesson)
                    context_parts.append(f"  • {lesson_text}")

        context = "\n".join(context_parts)

        logger.debug(
            "Generated chain context",
            extra={
                "session_id": str(current_session.session_id),
                "chain_length": len(chain),
                "has_retrospectives": retrospectives is not None,
            },
        )

        return context
