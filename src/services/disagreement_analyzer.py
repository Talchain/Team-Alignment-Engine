"""Disagreement analysis service."""

import logging
from typing import List, Dict, Any
import numpy as np

from src.models import StakeholderProfile, SharedGround, DisagreementMap
from src.clients import CEEClient

logger = logging.getLogger(__name__)


class DisagreementAnalyzer:
    """Service for analyzing stakeholder disagreements."""

    def __init__(self, cee_client: CEEClient = None):
        """Initialize disagreement analyzer."""
        self.cee_client = cee_client or CEEClient()

    async def find_common_ground(
        self, profiles: List[StakeholderProfile], decision_context: str
    ) -> SharedGround:
        """
        Identify shared ground among stakeholders.

        Args:
            profiles: List of stakeholder profiles
            decision_context: Decision context

        Returns:
            Shared ground analysis
        """
        if not profiles:
            return SharedGround(
                session_id=profiles[0].session_id if profiles else None,
                common_goals=[],
                common_concerns=[],
                summary="No profiles available",
            )

        session_id = profiles[0].session_id

        # Find common goals (high agreement)
        common_goals = self._identify_common_goals(profiles)

        # Find common concerns
        common_concerns = self._identify_common_concerns(profiles)

        # Generate summary via CEE
        try:
            summary_result = await self.cee_client.generate_shared_ground_summary(
                profiles=[p.dict() for p in profiles],
                decision_context=decision_context,
            )
            summary = summary_result.get("summary", "")
        except Exception as e:
            logger.warning(f"CEE summary generation failed: {e}")
            summary = self._generate_summary_heuristic(common_goals, common_concerns)

        return SharedGround(
            session_id=session_id,
            common_goals=common_goals,
            common_concerns=common_concerns,
            summary=summary,
        )

    async def map_tensions(
        self, profiles: List[StakeholderProfile], decision_context: str
    ) -> DisagreementMap:
        """
        Map disagreement tensions among stakeholders.

        Args:
            profiles: List of stakeholder profiles
            decision_context: Decision context

        Returns:
            Disagreement map analysis
        """
        if not profiles:
            return DisagreementMap(
                session_id=profiles[0].session_id if profiles else None,
                primary_tensions=[],
                secondary_differences=[],
                summary="No profiles available",
            )

        session_id = profiles[0].session_id

        # Identify primary tensions (conflicting priorities)
        primary_tensions = self._identify_tensions(profiles)

        # Identify secondary differences
        secondary_differences = self._identify_secondary_differences(profiles)

        # Generate summary via CEE
        try:
            summary_result = await self.cee_client.generate_disagreement_summary(
                profiles=[p.dict() for p in profiles],
                decision_context=decision_context,
            )
            summary = summary_result.get("summary", "")
        except Exception as e:
            logger.warning(f"CEE summary generation failed: {e}")
            summary = self._generate_tension_summary_heuristic(primary_tensions)

        return DisagreementMap(
            session_id=session_id,
            primary_tensions=primary_tensions,
            secondary_differences=secondary_differences,
            summary=summary,
        )

    def _identify_common_goals(
        self, profiles: List[StakeholderProfile]
    ) -> List[Dict[str, Any]]:
        """Identify goals with high agreement."""
        if not profiles:
            return []

        # Get all goal dimensions
        all_goals = set()
        for profile in profiles:
            all_goals.update(profile.goal_weights.keys())

        common_goals = []
        for goal in all_goals:
            # Get weights for this goal across all profiles
            weights = [
                profile.goal_weights.get(goal, 0) for profile in profiles
            ]

            # Calculate mean and variance
            mean_weight = np.mean(weights)
            variance = np.var(weights)

            # High agreement: high mean, low variance
            agreement_score = mean_weight * (1 - variance)

            if agreement_score > 0.5:  # Threshold for "common"
                common_goals.append({
                    "goal": goal,
                    "agreement_score": float(agreement_score),
                    "stakeholder_weights": {
                        str(profile.user_id): profile.goal_weights.get(goal, 0)
                        for profile in profiles
                    },
                })

        return sorted(common_goals, key=lambda x: x["agreement_score"], reverse=True)

    def _identify_common_concerns(
        self, profiles: List[StakeholderProfile]
    ) -> List[str]:
        """Identify concerns mentioned by multiple stakeholders."""
        # Count concern keywords
        concern_counts = {}
        for profile in profiles:
            for concern in profile.key_concerns:
                # Simple keyword matching (in production, use NLP)
                concern_lower = concern.lower()
                for keyword in concern_lower.split():
                    concern_counts[keyword] = concern_counts.get(keyword, 0) + 1

        # Find concerns mentioned by >50% of stakeholders
        threshold = len(profiles) / 2
        common = [
            keyword
            for keyword, count in concern_counts.items()
            if count >= threshold and len(keyword) > 3  # Filter short words
        ]

        return common[:5]  # Top 5

    def _identify_tensions(
        self, profiles: List[StakeholderProfile]
    ) -> List[Dict[str, Any]]:
        """Identify conflicting goal priorities."""
        if len(profiles) < 2:
            return []

        # Get all goal pairs
        all_goals = set()
        for profile in profiles:
            all_goals.update(profile.goal_weights.keys())

        tensions = []
        goals_list = list(all_goals)

        for i in range(len(goals_list)):
            for j in range(i + 1, len(goals_list)):
                goal1, goal2 = goals_list[i], goals_list[j]

                # Check if stakeholders prioritize these differently
                tension_score = self._calculate_tension(profiles, goal1, goal2)

                if tension_score > 0.5:  # Significant tension
                    positions = self._get_stakeholder_positions(
                        profiles, goal1, goal2
                    )
                    tensions.append({
                        "dimension_pair": (goal1, goal2),
                        "tension_score": float(tension_score),
                        "positions": positions,
                    })

        return sorted(tensions, key=lambda x: x["tension_score"], reverse=True)[:3]

    def _calculate_tension(
        self, profiles: List[StakeholderProfile], goal1: str, goal2: str
    ) -> float:
        """Calculate tension between two goals."""
        # Get weights for both goals
        weights1 = [profile.goal_weights.get(goal1, 0) for profile in profiles]
        weights2 = [profile.goal_weights.get(goal2, 0) for profile in profiles]

        # Check for inverse correlation (one high when other low)
        correlation = np.corrcoef(weights1, weights2)[0, 1]

        # High tension = strong negative correlation
        if correlation < 0:
            return abs(correlation)
        return 0.0

    def _get_stakeholder_positions(
        self, profiles: List[StakeholderProfile], goal1: str, goal2: str
    ) -> List[Dict[str, Any]]:
        """Get stakeholder positions on goal pair."""
        positions = []
        for profile in profiles:
            w1 = profile.goal_weights.get(goal1, 0)
            w2 = profile.goal_weights.get(goal2, 0)
            positions.append({
                "stakeholder_id": str(profile.user_id),
                "role": profile.role,
                goal1: w1,
                goal2: w2,
                "favors": goal1 if w1 > w2 else goal2,
            })
        return positions

    def _identify_secondary_differences(
        self, profiles: List[StakeholderProfile]
    ) -> List[Dict[str, Any]]:
        """Identify secondary differences (risk tolerance, time horizon, etc.)."""
        differences = []

        # Risk tolerance differences
        risk_levels = [profile.risk_tolerance for profile in profiles]
        if len(set(risk_levels)) > 1:
            differences.append({
                "dimension": "risk_tolerance",
                "values": {
                    str(profile.user_id): profile.risk_tolerance
                    for profile in profiles
                },
            })

        # Time horizon differences
        time_horizons = [profile.time_horizon for profile in profiles]
        if len(set(time_horizons)) > 1:
            differences.append({
                "dimension": "time_horizon",
                "values": {
                    str(profile.user_id): profile.time_horizon
                    for profile in profiles
                },
            })

        return differences

    def _generate_summary_heuristic(
        self, common_goals: List[Dict], common_concerns: List[str]
    ) -> str:
        """Generate summary without CEE."""
        if not common_goals:
            return "No significant common ground found."

        top_goals = [g["goal"] for g in common_goals[:3]]
        summary = f"Team aligns on: {', '.join(top_goals)}."

        if common_concerns:
            summary += f" Shared concerns: {', '.join(common_concerns[:3])}."

        return summary

    def _generate_tension_summary_heuristic(
        self, tensions: List[Dict]
    ) -> str:
        """Generate tension summary without CEE."""
        if not tensions:
            return "No significant disagreements detected."

        top_tension = tensions[0]
        goal1, goal2 = top_tension["dimension_pair"]
        return f"Primary tension: {goal1} vs {goal2}."
