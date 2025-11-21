"""Cross-team coordination manager service for Phase D6."""

import logging
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.portfolio import (
    CoordinationGroup,
    ConflictDetection,
    CoordinationView,
)
from src.models.session import AlignmentSession
from src.models.enums import SessionStatus
from src.services.dependency_manager import DecisionDependencyManager

logger = logging.getLogger(__name__)


class CrossTeamCoordinator:
    """Manage coordination across multiple teams."""

    def __init__(self, db: AsyncSession):
        """
        Initialize cross-team coordinator.

        Args:
            db: Database session
        """
        self.db = db
        self.dependency_manager = DecisionDependencyManager(db)

    async def create_coordination_group(
        self,
        name: str,
        description: str,
        session_ids: List[UUID],
        created_by: str,
    ) -> CoordinationGroup:
        """
        Create a coordination group linking multiple team decisions.

        Args:
            name: Group name
            description: Group description
            session_ids: Sessions to coordinate
            created_by: User who created group

        Returns:
            Created coordination group
        """
        try:
            group = CoordinationGroup(
                group_id=uuid4(),
                name=name,
                description=description,
                session_ids=[str(sid) for sid in session_ids],
                created_by=created_by,
                created_at=datetime.utcnow(),
            )

            # TODO: Store in database when coordination table exists

            logger.info(
                "coordination_group_created",
                extra={
                    "group_id": str(group.group_id),
                    "session_count": len(session_ids),
                },
            )

            return group

        except Exception as e:
            logger.error(
                "failed_to_create_coordination_group",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def detect_conflicts(
        self, session_ids: List[UUID]
    ) -> List[ConflictDetection]:
        """
        Detect conflicts between decisions.

        Args:
            session_ids: Sessions to analyze

        Returns:
            List of detected conflicts
        """
        try:
            # Get sessions
            query = select(AlignmentSession).where(
                AlignmentSession.session_id.in_(session_ids)
            )
            result = await self.db.execute(query)
            sessions = list(result.scalars().all())

            conflicts = []

            # Check for temporal conflicts (overlapping timelines)
            temporal_conflicts = self._detect_temporal_conflicts(sessions)
            conflicts.extend(temporal_conflicts)

            # Check for resource conflicts (same stakeholders)
            resource_conflicts = self._detect_resource_conflicts(sessions)
            conflicts.extend(resource_conflicts)

            # Check for dependency conflicts
            dependency_conflicts = await self._detect_dependency_conflicts(sessions)
            conflicts.extend(dependency_conflicts)

            # Check for scope conflicts (related topics)
            scope_conflicts = self._detect_scope_conflicts(sessions)
            conflicts.extend(scope_conflicts)

            logger.info(
                "conflict_detection_completed",
                extra={
                    "session_count": len(sessions),
                    "conflicts_found": len(conflicts),
                },
            )

            return conflicts

        except Exception as e:
            logger.error(
                "failed_to_detect_conflicts",
                extra={"error": str(e)},
                exc_info=True,
            )
            return []

    def _detect_temporal_conflicts(
        self, sessions: List[AlignmentSession]
    ) -> List[ConflictDetection]:
        """
        Detect sessions with overlapping timelines.

        Args:
            sessions: Sessions to analyze

        Returns:
            List of temporal conflicts
        """
        conflicts = []

        # Find active sessions
        active = [s for s in sessions if s.status != SessionStatus.COMPLETE]

        if len(active) >= 2:
            # Multiple active decisions may indicate overload
            session_ids_involved = [str(s.session_id) for s in active]

            conflicts.append(
                ConflictDetection(
                    conflict_id=uuid4(),
                    conflict_type="temporal",
                    session_ids=session_ids_involved,
                    severity="medium",
                    description=f"{len(active)} decisions active simultaneously may cause timeline conflicts",
                    detected_at=datetime.utcnow(),
                    resolution_suggestions=[
                        "Prioritize decisions based on urgency",
                        "Consider sequential processing",
                        "Allocate dedicated resources per decision",
                    ],
                )
            )

        return conflicts

    def _detect_resource_conflicts(
        self, sessions: List[AlignmentSession]
    ) -> List[ConflictDetection]:
        """
        Detect sessions competing for same stakeholders.

        Args:
            sessions: Sessions to analyze

        Returns:
            List of resource conflicts
        """
        conflicts = []

        # Build stakeholder participation map
        stakeholder_sessions: Dict[str, List[UUID]] = {}
        for session in sessions:
            for stakeholder in session.stakeholders:
                user_id = stakeholder.get("user_id", "")
                if user_id not in stakeholder_sessions:
                    stakeholder_sessions[user_id] = []
                stakeholder_sessions[user_id].append(session.session_id)

        # Find stakeholders involved in multiple active sessions
        active_sessions = {
            s.session_id: s for s in sessions if s.status != SessionStatus.COMPLETE
        }

        for user_id, session_ids in stakeholder_sessions.items():
            active_involvement = [sid for sid in session_ids if sid in active_sessions]

            if len(active_involvement) >= 3:
                # Stakeholder overloaded
                conflicts.append(
                    ConflictDetection(
                        conflict_id=uuid4(),
                        conflict_type="resource",
                        session_ids=[str(sid) for sid in active_involvement],
                        severity="high",
                        description=f"Key stakeholder involved in {len(active_involvement)} simultaneous decisions",
                        detected_at=datetime.utcnow(),
                        resolution_suggestions=[
                            "Stagger decision timelines to reduce load",
                            "Delegate some decisions to alternate stakeholders",
                            "Increase decision-making capacity",
                        ],
                    )
                )

        return conflicts

    async def _detect_dependency_conflicts(
        self, sessions: List[AlignmentSession]
    ) -> List[ConflictDetection]:
        """
        Detect conflicting dependencies.

        Args:
            sessions: Sessions to analyze

        Returns:
            List of dependency conflicts
        """
        conflicts = []

        # Check for circular dependencies (already prevented by dependency manager)
        # Check for long dependency chains

        for session in sessions:
            blocking_sessions = await self.dependency_manager.get_blocking_sessions(
                session.session_id
            )

            if len(blocking_sessions) >= 3:
                # Decision blocked by many dependencies
                conflicts.append(
                    ConflictDetection(
                        conflict_id=uuid4(),
                        conflict_type="dependency",
                        session_ids=[str(session.session_id)]
                        + [str(sid) for sid in blocking_sessions],
                        severity="high",
                        description=f"Decision blocked by {len(blocking_sessions)} dependencies",
                        detected_at=datetime.utcnow(),
                        resolution_suggestions=[
                            "Review if all dependencies are truly necessary",
                            "Parallelize independent dependency chains",
                            "Fast-track critical blocking decisions",
                        ],
                    )
                )

        return conflicts

    def _detect_scope_conflicts(
        self, sessions: List[AlignmentSession]
    ) -> List[ConflictDetection]:
        """
        Detect sessions with overlapping scope.

        Args:
            sessions: Sessions to analyze

        Returns:
            List of scope conflicts
        """
        conflicts = []

        # Group by decision type
        by_type: Dict[str, List[AlignmentSession]] = {}
        for session in sessions:
            if session.decision_type not in by_type:
                by_type[session.decision_type] = []
            by_type[session.decision_type].append(session)

        # Check for multiple active decisions of same type
        for decision_type, type_sessions in by_type.items():
            active = [s for s in type_sessions if s.status != SessionStatus.COMPLETE]

            if len(active) >= 2:
                conflicts.append(
                    ConflictDetection(
                        conflict_id=uuid4(),
                        conflict_type="scope",
                        session_ids=[str(s.session_id) for s in active],
                        severity="medium",
                        description=f"Multiple active {decision_type} decisions may have overlapping scope",
                        detected_at=datetime.utcnow(),
                        resolution_suggestions=[
                            "Clarify scope boundaries between decisions",
                            "Consider merging related decisions",
                            "Establish coordination checkpoints",
                        ],
                    )
                )

        return conflicts

    async def get_coordination_view(
        self, organization_id: UUID, team_ids: Optional[List[UUID]] = None
    ) -> CoordinationView:
        """
        Get coordination view across teams.

        Args:
            organization_id: Organization ID
            team_ids: Optional team filter

        Returns:
            Coordination view with conflicts and groups
        """
        try:
            # Get active sessions
            query = select(AlignmentSession).where(
                AlignmentSession.status != SessionStatus.COMPLETE
            )
            if team_ids:
                query = query.where(AlignmentSession.team_id.in_(team_ids))

            result = await self.db.execute(query)
            sessions = list(result.scalars().all())

            if not sessions:
                return CoordinationView(
                    organization_id=organization_id,
                    active_decisions=[],
                    conflicts=[],
                    coordination_groups=[],
                    coordination_needed=False,
                    generated_at=datetime.utcnow(),
                )

            # Detect conflicts
            session_ids = [s.session_id for s in sessions]
            conflicts = await self.detect_conflicts(session_ids)

            # Get coordination groups (placeholder - would query from database)
            groups: List[CoordinationGroup] = []

            return CoordinationView(
                organization_id=organization_id,
                active_decisions=[str(s.session_id) for s in sessions],
                conflicts=conflicts,
                coordination_groups=groups,
                coordination_needed=len(conflicts) > 0,
                generated_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(
                "failed_to_get_coordination_view",
                extra={
                    "organization_id": str(organization_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def resolve_conflict(self, conflict_id: UUID, resolution: str) -> None:
        """
        Mark a conflict as resolved.

        Args:
            conflict_id: Conflict ID
            resolution: Resolution description
        """
        try:
            # TODO: Update in database when conflict table exists

            logger.info(
                "conflict_resolved",
                extra={
                    "conflict_id": str(conflict_id),
                    "resolution": resolution,
                },
            )

        except Exception as e:
            logger.error(
                "failed_to_resolve_conflict",
                extra={
                    "conflict_id": str(conflict_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
