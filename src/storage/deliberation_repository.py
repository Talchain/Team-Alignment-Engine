"""Repository for deliberation session persistence.

Handles all database operations for multi-round deliberation sessions.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.storage.db_models import (
    DeliberationSessionDB,
    DeliberationRoundDB,
    DeliberationSubmissionDB,
    DeliberationVoteDB,
    DeliberationConflictDB,
)
from src.models.deliberation import (
    DeliberationSessionV1,
    DeliberationRoundV1,
    VoteV1,
    ParticipantV1,
    ConvergenceCriteriaV1,
    FinalOutcomeV1,
    ConvergenceStatusV1,
)
from src.models.consensus import (
    ConflictAnalysisV1,
    TeamInputV1,
    CausalQualityV1,
    GraphV1,
)

logger = logging.getLogger(__name__)


class DeliberationRepository:
    """Repository for deliberation session persistence."""

    def __init__(self, db: AsyncSession):
        """Initialize repository.

        Args:
            db: Database session
        """
        self.db = db

    # ========================================================================
    # SESSION OPERATIONS
    # ========================================================================

    async def create_session(
        self,
        session: DeliberationSessionV1,
    ) -> DeliberationSessionV1:
        """Create new deliberation session.

        Args:
            session: Session to create

        Returns:
            Created session
        """
        logger.info(f"Creating deliberation session {session.session_id}")

        db_session = DeliberationSessionDB(
            session_id=session.session_id,
            decision_context=session.decision_context,
            participants=[p.model_dump() for p in session.participants],
            status=session.status,
            convergence_criteria=session.convergence_criteria.model_dump(),
            final_outcome=session.final_outcome.model_dump() if session.final_outcome else None,
        )

        self.db.add(db_session)
        await self.db.flush()

        return session

    async def get_session(
        self,
        session_id: str,
    ) -> Optional[DeliberationSessionV1]:
        """Get deliberation session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session or None
        """
        result = await self.db.execute(
            select(DeliberationSessionDB).where(
                DeliberationSessionDB.session_id == session_id
            )
        )
        db_session = result.scalar_one_or_none()

        if not db_session:
            return None

        # Get all rounds for this session
        rounds = await self.get_rounds_for_session(session_id)

        return DeliberationSessionV1(
            session_id=db_session.session_id,
            decision_context=db_session.decision_context,
            participants=[ParticipantV1(**p) for p in db_session.participants],
            rounds=rounds,
            convergence_criteria=ConvergenceCriteriaV1(**db_session.convergence_criteria),
            final_outcome=FinalOutcomeV1(**db_session.final_outcome) if db_session.final_outcome else None,
            status=db_session.status,
        )

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        final_outcome: Optional[FinalOutcomeV1] = None,
    ) -> None:
        """Update session status.

        Args:
            session_id: Session ID
            status: New status
            final_outcome: Final outcome if converged
        """
        await self.db.execute(
            update(DeliberationSessionDB)
            .where(DeliberationSessionDB.session_id == session_id)
            .values(
                status=status,
                final_outcome=final_outcome.model_dump() if final_outcome else None,
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.flush()

    # ========================================================================
    # ROUND OPERATIONS
    # ========================================================================

    async def create_round(
        self,
        round_obj: DeliberationRoundV1,
    ) -> DeliberationRoundV1:
        """Create new deliberation round.

        Args:
            round_obj: Round to create

        Returns:
            Created round
        """
        logger.info(f"Creating round {round_obj.round_id} for session {round_obj.session_id}")

        db_round = DeliberationRoundDB(
            round_id=round_obj.round_id,
            session_id=round_obj.session_id,
            round_number=round_obj.round_number,
            round_type=round_obj.round_type,
            started_at=round_obj.started_at,
            completed_at=round_obj.completed_at,
            synthesis_options=[opt.model_dump() for opt in round_obj.synthesis_options] if round_obj.synthesis_options else None,
            convergence_status=round_obj.convergence_status.model_dump() if round_obj.convergence_status else None,
        )

        self.db.add(db_round)
        await self.db.flush()

        return round_obj

    async def get_round(
        self,
        round_id: str,
    ) -> Optional[DeliberationRoundV1]:
        """Get round by ID.

        Args:
            round_id: Round ID

        Returns:
            Round or None
        """
        result = await self.db.execute(
            select(DeliberationRoundDB).where(DeliberationRoundDB.round_id == round_id)
        )
        db_round = result.scalar_one_or_none()

        if not db_round:
            return None

        # Get submissions for this round
        submissions = await self.get_submissions_for_round(round_id)

        # Get votes for this round
        votes = await self.get_votes_for_round(round_id)

        from src.models.deliberation import SynthesisOptionV1

        return DeliberationRoundV1(
            round_id=db_round.round_id,
            session_id=db_round.session_id,
            round_number=db_round.round_number,
            round_type=db_round.round_type,
            started_at=db_round.started_at,
            completed_at=db_round.completed_at,
            submissions=submissions,
            synthesis_options=[SynthesisOptionV1(**opt) for opt in db_round.synthesis_options] if db_round.synthesis_options else None,
            votes=votes,
            convergence_status=ConvergenceStatusV1(**db_round.convergence_status) if db_round.convergence_status else None,
        )

    async def get_rounds_for_session(
        self,
        session_id: str,
    ) -> List[DeliberationRoundV1]:
        """Get all rounds for a session.

        PERFORMANCE: Optimized to avoid N+1 queries by batching related data fetches.

        Args:
            session_id: Session ID

        Returns:
            List of rounds
        """
        # Fetch all rounds in one query
        result = await self.db.execute(
            select(DeliberationRoundDB)
            .where(DeliberationRoundDB.session_id == session_id)
            .order_by(DeliberationRoundDB.round_number)
        )
        db_rounds = result.scalars().all()

        if not db_rounds:
            return []

        # Extract round IDs for batch fetching
        round_ids = [db_round.round_id for db_round in db_rounds]

        # Fetch all submissions for all rounds in ONE query (avoid N+1)
        submissions_result = await self.db.execute(
            select(DeliberationSubmissionDB)
            .where(DeliberationSubmissionDB.round_id.in_(round_ids))
            .order_by(DeliberationSubmissionDB.submitted_at)
        )
        all_submissions = submissions_result.scalars().all()

        # Group submissions by round_id
        submissions_by_round = {}
        for sub in all_submissions:
            if sub.round_id not in submissions_by_round:
                submissions_by_round[sub.round_id] = []
            submissions_by_round[sub.round_id].append(
                TeamInputV1(
                    user_id=sub.user_id,
                    graph=GraphV1(**sub.graph),
                    reasoning=sub.reasoning,
                    submitted_at=sub.submitted_at,
                )
            )

        # Fetch all votes for all rounds in ONE query (avoid N+1)
        votes_result = await self.db.execute(
            select(DeliberationVoteDB)
            .where(DeliberationVoteDB.round_id.in_(round_ids))
            .order_by(DeliberationVoteDB.submitted_at)
        )
        all_votes = votes_result.scalars().all()

        # Group votes by round_id
        from src.models.deliberation import RankingV1

        votes_by_round = {}
        for vote in all_votes:
            if vote.round_id not in votes_by_round:
                votes_by_round[vote.round_id] = []
            votes_by_round[vote.round_id].append(
                VoteV1(
                    user_id=vote.user_id if vote.user_id else "anonymous",
                    round_id=vote.round_id,
                    rankings=[RankingV1(**r) for r in vote.rankings],
                    submitted_at=vote.submitted_at,
                )
            )

        # Assemble rounds with their related data
        from src.models.deliberation import SynthesisOptionV1

        rounds = []
        for db_round in db_rounds:
            rounds.append(
                DeliberationRoundV1(
                    round_id=db_round.round_id,
                    session_id=db_round.session_id,
                    round_number=db_round.round_number,
                    round_type=db_round.round_type,
                    started_at=db_round.started_at,
                    completed_at=db_round.completed_at,
                    submissions=submissions_by_round.get(db_round.round_id, []),
                    synthesis_options=[SynthesisOptionV1(**opt) for opt in db_round.synthesis_options]
                    if db_round.synthesis_options
                    else None,
                    votes=votes_by_round.get(db_round.round_id, []),
                    convergence_status=ConvergenceStatusV1(**db_round.convergence_status)
                    if db_round.convergence_status
                    else None,
                )
            )

        return rounds

    async def update_round_synthesis_options(
        self,
        round_id: str,
        synthesis_options: List[Any],
    ) -> None:
        """Update synthesis options for a round.

        Args:
            round_id: Round ID
            synthesis_options: Synthesis options
        """
        await self.db.execute(
            update(DeliberationRoundDB)
            .where(DeliberationRoundDB.round_id == round_id)
            .values(synthesis_options=[opt.model_dump() for opt in synthesis_options])
        )
        await self.db.flush()

    async def update_round_convergence_status(
        self,
        round_id: str,
        convergence_status: ConvergenceStatusV1,
    ) -> None:
        """Update convergence status for a round.

        Args:
            round_id: Round ID
            convergence_status: Convergence status
        """
        await self.db.execute(
            update(DeliberationRoundDB)
            .where(DeliberationRoundDB.round_id == round_id)
            .values(convergence_status=convergence_status.model_dump())
        )
        await self.db.flush()

    async def complete_round(
        self,
        round_id: str,
    ) -> None:
        """Mark round as completed.

        Args:
            round_id: Round ID
        """
        await self.db.execute(
            update(DeliberationRoundDB)
            .where(DeliberationRoundDB.round_id == round_id)
            .values(completed_at=datetime.utcnow())
        )
        await self.db.flush()

    # ========================================================================
    # SUBMISSION OPERATIONS
    # ========================================================================

    async def create_submission(
        self,
        submission: TeamInputV1,
        session_id: str,
        round_id: str,
        causal_quality: CausalQualityV1,
        validation_issues: List[str],
    ) -> TeamInputV1:
        """Create new submission.

        Args:
            submission: Team input to create
            session_id: Session ID
            round_id: Round ID
            causal_quality: Causal quality assessment
            validation_issues: Validation issues

        Returns:
            Created submission
        """
        logger.info(f"Creating submission for user {submission.user_id} in round {round_id}")

        db_submission = DeliberationSubmissionDB(
            round_id=round_id,
            session_id=session_id,
            user_id=submission.user_id,
            graph=submission.graph.model_dump(),
            reasoning=submission.reasoning,
            causal_quality=causal_quality.model_dump(),
            validation_issues=validation_issues,
            evidence_items=None,  # Will be added later via evidence extraction
            unsupported_claims=None,  # Will be added later via evidence extraction
            submitted_at=submission.submitted_at,
        )

        self.db.add(db_submission)
        await self.db.flush()

        return submission

    async def get_submissions_for_round(
        self,
        round_id: str,
    ) -> List[TeamInputV1]:
        """Get all submissions for a round.

        Args:
            round_id: Round ID

        Returns:
            List of team inputs
        """
        result = await self.db.execute(
            select(DeliberationSubmissionDB)
            .where(DeliberationSubmissionDB.round_id == round_id)
            .order_by(DeliberationSubmissionDB.submitted_at)
        )
        db_submissions = result.scalars().all()

        submissions = []
        for db_sub in db_submissions:
            submissions.append(
                TeamInputV1(
                    user_id=db_sub.user_id,
                    graph=GraphV1(**db_sub.graph),
                    reasoning=db_sub.reasoning,
                    submitted_at=db_sub.submitted_at,
                )
            )

        return submissions

    # ========================================================================
    # VOTE OPERATIONS
    # ========================================================================

    async def create_vote(
        self,
        vote: VoteV1,
        session_id: str,
        encrypted_user_id: str,
    ) -> str:
        """Create new vote.

        Args:
            vote: Vote to create
            session_id: Session ID
            encrypted_user_id: Encrypted user ID for anonymity

        Returns:
            Vote ID
        """
        logger.info(f"Creating anonymous vote for round {vote.round_id}")

        vote_id = str(uuid4())

        db_vote = DeliberationVoteDB(
            vote_id=vote_id,
            round_id=vote.round_id,
            session_id=session_id,
            encrypted_user_id=encrypted_user_id,
            user_id=None,  # Not revealed until round closes
            rankings=[r.model_dump() for r in vote.rankings],
            submitted_at=vote.submitted_at,
        )

        self.db.add(db_vote)
        await self.db.flush()

        return vote_id

    async def get_votes_for_round(
        self,
        round_id: str,
        reveal_user_ids: bool = False,
    ) -> List[VoteV1]:
        """Get all votes for a round.

        Args:
            round_id: Round ID
            reveal_user_ids: Whether to include user IDs (only after round closes)

        Returns:
            List of votes
        """
        result = await self.db.execute(
            select(DeliberationVoteDB)
            .where(DeliberationVoteDB.round_id == round_id)
            .order_by(DeliberationVoteDB.submitted_at)
        )
        db_votes = result.scalars().all()

        from src.models.deliberation import RankingV1

        votes = []
        for db_vote in db_votes:
            votes.append(
                VoteV1(
                    user_id=db_vote.user_id if reveal_user_ids else "anonymous",
                    round_id=db_vote.round_id,
                    rankings=[RankingV1(**r) for r in db_vote.rankings],
                    submitted_at=db_vote.submitted_at,
                )
            )

        return votes

    async def reveal_vote_user_ids(
        self,
        round_id: str,
        decryption_map: Dict[str, str],
    ) -> None:
        """Reveal user IDs for votes after round closes.

        Args:
            round_id: Round ID
            decryption_map: Map of encrypted_user_id -> user_id
        """
        logger.info(f"Revealing user IDs for round {round_id}")

        result = await self.db.execute(
            select(DeliberationVoteDB).where(DeliberationVoteDB.round_id == round_id)
        )
        db_votes = result.scalars().all()

        for db_vote in db_votes:
            if db_vote.encrypted_user_id in decryption_map:
                await self.db.execute(
                    update(DeliberationVoteDB)
                    .where(DeliberationVoteDB.vote_id == db_vote.vote_id)
                    .values(user_id=decryption_map[db_vote.encrypted_user_id])
                )

        await self.db.flush()

    # ========================================================================
    # CONFLICT OPERATIONS
    # ========================================================================

    async def create_conflict(
        self,
        session_id: str,
        round_id: str,
        conflict_analysis: ConflictAnalysisV1,
        decisive_test: Optional[Any] = None,
        pareto_analysis: Optional[Any] = None,
        reframing_analysis: Optional[Any] = None,
    ) -> str:
        """Create conflict record.

        Args:
            session_id: Session ID
            round_id: Round ID
            conflict_analysis: Conflict analysis
            decisive_test: Decisive test suggestion
            pareto_analysis: Pareto analysis
            reframing_analysis: Reframing analysis

        Returns:
            Conflict ID
        """
        logger.info(f"Creating conflict record for session {session_id}")

        conflict_id = str(uuid4())

        db_conflict = DeliberationConflictDB(
            conflict_id=conflict_id,
            session_id=session_id,
            round_id=round_id,
            conflict_analysis=conflict_analysis.model_dump(),
            decisive_test=decisive_test.model_dump() if decisive_test else None,
            pareto_analysis=pareto_analysis.model_dump() if pareto_analysis else None,
            reframing_analysis=reframing_analysis.model_dump() if reframing_analysis else None,
        )

        self.db.add(db_conflict)
        await self.db.flush()

        return conflict_id

    async def get_conflicts_for_round(
        self,
        round_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all conflicts for a round.

        Args:
            round_id: Round ID

        Returns:
            List of conflict records
        """
        result = await self.db.execute(
            select(DeliberationConflictDB)
            .where(DeliberationConflictDB.round_id == round_id)
            .order_by(DeliberationConflictDB.detected_at)
        )
        db_conflicts = result.scalars().all()

        conflicts = []
        for db_conflict in db_conflicts:
            conflicts.append({
                "conflict_id": str(db_conflict.conflict_id),
                "conflict_analysis": db_conflict.conflict_analysis,
                "decisive_test": db_conflict.decisive_test,
                "pareto_analysis": db_conflict.pareto_analysis,
                "reframing_analysis": db_conflict.reframing_analysis,
                "detected_at": db_conflict.detected_at.isoformat() + "Z",
            })

        return conflicts
