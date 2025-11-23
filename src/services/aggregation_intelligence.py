"""Aggregation intelligence service (Phase 3: Navajas Methods).

Implements confidence calibration, strategic behavior detection, and optimal team composition analysis.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from src.models.aggregation import (
    ConfidenceAnalysisV1,
    ConfidenceCalibrationFactorsV1,
    StrategyDetectionV1,
    DetectedPatternV1,
    MitigationActionV1,
    TeamSizeAnalysisV1,
    TeamSizeAnalysisDetailsV1,
    CommunicationAnalysisV1,
    CommunicationPatternV1,
    RecommendedWeightV1,
    WeightBreakdownV1,
    AggregationQualityV1,
)
from src.models.deliberation import DeliberationSessionV1, DeliberationRoundV1
from src.models.consensus import TeamInputV1

logger = logging.getLogger(__name__)


class AggregationIntelligenceService:
    """Service for aggregation intelligence using Navajas methods."""

    def __init__(self):
        """Initialize aggregation service."""
        # In-memory storage for user history (in production, use database)
        self.user_history: Dict[str, List[Dict]] = defaultdict(list)

    # ========================================================================
    # CONFIDENCE CALIBRATION
    # ========================================================================

    def calibrate_confidence(
        self,
        user_id: str,
        stated_confidence: float,
        domain: str,
    ) -> ConfidenceAnalysisV1:
        """Calibrate user's stated confidence based on historical accuracy.

        Args:
            user_id: User ID
            stated_confidence: User's stated confidence (0-1)
            domain: Decision domain

        Returns:
            Confidence analysis with calibrated value
        """
        # Get user history
        history = self.user_history.get(user_id, [])

        # Compute historical accuracy (Brier score)
        historical_accuracy = self._compute_brier_score(history)

        # Compute domain expertise
        expertise = self._compute_domain_expertise(user_id, domain, history)

        # Detect overconfidence pattern
        overconfidence_bias = self._detect_overconfidence(history)

        # Calibrate confidence
        calibrated = stated_confidence * historical_accuracy * expertise / (1.0 + overconfidence_bias)
        calibrated = max(0.0, min(1.0, calibrated))

        # Determine recommendation
        if calibrated > stated_confidence * 1.1:
            recommendation = "increase_weight"
        elif calibrated < stated_confidence * 0.9:
            recommendation = "decrease_weight"
        else:
            recommendation = "unchanged"

        factors = ConfidenceCalibrationFactorsV1(
            historical_accuracy=historical_accuracy,
            domain_expertise=expertise,
            overconfidence_bias=overconfidence_bias,
        )

        return ConfidenceAnalysisV1(
            user_id=user_id,
            stated_confidence=stated_confidence,
            calibrated_confidence=calibrated,
            calibration_factors=factors,
            recommendation=recommendation,
        )

    def _compute_brier_score(self, history: List[Dict]) -> float:
        """Compute Brier score from user history.

        Args:
            history: List of past predictions

        Returns:
            Historical accuracy (1 - Brier score, 0-1)
        """
        if not history:
            return 0.7  # Neutral prior

        # Simplified: assume history contains {confidence, outcome, predicted}
        total_score = 0.0
        for record in history[-20:]:  # Last 20 decisions
            confidence = record.get("confidence", 0.5)
            correct = record.get("correct", 0.5)  # 1 if correct, 0 if wrong
            brier = (confidence - correct) ** 2
            total_score += (1.0 - brier)

        return total_score / min(len(history), 20)

    def _compute_domain_expertise(
        self,
        user_id: str,
        domain: str,
        history: List[Dict],
    ) -> float:
        """Compute domain expertise based on role and history.

        Args:
            user_id: User ID
            domain: Decision domain
            history: User history

        Returns:
            Domain expertise score (0-1)
        """
        # Simplified: check if user has relevant history in this domain
        domain_history = [h for h in history if h.get("domain") == domain]

        if not domain_history:
            return 0.5  # Neutral if no domain history

        # Higher expertise if more domain-specific history
        expertise = min(1.0, len(domain_history) / 10.0 + 0.5)
        return expertise

    def _detect_overconfidence(self, history: List[Dict]) -> float:
        """Detect overconfidence bias in user's historical predictions.

        Args:
            history: User history

        Returns:
            Overconfidence bias score (0=none, >0=overconfident)
        """
        if len(history) < 5:
            return 0.0  # Not enough data

        # Compare stated confidence to actual accuracy
        total_overconfidence = 0.0
        count = 0

        for record in history[-20:]:
            stated = record.get("confidence", 0.5)
            correct = record.get("correct", 0.5)

            # Overconfidence = stated confidence exceeds actual performance
            overconfidence = max(0.0, stated - correct)
            total_overconfidence += overconfidence
            count += 1

        avg_overconfidence = total_overconfidence / count if count > 0 else 0.0

        # Bias factor (0-1, higher = more overconfident)
        return min(1.0, avg_overconfidence * 2.0)

    # ========================================================================
    # STRATEGIC BEHAVIOR DETECTION
    # ========================================================================

    def detect_strategic_behavior(
        self,
        session: DeliberationSessionV1,
    ) -> StrategyDetectionV1:
        """Detect strategic behavior patterns in deliberation session.

        Args:
            session: Deliberation session

        Returns:
            Strategy detection results
        """
        patterns = []

        # Detect anchoring
        anchoring = self._detect_anchoring(session)
        if anchoring:
            patterns.append(anchoring)

        # Detect conformity
        conformity = self._detect_conformity(session)
        if conformity:
            patterns.append(conformity)

        # Detect withholding
        withholding = self._detect_withholding(session)
        if withholding:
            patterns.append(withholding)

        # Detect strategic voting
        strategic_voting = self._detect_strategic_voting(session)
        if strategic_voting:
            patterns.append(strategic_voting)

        # Generate mitigation actions
        mitigations = self._generate_mitigations(patterns)

        return StrategyDetectionV1(
            session_id=session.session_id,
            detected_patterns=patterns,
            mitigation_applied=mitigations,
        )

    def _detect_anchoring(
        self,
        session: DeliberationSessionV1,
    ) -> Optional[DetectedPatternV1]:
        """Detect anchoring bias (early submissions bias later ones).

        Args:
            session: Deliberation session

        Returns:
            Detected pattern or None
        """
        if not session.rounds or len(session.rounds) < 2:
            return None

        first_round = session.rounds[0]
        if not first_round.submissions or len(first_round.submissions) < 2:
            return None

        # Check if later submissions are similar to first submission
        first_sub = first_round.submissions[0]
        later_subs = first_round.submissions[1:]

        # Simple similarity check: count users with similar language
        similar_count = 0
        for sub in later_subs:
            # Check if reasoning contains key phrases from first submission
            first_words = set(first_sub.reasoning.lower().split()[:20])
            sub_words = set(sub.reasoning.lower().split()[:20])
            overlap = len(first_words & sub_words)

            if overlap > 5:  # Significant overlap
                similar_count += 1

        if similar_count >= len(later_subs) * 0.4:  # 40% threshold
            return DetectedPatternV1(
                pattern_type="anchoring",
                affected_users=[s.user_id for s in later_subs],
                confidence=0.7,
                evidence=[
                    f"First submission at {first_sub.submitted_at} may have anchored {similar_count} later submissions",
                    "Similar language/structure detected in subsequent inputs",
                ],
            )

        return None

    def _detect_conformity(
        self,
        session: DeliberationSessionV1,
    ) -> Optional[DetectedPatternV1]:
        """Detect conformity pressure (avoiding disagreement).

        Args:
            session: Deliberation session

        Returns:
            Detected pattern or None
        """
        if len(session.rounds) < 3:
            return None

        # Check if voting round shows high agreement without strong causal backing
        voting_rounds = [r for r in session.rounds if r.round_type == "voting"]
        if not voting_rounds:
            return None

        vote_round = voting_rounds[0]
        if not vote_round.votes or len(vote_round.votes) < 3:
            return None

        # Check if convergence is high but causal quality is low
        if vote_round.convergence_status:
            agreement = vote_round.convergence_status.metrics.agreement_level
            causal_quality = vote_round.convergence_status.metrics.avg_causal_quality

            if agreement > 0.8 and causal_quality < 0.6:
                # High agreement but low causal quality = possible conformity
                return DetectedPatternV1(
                    pattern_type="conformity",
                    affected_users=[],  # Can't identify specific users
                    confidence=0.6,
                    evidence=[
                        f"High agreement ({agreement:.2f}) despite low causal quality ({causal_quality:.2f})",
                        "Possible conformity pressure or groupthink",
                    ],
                )

        return None

    def _detect_withholding(
        self,
        session: DeliberationSessionV1,
    ) -> Optional[DetectedPatternV1]:
        """Detect information withholding (strategic silence).

        Args:
            session: Deliberation session

        Returns:
            Detected pattern or None
        """
        if not session.rounds:
            return None

        submission_rounds = [r for r in session.rounds if r.round_type == "submission"]
        if not submission_rounds:
            return None

        # Check for unusually short submissions
        withholders = []
        for round_obj in submission_rounds:
            if not round_obj.submissions:
                continue

            avg_length = sum(len(s.reasoning) for s in round_obj.submissions) / len(round_obj.submissions)

            for sub in round_obj.submissions:
                if len(sub.reasoning) < avg_length * 0.5:  # Less than 50% of average
                    withholders.append(sub.user_id)

        if len(set(withholders)) >= 2:  # At least 2 users withholding
            return DetectedPatternV1(
                pattern_type="withholding",
                affected_users=list(set(withholders)),
                confidence=0.5,
                evidence=[
                    f"{len(set(withholders))} users provided minimal reasoning",
                    "Shorter responses than session average",
                ],
            )

        return None

    def _detect_strategic_voting(
        self,
        session: DeliberationSessionV1,
    ) -> Optional[DetectedPatternV1]:
        """Detect strategic voting patterns.

        Args:
            session: Deliberation session

        Returns:
            Detected pattern or None
        """
        # Simplified: check if any user consistently votes for their own option first
        # In full implementation, would analyze voting patterns across rounds

        voting_rounds = [r for r in session.rounds if r.round_type == "voting"]
        if not voting_rounds or not voting_rounds[0].votes:
            return None

        # This is a simplified placeholder
        # Real implementation would track:
        # - Users who always rank their own proposal first
        # - Strategic ranking to eliminate competitors
        # - Coordination between users

        return None

    def _generate_mitigations(
        self,
        patterns: List[DetectedPatternV1],
    ) -> List[MitigationActionV1]:
        """Generate mitigation actions for detected patterns.

        Args:
            patterns: Detected patterns

        Returns:
            List of mitigation actions
        """
        mitigations = []

        for pattern in patterns:
            if pattern.pattern_type == "anchoring":
                mitigations.append(MitigationActionV1(
                    pattern_type="anchoring",
                    action="Randomize submission order display",
                    effectiveness=0.7,
                ))

            elif pattern.pattern_type == "conformity":
                mitigations.append(MitigationActionV1(
                    pattern_type="conformity",
                    action="Emphasize minority positions in synthesis",
                    effectiveness=0.6,
                ))

            elif pattern.pattern_type == "withholding":
                mitigations.append(MitigationActionV1(
                    pattern_type="withholding",
                    action="Prompt for additional reasoning from affected users",
                    effectiveness=0.5,
                ))

        return mitigations

    # ========================================================================
    # TEAM SIZE ANALYSIS
    # ========================================================================

    def analyze_team_size(
        self,
        session: DeliberationSessionV1,
        decision_type: str = "feature_decision",
    ) -> TeamSizeAnalysisV1:
        """Analyze team size optimality using Navajas thresholds.

        Args:
            session: Deliberation session
            decision_type: Type of decision

        Returns:
            Team size analysis
        """
        current_size = len(session.participants)

        # Measure perspective diversity
        diversity = self._measure_diversity(session)

        # Estimate coordination cost
        coordination = self._estimate_coordination_cost(session)

        # Compute collective accuracy potential
        accuracy = self._compute_collective_accuracy(current_size, diversity)

        analysis = TeamSizeAnalysisDetailsV1(
            diversity_score=diversity,
            coordination_cost=coordination,
            collective_accuracy=accuracy,
        )

        # Navajas finding: 3-5 people optimal for most decisions
        if current_size < 3:
            recommendation = "add_members"
            reasoning = "Below minimum for collective intelligence benefits (Navajas threshold: 3-5)"

        elif current_size > 7 and diversity < 0.6:
            recommendation = "run_smaller_groups"
            reasoning = "Large group with low diversity - split into subgroups of 3-5"

        elif 3 <= current_size <= 5 and diversity > 0.7:
            recommendation = "optimal"
            reasoning = "Sweet spot: high diversity, manageable coordination (Navajas optimal range)"

        elif current_size > 10:
            recommendation = "reduce_size"
            reasoning = "Large groups add noise faster than signal - consider 3-5 person core team"

        else:
            recommendation = "optimal"
            reasoning = "Team size within acceptable range"

        return TeamSizeAnalysisV1(
            decision_type=decision_type,
            current_team_size=current_size,
            optimal_range={"min": 3, "max": 5},
            analysis=analysis,
            recommendation=recommendation,
            reasoning=reasoning,
        )

    def _measure_diversity(self, session: DeliberationSessionV1) -> float:
        """Measure perspective diversity in session.

        Args:
            session: Deliberation session

        Returns:
            Diversity score (0-1)
        """
        if not session.rounds or not session.rounds[0].submissions:
            return 0.5  # Neutral if no data

        submissions = session.rounds[0].submissions

        # Measure diversity by checking graph structure variance
        unique_structures = set()
        for sub in submissions:
            # Create fingerprint of graph structure
            edges = tuple(sorted((e["source"], e["target"]) for e in sub.graph.edges))
            unique_structures.add(edges)

        # Diversity = ratio of unique structures to total submissions
        diversity = len(unique_structures) / len(submissions) if submissions else 0.5

        return min(1.0, diversity + 0.2)  # Boost to account for reasoning diversity

    def _estimate_coordination_cost(self, session: DeliberationSessionV1) -> float:
        """Estimate coordination cost based on team size and rounds.

        Args:
            session: Deliberation session

        Returns:
            Coordination cost (time in arbitrary units)
        """
        team_size = len(session.participants)
        num_rounds = len(session.rounds)

        # O(n^2) coordination cost with team size
        base_cost = (team_size ** 2) / 10.0

        # Additional cost per round
        round_cost = num_rounds * 0.5

        return base_cost + round_cost

    def _compute_collective_accuracy(
        self,
        team_size: int,
        diversity: float,
    ) -> float:
        """Compute expected collective accuracy.

        Args:
            team_size: Team size
            diversity: Diversity score

        Returns:
            Expected collective accuracy (0-1)
        """
        # Navajas finding: accuracy improves with diversity up to ~5 people
        if team_size <= 5:
            accuracy = min(0.9, 0.5 + (team_size / 10.0) + (diversity * 0.3))
        else:
            # Diminishing returns after 5
            accuracy = min(0.9, 0.7 + (diversity * 0.2) - ((team_size - 5) * 0.02))

        return max(0.3, accuracy)

    # ========================================================================
    # COMMUNICATION PATTERN ANALYSIS
    # ========================================================================

    def analyze_communication_patterns(
        self,
        session: DeliberationSessionV1,
    ) -> CommunicationAnalysisV1:
        """Analyze communication patterns for optimal structure.

        Args:
            session: Deliberation session

        Returns:
            Communication analysis
        """
        diversity = self._measure_diversity(session)

        # Analyze impact of different communication modes
        patterns = []

        # Public debate pattern
        patterns.append(CommunicationPatternV1(
            interaction_type="public_debate",
            accuracy_impact=0.3 if diversity > 0.7 else -0.1,
            confidence_impact=0.2 if diversity > 0.7 else -0.2,
            convergence_impact=-0.1,  # Slows convergence
        ))

        # Private submission pattern
        patterns.append(CommunicationPatternV1(
            interaction_type="private_submission",
            accuracy_impact=0.2,
            confidence_impact=-0.1,
            convergence_impact=0.2,  # Faster convergence
        ))

        # Anonymous voting pattern
        patterns.append(CommunicationPatternV1(
            interaction_type="anonymous_voting",
            accuracy_impact=0.3,
            confidence_impact=0.0,
            convergence_impact=0.3,  # Much faster
        ))

        # Generate recommendation
        if diversity > 0.7:
            optimal = "sequential_revelation"
            reasoning = "High diversity - public debate beneficial after private submission"
        else:
            optimal = "anonymous_first"
            reasoning = "Low diversity or conformity risk - collect inputs privately, then vote anonymously"

        return CommunicationAnalysisV1(
            session_id=session.session_id,
            patterns=patterns,
            recommendation={
                "optimal_structure": optimal,
                "reasoning": reasoning,
            },
        )

    # ========================================================================
    # SMART WEIGHTING
    # ========================================================================

    def compute_smart_weights(
        self,
        session: DeliberationSessionV1,
        causal_weights: Dict[str, float],
        value_weights: Dict[str, float],
        strategy_detection: StrategyDetectionV1,
    ) -> List[RecommendedWeightV1]:
        """Compute smart aggregation weights combining all factors.

        Args:
            session: Deliberation session
            causal_weights: Causal quality weights
            value_weights: Value alignment weights
            strategy_detection: Strategic behavior detection results

        Returns:
            List of recommended weights
        """
        recommended = []

        for participant in session.participants:
            user_id = participant.user_id

            # Get component weights
            causal_w = causal_weights.get(user_id, 0.5)
            value_w = value_weights.get(user_id, 0.5)

            # Calibrate confidence
            calibration = self.calibrate_confidence(user_id, 0.8, "general")
            confidence_w = calibration.calibrated_confidence

            # Compute strategy penalty
            strategy_penalty = self._compute_strategy_penalty(
                user_id,
                strategy_detection,
            )

            # Combine weights
            final_weight = (
                causal_w * 0.4 +
                value_w * 0.3 +
                confidence_w * 0.3 -
                strategy_penalty * 0.1
            )
            final_weight = max(0.0, min(1.0, final_weight))

            breakdown = WeightBreakdownV1(
                causal_quality=causal_w,
                value_alignment=value_w,
                calibrated_confidence=confidence_w,
                strategy_penalty=strategy_penalty,
            )

            recommended.append(RecommendedWeightV1(
                user_id=user_id,
                final_weight=final_weight,
                weight_breakdown=breakdown,
            ))

        return recommended

    def _compute_strategy_penalty(
        self,
        user_id: str,
        strategy_detection: StrategyDetectionV1,
    ) -> float:
        """Compute penalty for strategic behavior.

        Args:
            user_id: User ID
            strategy_detection: Strategy detection results

        Returns:
            Penalty score (0-1, higher = more penalty)
        """
        penalty = 0.0

        for pattern in strategy_detection.detected_patterns:
            if user_id in pattern.affected_users:
                # Add penalty based on pattern type and confidence
                if pattern.pattern_type == "strategic_voting":
                    penalty += pattern.confidence * 0.5
                elif pattern.pattern_type == "withholding":
                    penalty += pattern.confidence * 0.3
                else:
                    penalty += pattern.confidence * 0.2

        return min(1.0, penalty)

    def compute_aggregation_quality(
        self,
        session: DeliberationSessionV1,
        diversity: float,
    ) -> AggregationQualityV1:
        """Compute quality metrics for aggregated result.

        Args:
            session: Deliberation session
            diversity: Diversity score

        Returns:
            Aggregation quality metrics
        """
        team_size = len(session.participants)

        # Collective intelligence score (Navajas formula approximation)
        if 3 <= team_size <= 5:
            ci_score = min(0.95, 0.6 + diversity * 0.3 + 0.1)
        else:
            ci_score = min(0.85, 0.5 + diversity * 0.25)

        # Diversity bonus
        diversity_bonus = diversity * 0.3

        # Coordination cost
        coordination_cost = self._estimate_coordination_cost(session)

        return AggregationQualityV1(
            collective_intelligence_score=ci_score,
            diversity_bonus=diversity_bonus,
            coordination_cost=coordination_cost,
        )
