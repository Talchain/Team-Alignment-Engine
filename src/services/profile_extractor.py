"""Profile extraction service."""

import logging
from typing import Dict, Any, Optional
from uuid import UUID

from src.models import StakeholderProfile, StakeholderRole, RiskLevel, TimeHorizon
from src.clients import CEEClient

logger = logging.getLogger(__name__)


class ProfileExtractor:
    """Service for extracting stakeholder profiles."""

    def __init__(self, cee_client: Optional[CEEClient] = None):
        """Initialize profile extractor."""
        self.cee_client = cee_client or CEEClient()
        # In-memory storage for now (would use database in production)
        self.profiles: Dict[UUID, StakeholderProfile] = {}

    async def create(
        self,
        session_id: UUID,
        user_id: UUID,
        role: str,
        stakeholder_role: StakeholderRole,
        desired_outcome: str,
        key_concerns: list,
        preferred_option: Optional[str],
        goal_dimensions: list,
        decision_context: str,
    ) -> StakeholderProfile:
        """
        Create stakeholder profile with CEE extraction.

        Args:
            session_id: Session identifier
            user_id: User identifier
            role: Stakeholder role (PM, Designer, etc.)
            stakeholder_role: Permission level role
            desired_outcome: Desired outcome text
            key_concerns: List of concerns
            preferred_option: Optional preferred option
            goal_dimensions: Goal dimensions to extract
            decision_context: Decision context

        Returns:
            Created stakeholder profile
        """
        # Build user input for CEE
        user_input = {
            "desired_outcome": desired_outcome,
            "key_concerns": key_concerns,
            "preferred_option": preferred_option,
        }

        # Seed for deterministic extraction
        seed = f"{session_id}:{user_id}"

        # Try CEE extraction
        try:
            extracted = await self.cee_client.extract_profile(
                user_input=user_input,
                role=role,
                decision_context=decision_context,
                goal_dimensions=goal_dimensions,
                seed=seed,
            )

            goal_weights = extracted.get("goal_weights", {})
            risk_tolerance = RiskLevel(extracted.get("risk_tolerance", "moderate"))
            time_horizon = TimeHorizon(extracted.get("time_horizon", "quarterly"))
            must_have_constraints = extracted.get("must_have_constraints", [])
            red_lines = extracted.get("red_lines", [])
            extraction_confidence = extracted.get("confidence", 1.0)
            extraction_source = "cee"

            logger.info(
                "Profile extracted via CEE",
                extra={
                    "user_id": str(user_id),
                    "confidence": extraction_confidence,
                },
            )

        except Exception as e:
            logger.warning(
                f"CEE extraction failed, using heuristic: {e}",
                extra={"user_id": str(user_id)},
            )

            # Graceful degradation - heuristic extraction
            extraction = self._extract_profile_heuristic(
                desired_outcome, key_concerns, goal_dimensions
            )
            goal_weights = extraction["goal_weights"]
            risk_tolerance = extraction["risk_tolerance"]
            time_horizon = extraction["time_horizon"]
            must_have_constraints = extraction["must_have_constraints"]
            red_lines = extraction["red_lines"]
            extraction_confidence = 0.5
            extraction_source = "heuristic"

        # Create profile
        profile = StakeholderProfile(
            session_id=session_id,
            user_id=user_id,
            role=role,
            stakeholder_role=stakeholder_role,
            desired_outcome=desired_outcome,
            key_concerns=key_concerns,
            preferred_option=preferred_option,
            goal_weights=goal_weights,
            risk_tolerance=risk_tolerance,
            time_horizon=time_horizon,
            must_have_constraints=must_have_constraints,
            red_lines=red_lines,
            extraction_confidence=extraction_confidence,
            extraction_source=extraction_source,
        )

        self.profiles[profile.profile_id] = profile
        return profile

    async def get(self, profile_id: UUID) -> Optional[StakeholderProfile]:
        """Get profile by ID."""
        return self.profiles.get(profile_id)

    async def get_by_user(
        self, session_id: UUID, user_id: UUID
    ) -> Optional[StakeholderProfile]:
        """Get profile by session and user."""
        for profile in self.profiles.values():
            if profile.session_id == session_id and profile.user_id == user_id:
                return profile
        return None

    async def get_all(self, session_id: UUID) -> list:
        """Get all profiles for a session."""
        return [p for p in self.profiles.values() if p.session_id == session_id]

    async def count(self, session_id: UUID) -> int:
        """Count profiles for a session."""
        return len([p for p in self.profiles.values() if p.session_id == session_id])

    async def all_collected(self, session_id: UUID, expected_count: int) -> bool:
        """Check if all profiles collected."""
        return await self.count(session_id) >= expected_count

    def _extract_profile_heuristic(
        self, desired_outcome: str, key_concerns: list, goal_dimensions: list
    ) -> Dict[str, Any]:
        """Heuristic profile extraction as fallback."""
        # Simple heuristic based on keywords
        goal_weights = {dim: 0.5 for dim in goal_dimensions}

        # Adjust weights based on keywords in desired outcome
        outcome_lower = desired_outcome.lower()
        if "revenue" in outcome_lower or "growth" in outcome_lower:
            goal_weights["revenue_growth"] = 0.8
        if "retention" in outcome_lower or "churn" in outcome_lower:
            goal_weights["customer_retention"] = 0.8
        if "quality" in outcome_lower:
            goal_weights["product_quality"] = 0.8
        if "fast" in outcome_lower or "quick" in outcome_lower:
            goal_weights["time_to_market"] = 0.9

        # Determine risk tolerance
        if "conservative" in outcome_lower or "safe" in outcome_lower:
            risk_tolerance = RiskLevel.CONSERVATIVE
        elif "aggressive" in outcome_lower or "bold" in outcome_lower:
            risk_tolerance = RiskLevel.AGGRESSIVE
        else:
            risk_tolerance = RiskLevel.MODERATE

        # Determine time horizon
        if "week" in outcome_lower:
            time_horizon = TimeHorizon.WEEKLY
        elif "month" in outcome_lower:
            time_horizon = TimeHorizon.MONTHLY
        elif "year" in outcome_lower:
            time_horizon = TimeHorizon.ANNUAL
        else:
            time_horizon = TimeHorizon.QUARTERLY

        return {
            "goal_weights": goal_weights,
            "risk_tolerance": risk_tolerance,
            "time_horizon": time_horizon,
            "must_have_constraints": key_concerns[:2],  # First 2 concerns as constraints
            "red_lines": [],
        }
