"""Session management service."""

import logging
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from src.models import AlignmentSession, SessionStatus, DecisionType, AlignmentMode

logger = logging.getLogger(__name__)


class SessionManager:
    """Service for managing alignment sessions."""

    def __init__(self):
        """Initialize session manager."""
        # In-memory storage for now (would use database in production)
        self.sessions: Dict[UUID, AlignmentSession] = {}

    async def create(
        self,
        team_id: UUID,
        decision_topic: str,
        decision_context: str,
        decision_type: DecisionType,
        alignment_mode: AlignmentMode,
        stakeholders: List[Dict[str, str]],
        created_by: UUID,
        scenario_model_id: Optional[UUID] = None,
    ) -> AlignmentSession:
        """
        Create new alignment session.

        Args:
            team_id: Team identifier
            decision_topic: Topic of the decision
            decision_context: Context and background
            decision_type: Type of decision
            alignment_mode: Quick or evidence-backed mode
            stakeholders: List of stakeholder dicts
            created_by: User who created the session
            scenario_model_id: Optional scenario model ID for ISL integration

        Returns:
            Created alignment session
        """
        session = AlignmentSession(
            team_id=team_id,
            decision_topic=decision_topic,
            decision_context=decision_context,
            decision_type=decision_type,
            alignment_mode=alignment_mode,
            stakeholders=stakeholders,
            created_by=created_by,
            scenario_model_id=scenario_model_id,
            status=SessionStatus.COLLECTING,
        )

        self.sessions[session.session_id] = session

        logger.info(
            "Session created",
            extra={
                "session_id": str(session.session_id),
                "team_id": str(team_id),
                "decision_type": decision_type,
                "alignment_mode": alignment_mode,
                "stakeholder_count": len(stakeholders),
            },
        )

        return session

    async def get(self, session_id: UUID) -> Optional[AlignmentSession]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Alignment session or None if not found
        """
        return self.sessions.get(session_id)

    async def update_status(self, session_id: UUID, status: SessionStatus) -> None:
        """
        Update session status.

        Args:
            session_id: Session identifier
            status: New status
        """
        session = self.sessions.get(session_id)
        if session:
            session.status = status
            session.updated_at = datetime.utcnow()

            if status == SessionStatus.COMPLETE:
                session.completed_at = datetime.utcnow()

            logger.info(
                "Session status updated",
                extra={
                    "session_id": str(session_id),
                    "status": status,
                },
            )

    async def update_shared_ground(self, session_id: UUID, shared_ground: Dict) -> None:
        """
        Update session with shared ground analysis.

        Args:
            session_id: Session identifier
            shared_ground: Shared ground analysis
        """
        session = self.sessions.get(session_id)
        if session:
            session.shared_ground = shared_ground
            session.updated_at = datetime.utcnow()

    async def update_disagreement_map(
        self, session_id: UUID, disagreement_map: Dict
    ) -> None:
        """
        Update session with disagreement map.

        Args:
            session_id: Session identifier
            disagreement_map: Disagreement map analysis
        """
        session = self.sessions.get(session_id)
        if session:
            session.disagreement_map = disagreement_map
            session.updated_at = datetime.utcnow()

    async def set_selected_option(self, session_id: UUID, option_id: UUID) -> None:
        """
        Set the selected option for the session.

        Args:
            session_id: Session identifier
            option_id: Selected option ID
        """
        session = self.sessions.get(session_id)
        if session:
            session.selected_option_id = option_id
            session.updated_at = datetime.utcnow()

    async def get_pending_stakeholders(self, session_id: UUID) -> List[str]:
        """
        Get list of stakeholders who haven't submitted profiles.

        Args:
            session_id: Session identifier

        Returns:
            List of stakeholder names
        """
        # Placeholder - would check against submitted profiles
        return []

    async def generate_invite_links(self, session_id: UUID) -> Dict[str, str]:
        """
        Generate invite links for all stakeholders.

        Args:
            session_id: Session identifier

        Returns:
            Dict mapping user_id to invite URL
        """
        session = self.sessions.get(session_id)
        if not session:
            return {}

        # Placeholder - would generate actual tokens and URLs
        invite_links = {}
        for stakeholder in session.stakeholders:
            user_id = stakeholder["user_id"]
            # In production, generate secure token
            token = f"invite_token_{user_id}"
            invite_links[user_id] = f"/join/{session_id}?token={token}"

        return invite_links
