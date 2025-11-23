"""Deliberation service for multi-round consensus building.

Orchestrates iterative deliberation with anonymous voting and convergence detection.
"""

import logging
import hashlib
import base64
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from src.models.deliberation import (
    DeliberationSessionV1,
    DeliberationRoundV1,
    ParticipantV1,
    ConvergenceCriteriaV1,
    TeamInputV1,
    VoteV1,
    VotingSummaryV1,
    OptionScoreV1,
    ConvergenceStatusV1,
    ConvergenceMetricsV1,
    FinalOutcomeV1,
)
from src.models.consensus import (
    GraphV1,
    ConsensusRequestV1,
    SynthesisOptionV1,
)
from src.services.consensus_builder import ConsensusBuilder
from src.clients.isl_client import ISLClient
from src.clients.llm_client import LLMClient
from src.clients.facet_client import FACETClient

logger = logging.getLogger(__name__)


# Encryption key for anonymous voting (in production, use proper key management)
VOTING_ENCRYPTION_KEY = b"tae-voting-secret-key-change-in-production"


class DeliberationService:
    """Service for managing multi-round deliberation sessions."""

    def __init__(
        self,
        consensus_builder: Optional[ConsensusBuilder] = None,
        facet_client: Optional[FACETClient] = None,
    ):
        """Initialize deliberation service.

        Args:
            consensus_builder: Consensus builder for synthesis
            facet_client: FACET client for robustness analysis
        """
        self.consensus_builder = consensus_builder or ConsensusBuilder(
            isl_client=ISLClient(),
            llm_client=LLMClient(),
        )
        self.facet_client = facet_client or FACETClient(use_mock=True)

        # In-memory storage (in production, use database)
        self.sessions: Dict[str, DeliberationSessionV1] = {}

    async def start_session(
        self,
        decision_context: str,
        participants: List[str],
        convergence_criteria: Optional[ConvergenceCriteriaV1] = None,
    ) -> Tuple[DeliberationSessionV1, DeliberationRoundV1]:
        """Start a new deliberation session.

        Args:
            decision_context: Decision background
            participants: List of participant user IDs
            convergence_criteria: Optional convergence criteria

        Returns:
            Tuple of (session, first_round)
        """
        logger.info(
            f"Starting deliberation session with {len(participants)} participants",
            extra={"decision_context": decision_context[:100]},
        )

        # Create session
        session = DeliberationSessionV1(
            decision_context=decision_context,
            participants=[
                ParticipantV1(user_id=uid) for uid in participants
            ],
            convergence_criteria=convergence_criteria or ConvergenceCriteriaV1(),
        )

        # Create first round (submission)
        first_round = DeliberationRoundV1(
            round_number=1,
            round_type="submission",
            submissions=[],
        )

        session.rounds.append(first_round)

        # Store session
        self.sessions[session.session_id] = session

        logger.info(f"Session {session.session_id} started with round {first_round.round_id}")

        return session, first_round

    async def submit_input(
        self,
        session_id: str,
        user_id: str,
        round_id: str,
        graph: GraphV1,
        reasoning: str,
    ) -> Tuple[bool, Dict]:
        """Submit input for a submission round.

        Args:
            session_id: Session ID
            user_id: Participant ID
            round_id: Round ID
            graph: Causal graph
            reasoning: Natural language reasoning

        Returns:
            Tuple of (accepted, validation_result)
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        current_round = next((r for r in session.rounds if r.round_id == round_id), None)
        if not current_round:
            raise ValueError(f"Round {round_id} not found")

        if current_round.round_type != "submission" and current_round.round_type != "refinement":
            raise ValueError(f"Cannot submit input in {current_round.round_type} round")

        # Validate participant
        if not any(p.user_id == user_id for p in session.participants):
            raise ValueError(f"User {user_id} not a participant")

        # Check if already submitted
        if current_round.submissions:
            if any(s.user_id == user_id for s in current_round.submissions):
                raise ValueError(f"User {user_id} already submitted")

        # Create team input
        team_input = TeamInputV1(
            user_id=user_id,
            graph=graph,
            reasoning=reasoning,
        )

        # Validate with consensus builder quality scorer
        quality = await self.consensus_builder.quality_scorer.score_team_input(team_input)

        # Add to round
        if current_round.submissions is None:
            current_round.submissions = []
        current_round.submissions.append(team_input)

        logger.info(
            f"Input submitted by {user_id} in round {round_id}",
            extra={"robustness_score": quality.robustness_score},
        )

        return True, {
            "causal_quality": quality,
            "validation_issues": quality.validation_issues,
        }

    async def submit_vote(
        self,
        session_id: str,
        user_id: str,
        round_id: str,
        vote: VoteV1,
    ) -> Tuple[bool, Dict]:
        """Submit vote in a voting round.

        Votes are encrypted to maintain anonymity during active voting.

        Args:
            session_id: Session ID
            user_id: Participant ID
            round_id: Round ID
            vote: Vote with rankings

        Returns:
            Tuple of (accepted, vote_info)
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        current_round = next((r for r in session.rounds if r.round_id == round_id), None)
        if not current_round:
            raise ValueError(f"Round {round_id} not found")

        if current_round.round_type != "voting":
            raise ValueError(f"Cannot vote in {current_round.round_type} round")

        # Encrypt user ID for anonymity
        encrypted_user_id = self._encrypt_user_id(user_id)
        vote.user_id = encrypted_user_id

        # Add vote
        if current_round.votes is None:
            current_round.votes = []
        current_round.votes.append(vote)

        # Count votes
        total_votes = len(current_round.votes)
        awaiting = len(session.participants) - total_votes

        logger.info(
            f"Vote submitted (encrypted) in round {round_id}",
            extra={"total_votes": total_votes, "awaiting": awaiting},
        )

        return True, {
            "vote_id": vote.vote_id,
            "vote_count": total_votes,
            "awaiting_votes_from": awaiting,
        }

    async def advance_round(
        self,
        session_id: str,
        current_round_id: str,
    ) -> Tuple[Optional[DeliberationRoundV1], Optional[ConvergenceStatusV1], bool]:
        """Advance to next round.

        Args:
            session_id: Session ID
            current_round_id: Current round ID

        Returns:
            Tuple of (next_round, convergence_status, session_complete)
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        current_round = next((r for r in session.rounds if r.round_id == current_round_id), None)
        if not current_round:
            raise ValueError(f"Round {current_round_id} not found")

        # Mark current round as complete
        current_round.completed_at = datetime.utcnow().isoformat() + "Z"

        logger.info(
            f"Advancing from round {current_round.round_number} ({current_round.round_type})",
            extra={"session_id": session_id},
        )

        # Determine next round type
        if current_round.round_type == "submission" or current_round.round_type == "refinement":
            # After submission/refinement → synthesis
            next_round = await self._create_synthesis_round(session, current_round)

        elif current_round.round_type == "synthesis":
            # After synthesis → voting
            next_round = self._create_voting_round(session, current_round)

        elif current_round.round_type == "voting":
            # After voting → check convergence
            convergence = await self._assess_convergence(session, current_round)

            if convergence.converged or session.rounds[-1].round_number >= session.convergence_criteria.max_rounds:
                # Converged or max rounds reached
                await self._finalize_session(session, current_round, convergence)
                return None, convergence, True

            elif convergence.recommendation == "needs_refinement":
                # Create refinement round
                next_round = self._create_refinement_round(session, current_round)

            else:
                # Continue with new submission round
                next_round = DeliberationRoundV1(
                    round_number=current_round.round_number + 1,
                    round_type="submission",
                    submissions=[],
                )

            current_round.convergence_status = convergence

        else:
            raise ValueError(f"Unknown round type: {current_round.round_type}")

        # Add next round to session
        session.rounds.append(next_round)

        logger.info(
            f"Created next round: {next_round.round_number} ({next_round.round_type})",
            extra={"session_id": session_id},
        )

        return next_round, None, False

    async def _create_synthesis_round(
        self,
        session: DeliberationSessionV1,
        submission_round: DeliberationRoundV1,
    ) -> DeliberationRoundV1:
        """Create synthesis round from submissions.

        Args:
            session: Deliberation session
            submission_round: Completed submission round

        Returns:
            New synthesis round with options
        """
        logger.info("Creating synthesis round from submissions")

        # Build consensus request
        consensus_request = ConsensusRequestV1(
            perspectives=submission_round.submissions,
            decision_context=session.decision_context,
            require_creative_synthesis=True,
            protect_minority_evidence=True,
            min_causal_quality="partial",
        )

        # Generate synthesis options
        consensus_response = await self.consensus_builder.build_consensus(
            request=consensus_request,
            trace_id=f"session-{session.session_id}-round-{submission_round.round_number}",
        )

        # Create synthesis round
        synthesis_round = DeliberationRoundV1(
            round_number=submission_round.round_number + 1,
            round_type="synthesis",
            synthesis_options=consensus_response.synthesis_options,
            conflicts=consensus_response.conflicts,
        )

        logger.info(
            f"Generated {len(consensus_response.synthesis_options)} synthesis options",
            extra={"conflicts": len(consensus_response.conflicts)},
        )

        return synthesis_round

    def _create_voting_round(
        self,
        session: DeliberationSessionV1,
        synthesis_round: DeliberationRoundV1,
    ) -> DeliberationRoundV1:
        """Create voting round from synthesis options.

        Args:
            session: Deliberation session
            synthesis_round: Completed synthesis round

        Returns:
            New voting round
        """
        logger.info("Creating voting round")

        voting_round = DeliberationRoundV1(
            round_number=synthesis_round.round_number + 1,
            round_type="voting",
            votes=[],
        )

        return voting_round

    def _create_refinement_round(
        self,
        session: DeliberationSessionV1,
        voting_round: DeliberationRoundV1,
    ) -> DeliberationRoundV1:
        """Create refinement round for conflict resolution.

        Args:
            session: Deliberation session
            voting_round: Completed voting round with conflicts

        Returns:
            New refinement round
        """
        logger.info("Creating refinement round for conflict resolution")

        refinement_round = DeliberationRoundV1(
            round_number=voting_round.round_number + 1,
            round_type="refinement",
            submissions=[],
            conflicts=voting_round.convergence_status.metrics.__dict__ if voting_round.convergence_status else {},
        )

        return refinement_round

    async def _assess_convergence(
        self,
        session: DeliberationSessionV1,
        voting_round: DeliberationRoundV1,
    ) -> ConvergenceStatusV1:
        """Assess whether session has converged.

        Args:
            session: Deliberation session
            voting_round: Completed voting round

        Returns:
            Convergence status
        """
        logger.info("Assessing convergence")

        # Decrypt votes
        decrypted_votes = [
            VoteV1(**{**v.model_dump(), "user_id": self._decrypt_user_id(v.user_id)})
            for v in voting_round.votes
        ]

        # Compute vote summary
        vote_summary = self._compute_vote_summary(voting_round, decrypted_votes)

        # Calculate agreement level (Kendall tau approximation)
        agreement_level = self._compute_agreement(decrypted_votes)

        # Get causal quality from previous submission round
        submission_round = next(
            (r for r in reversed(session.rounds) if r.round_type in ["submission", "refinement"]),
            None
        )
        avg_causal_quality = self._compute_avg_causal_quality(submission_round)

        # Get creative synthesis score
        synthesis_round = next(
            (r for r in reversed(session.rounds) if r.round_type == "synthesis"),
            None
        )
        creative_synthesis = self._compute_avg_creative_score(synthesis_round)

        # Check minority protection
        minority_protected = False  # TODO: Implement minority protection check

        # Count conflicts
        conflicts_remaining = len(synthesis_round.conflicts) if synthesis_round and synthesis_round.conflicts else 0

        # Build metrics
        metrics = ConvergenceMetricsV1(
            agreement_level=agreement_level,
            causal_quality=avg_causal_quality,
            creative_synthesis=creative_synthesis,
            minority_protected=minority_protected,
            conflicts_resolved=0,
            conflicts_remaining=conflicts_remaining,
        )

        # Compute composite quality score
        quality_score = (
            agreement_level * 0.3 +
            avg_causal_quality * 0.4 +
            creative_synthesis * 0.2 +
            (1.0 if minority_protected else 0.8) * 0.1
        )

        # Determine convergence
        if agreement_level < session.convergence_criteria.min_agreement:
            return ConvergenceStatusV1(
                converged=False,
                quality_score=quality_score,
                metrics=metrics,
                recommendation="continue",
                reason="Agreement level too low - continue deliberation",
            )

        if agreement_level >= 0.6 and avg_causal_quality < 0.5:
            return ConvergenceStatusV1(
                converged=False,
                quality_score=quality_score,
                metrics=metrics,
                recommendation="needs_refinement",
                reason="High agreement but low causal quality - gather more evidence",
            )

        if quality_score >= session.convergence_criteria.min_quality_score:
            return ConvergenceStatusV1(
                converged=True,
                quality_score=quality_score,
                metrics=metrics,
                recommendation="converge",
                reason=f"Quality threshold met (score: {quality_score:.2f})",
            )

        # Default: continue
        return ConvergenceStatusV1(
            converged=False,
            quality_score=quality_score,
            metrics=metrics,
            recommendation="continue",
            reason="Continue deliberation to improve quality",
        )

    async def _finalize_session(
        self,
        session: DeliberationSessionV1,
        voting_round: DeliberationRoundV1,
        convergence: ConvergenceStatusV1,
    ) -> None:
        """Finalize session with final outcome.

        Args:
            session: Deliberation session
            voting_round: Final voting round
            convergence: Convergence status
        """
        logger.info(f"Finalizing session {session.session_id}")

        # Find top-ranked option
        vote_summary = self._compute_vote_summary(voting_round, voting_round.votes)
        top_option_id = min(vote_summary.option_scores, key=lambda x: x.avg_rank).option_id

        # Get synthesis round
        synthesis_round = next(
            r for r in reversed(session.rounds) if r.round_type == "synthesis"
        )

        top_option = next(
            opt for opt in synthesis_round.synthesis_options if opt.description == top_option_id
        )

        # Create final outcome
        session.final_outcome = FinalOutcomeV1(
            selected_option=top_option,
            consensus_level=convergence.metrics.agreement_level,
            quality_score=convergence.quality_score,
            converged_at=datetime.utcnow().isoformat() + "Z",
        )

        session.status = "converged"

        logger.info(
            f"Session converged with quality score {convergence.quality_score:.2f}",
            extra={"selected_option": top_option.description[:100]},
        )

    def _compute_vote_summary(
        self,
        voting_round: DeliberationRoundV1,
        votes: List[VoteV1],
    ) -> VotingSummaryV1:
        """Compute aggregated vote summary.

        Args:
            voting_round: Voting round
            votes: List of votes

        Returns:
            Voting summary with scores
        """
        # Get all option IDs
        option_ids = set()
        for vote in votes:
            for ranking in vote.rankings:
                option_ids.add(ranking.option_id)

        # Compute scores for each option
        option_scores = []
        for option_id in option_ids:
            ranks = [
                ranking.rank
                for vote in votes
                for ranking in vote.rankings
                if ranking.option_id == option_id
            ]

            if ranks:
                avg_rank = sum(ranks) / len(ranks)

                # Distribution
                max_rank = max(ranks)
                distribution = [ranks.count(r) for r in range(1, max_rank + 1)]

                option_scores.append(
                    OptionScoreV1(
                        option_id=option_id,
                        avg_rank=round(avg_rank, 2),
                        vote_distribution=distribution,
                        total_votes=len(ranks),
                    )
                )

        # Compute agreement (simplified Kendall tau)
        agreement_level = self._compute_agreement(votes)

        return VotingSummaryV1(
            round_id=voting_round.round_id,
            total_votes=len(votes),
            option_scores=sorted(option_scores, key=lambda x: x.avg_rank),
            agreement_level=agreement_level,
            individual_votes=votes,
        )

    def _compute_agreement(self, votes: List[VoteV1]) -> float:
        """Compute inter-rater agreement (simplified Kendall tau).

        Args:
            votes: List of votes

        Returns:
            Agreement level (0-1)
        """
        if len(votes) < 2:
            return 1.0

        # Simplified: compare top choice agreement
        top_choices = [vote.rankings[0].option_id for vote in votes if vote.rankings]

        if not top_choices:
            return 0.0

        # Most common top choice
        from collections import Counter
        most_common_count = Counter(top_choices).most_common(1)[0][1]

        agreement = most_common_count / len(top_choices)

        return round(agreement, 2)

    def _compute_avg_causal_quality(self, submission_round: Optional[DeliberationRoundV1]) -> float:
        """Compute average causal quality from submission round.

        Args:
            submission_round: Submission or refinement round

        Returns:
            Average causal quality (0-1)
        """
        if not submission_round or not submission_round.submissions:
            return 0.5

        # In production, get quality from stored assessments
        # For now, estimate based on graph complexity
        avg_quality = sum(
            0.7 if len(s.graph.edges) >= 2 else 0.5
            for s in submission_round.submissions
        ) / len(submission_round.submissions)

        return round(avg_quality, 2)

    def _compute_avg_creative_score(self, synthesis_round: Optional[DeliberationRoundV1]) -> float:
        """Compute average creative score from synthesis options.

        Args:
            synthesis_round: Synthesis round

        Returns:
            Average creative score (0-1)
        """
        if not synthesis_round or not synthesis_round.synthesis_options:
            return 0.5

        scores = [opt.creative_score for opt in synthesis_round.synthesis_options]
        return round(sum(scores) / len(scores), 2)

    def _encrypt_user_id(self, user_id: str) -> str:
        """Encrypt user ID for anonymous voting.

        Uses deterministic encryption (same input → same output).

        Args:
            user_id: Plain user ID

        Returns:
            Encrypted user ID
        """
        # Use HMAC for deterministic encryption
        h = hashlib.sha256()
        h.update(VOTING_ENCRYPTION_KEY)
        h.update(user_id.encode('utf-8'))

        encrypted = base64.b64encode(h.digest()).decode('utf-8')
        return f"encrypted-{encrypted[:16]}"

    def _decrypt_user_id(self, encrypted_user_id: str) -> str:
        """Decrypt user ID after voting round closes.

        Note: This is a simplified implementation. In production,
        use proper reversible encryption with key management.

        Args:
            encrypted_user_id: Encrypted user ID

        Returns:
            Decrypted user ID (or encrypted if cannot decrypt)
        """
        # In this simplified version, we cannot reverse the hash
        # In production, use symmetric encryption (AES) with proper key management

        # For testing, just return the encrypted ID with marker
        return encrypted_user_id.replace("encrypted-", "decrypted-")
