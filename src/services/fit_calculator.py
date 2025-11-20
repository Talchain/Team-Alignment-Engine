"""Fit calculation service."""

import logging
from typing import List, Dict
from uuid import UUID

from src.models import (
    StakeholderProfile,
    ProposedOption,
    StakeholderFitScore,
    OptionFit,
    FitLevel,
    ConsensusLevel,
)

logger = logging.getLogger(__name__)


class FitCalculator:
    """Service for calculating option fit scores."""

    def __init__(self):
        """Initialize fit calculator."""
        # In-memory storage for now
        self.fits: Dict[UUID, OptionFit] = {}

    async def calculate_all_fits(
        self, option: ProposedOption, profiles: List[StakeholderProfile]
    ) -> OptionFit:
        """
        Calculate fit scores for option against all profiles.

        Args:
            option: Proposed option
            profiles: List of stakeholder profiles

        Returns:
            Option fit with all stakeholder scores
        """
        stakeholder_fits = {}

        for profile in profiles:
            fit_score = await self.calculate_fit(profile, option)
            stakeholder_fits[str(profile.user_id)] = fit_score

        # Calculate overall alignment
        if stakeholder_fits:
            overall_alignment = sum(
                fit.fit_score for fit in stakeholder_fits.values()
            ) / len(stakeholder_fits)
        else:
            overall_alignment = 0.0

        # Determine consensus level
        consensus_level = self._determine_consensus_level(stakeholder_fits)

        option_fit = OptionFit(
            option_id=option.option_id,
            stakeholder_fits=stakeholder_fits,
            overall_alignment=overall_alignment,
            consensus_level=consensus_level,
        )

        self.fits[option_fit.fit_id] = option_fit

        logger.info(
            "Fit calculated",
            extra={
                "option_id": str(option.option_id),
                "overall_alignment": overall_alignment,
                "consensus_level": consensus_level,
            },
        )

        return option_fit

    async def calculate_fit(
        self, profile: StakeholderProfile, option: ProposedOption
    ) -> StakeholderFitScore:
        """
        Calculate fit score for single stakeholder.

        Args:
            profile: Stakeholder profile
            option: Proposed option

        Returns:
            Fit score with explanation
        """
        # Base score from goal alignment
        goal_score = self._calculate_goal_alignment(profile, option)

        # Check constraint violations
        violations = self._check_constraint_violations(profile, option)

        # Penalty for violations
        violation_penalty = 0.3 * len(violations)
        fit_score = max(0.0, goal_score - violation_penalty)

        # Determine fit level
        fit_level = self._determine_fit_level(fit_score)

        # Goals satisfied
        satisfies_goals = [
            goal for goal in option.addresses_goals
            if profile.goal_weights.get(goal, 0) > 0.5
        ]

        # Generate explanation
        explanation = self._generate_explanation(
            fit_score, satisfies_goals, violations
        )

        return StakeholderFitScore(
            stakeholder_id=profile.user_id,
            fit_score=fit_score,
            fit_level=fit_level,
            satisfies_goals=satisfies_goals,
            violates_constraints=violations,
            explanation=explanation,
        )

    def _calculate_goal_alignment(
        self, profile: StakeholderProfile, option: ProposedOption
    ) -> float:
        """Calculate goal alignment score."""
        if not option.addresses_goals:
            return 0.0

        # Weight by profile's goal priorities
        total_weight = 0.0
        aligned_weight = 0.0

        for goal, weight in profile.goal_weights.items():
            total_weight += weight
            if goal in option.addresses_goals:
                aligned_weight += weight

        if total_weight == 0:
            return 0.5  # Neutral if no goals weighted

        return aligned_weight / total_weight

    def _check_constraint_violations(
        self, profile: StakeholderProfile, option: ProposedOption
    ) -> List[str]:
        """Check if option violates stakeholder constraints."""
        violations = []

        # Check must-have constraints
        for constraint in profile.must_have_constraints:
            if self._violates_constraint(constraint, option):
                violations.append(constraint)

        # Check red lines
        for red_line in profile.red_lines:
            if self._crosses_red_line(red_line, option):
                violations.append(f"RED LINE: {red_line}")

        return violations

    def _violates_constraint(self, constraint: str, option: ProposedOption) -> bool:
        """Check if option violates a constraint."""
        # Simple keyword matching (in production, use NLP)
        constraint_lower = constraint.lower()
        option_text = (
            option.description.lower() + " " + option.expected_outcome.lower()
        )

        # Check for timeline constraints
        if "month" in constraint_lower or "week" in constraint_lower:
            # Extract numbers and compare (simplified)
            if "timeline" in option_text:
                return True  # Placeholder

        return False

    def _crosses_red_line(self, red_line: str, option: ProposedOption) -> bool:
        """Check if option crosses a red line."""
        # Similar to constraint checking but stricter
        red_line_lower = red_line.lower()
        option_text = option.description.lower()

        # Check for explicit mentions
        keywords = red_line_lower.split()
        matches = sum(1 for keyword in keywords if keyword in option_text)

        return matches >= len(keywords) / 2  # >50% keyword match

    def _determine_fit_level(self, fit_score: float) -> FitLevel:
        """Determine fit level category."""
        if fit_score >= 0.7:
            return FitLevel.STRONG
        elif fit_score >= 0.4:
            return FitLevel.MODERATE
        else:
            return FitLevel.POOR

    def _determine_consensus_level(
        self, stakeholder_fits: Dict[str, StakeholderFitScore]
    ) -> ConsensusLevel:
        """Determine consensus level from stakeholder fits."""
        if not stakeholder_fits:
            return ConsensusLevel.NONE

        scores = [fit.fit_score for fit in stakeholder_fits.values()]
        avg_score = sum(scores) / len(scores)

        if avg_score >= 0.8:
            return ConsensusLevel.STRONG
        elif avg_score >= 0.6:
            return ConsensusLevel.MODERATE
        elif avg_score >= 0.4:
            return ConsensusLevel.WEAK
        else:
            return ConsensusLevel.NONE

    def _generate_explanation(
        self, fit_score: float, satisfies_goals: List[str], violations: List[str]
    ) -> str:
        """Generate human-readable explanation."""
        if fit_score >= 0.7:
            explanation = f"Strong fit: addresses {len(satisfies_goals)} key goals"
        elif fit_score >= 0.4:
            explanation = f"Moderate fit: addresses {len(satisfies_goals)} goals"
        else:
            explanation = f"Poor fit: only addresses {len(satisfies_goals)} goals"

        if violations:
            explanation += f", but violates {len(violations)} constraints"

        return explanation

    async def get_by_option(self, option_id: UUID) -> OptionFit:
        """Get fit analysis for an option."""
        for fit in self.fits.values():
            if fit.option_id == option_id:
                return fit
        return None

    async def calculate_consensus_strength(
        self, stakeholder_support: Dict[str, str]
    ) -> float:
        """Calculate consensus strength from support levels."""
        support_scores = {
            "strong": 1.0,
            "moderate": 0.7,
            "weak": 0.4,
            "none": 0.0,
        }

        if not stakeholder_support:
            return 0.0

        scores = [
            support_scores.get(level.lower(), 0.5)
            for level in stakeholder_support.values()
        ]

        return sum(scores) / len(scores)
