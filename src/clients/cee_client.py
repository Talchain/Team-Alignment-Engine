"""CEE (Cognitive Enhancement Engine) client integration.

TAE NEVER calls LLMs directly. All LLM work goes through CEE.
"""

import httpx
import logging
from typing import Dict, List, Any, Optional

from src.config import settings

logger = logging.getLogger(__name__)


class CEEClient:
    """Client for CEE service integration.

    Usage:
        async with CEEClient() as client:
            profile = await client.extract_profile(...)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize CEE client."""
        self.base_url = base_url or settings.cee_base_url
        self.api_key = api_key or settings.cee_api_key
        self.timeout = timeout or settings.cee_timeout
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Enter async context manager - create HTTP client."""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager - close HTTP client."""
        if self.client:
            await self.client.aclose()
        return False

    async def extract_profile(
        self,
        user_input: Dict[str, Any],
        role: str,
        decision_context: str,
        goal_dimensions: List[str],
        seed: str,
    ) -> Dict[str, Any]:
        """
        Extract structured profile from free-text input.

        Endpoint: POST /assist/v1/extract-profile

        Args:
            user_input: Raw user input dict
            role: Stakeholder role (PM, Designer, etc.)
            decision_context: Context of the decision
            goal_dimensions: List of goal dimensions to extract
            seed: Deterministic seed for reproducibility

        Returns:
            Extracted profile with goal_weights, risk_tolerance, etc.

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "user_input": user_input,
            "role": role,
            "decision_context": decision_context,
            "goal_dimensions": goal_dimensions,
            "seed": seed,
        }

        logger.info(
            "Extracting profile via CEE",
            extra={"role": role, "seed": seed, "dimensions": len(goal_dimensions)},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/extract-profile",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "X-Request-ID": f"tae-profile-{seed}",
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            result = response.json()

            logger.info(
                "Profile extraction successful",
                extra={"seed": seed, "confidence": result.get("confidence", 1.0)},
            )

            return result

        except httpx.HTTPError as e:
            logger.error(
                "CEE profile extraction failed",
                extra={"error": str(e), "seed": seed},
                exc_info=True,
            )
            raise

    async def explain_validation(
        self,
        option: Dict[str, Any],
        validation_result: Dict[str, Any],
        audience_role: str,
        tier: int = 1,
    ) -> Dict[str, Any]:
        """
        Generate plain-English explanation of ISL validation.

        Endpoint: POST /assist/v1/explain-validation

        Args:
            option: Option dict
            validation_result: ISL validation result
            audience_role: Role of the audience (PM, Designer, etc.)
            tier: Explanation tier (1=summary, 2=detailed, 3=expert)

        Returns:
            Plain-English explanation

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "option": option,
            "validation_result": validation_result,
            "audience_role": audience_role,
            "explanation_tier": tier,
        }

        logger.info(
            "Requesting validation explanation from CEE",
            extra={"option_id": option.get("option_id"), "tier": tier},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/explain-validation",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "CEE validation explanation failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def generate_shared_ground_summary(
        self, profiles: List[Dict[str, Any]], decision_context: str
    ) -> Dict[str, Any]:
        """
        Generate plain-English summary of common ground.

        Endpoint: POST /assist/v1/summarize-alignment

        Args:
            profiles: List of stakeholder profiles
            decision_context: Context of the decision

        Returns:
            Summary of shared ground

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "profiles": profiles,
            "decision_context": decision_context,
            "summary_type": "shared_ground",
        }

        logger.info(
            "Requesting shared ground summary from CEE",
            extra={"num_profiles": len(profiles)},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/summarize-alignment",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "CEE shared ground summary failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def generate_disagreement_summary(
        self, profiles: List[Dict[str, Any]], decision_context: str
    ) -> Dict[str, Any]:
        """
        Generate plain-English summary of disagreements.

        Endpoint: POST /assist/v1/summarize-alignment

        Args:
            profiles: List of stakeholder profiles
            decision_context: Context of the decision

        Returns:
            Summary of disagreements

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "profiles": profiles,
            "decision_context": decision_context,
            "summary_type": "disagreement",
        }

        logger.info(
            "Requesting disagreement summary from CEE",
            extra={"num_profiles": len(profiles)},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/summarize-alignment",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "CEE disagreement summary failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def generate_options(
        self,
        profiles: List[Dict[str, Any]],
        decision_context: str,
        disagreement_map: Dict[str, Any],
        generation_mode: str,
        num_options: int = 3,
        seed: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate creative options using AI (Phase C: C1).

        Endpoint: POST /assist/v1/generate-options

        Args:
            profiles: List of stakeholder profiles
            decision_context: Context of the decision
            disagreement_map: Map of disagreements to address
            generation_mode: "creative_synthesis" or "constraint_satisfaction"
            num_options: Number of options to generate (default 3)
            seed: Optional seed for determinism

        Returns:
            Generated options with metadata

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "profiles": profiles,
            "decision_context": decision_context,
            "disagreement_map": disagreement_map,
            "generation_mode": generation_mode,
            "num_options": num_options,
            "seed": seed,
        }

        logger.info(
            "Requesting AI option generation from CEE",
            extra={"mode": generation_mode, "num_options": num_options},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/generate-options",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "CEE option generation failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def synthesize_options(
        self,
        source_options: List[Dict[str, Any]],
        decision_context: str,
        profiles: List[Dict[str, Any]],
        synthesis_goal: str,
    ) -> Dict[str, Any]:
        """
        Synthesize hybrid options from multiple source options (Phase C: C2).

        Endpoint: POST /assist/v1/synthesize-options

        Args:
            source_options: Options to combine
            decision_context: Context of the decision
            profiles: Stakeholder profiles
            synthesis_goal: What to optimize for in synthesis

        Returns:
            Synthesized hybrid option with metadata

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "source_options": source_options,
            "decision_context": decision_context,
            "profiles": profiles,
            "synthesis_goal": synthesis_goal,
        }

        logger.info(
            "Requesting option synthesis from CEE",
            extra={"num_sources": len(source_options), "goal": synthesis_goal},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/synthesize-options",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "CEE option synthesis failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def tune_option(
        self,
        option: Dict[str, Any],
        concern: Dict[str, Any],
        profiles: List[Dict[str, Any]],
        decision_context: str,
        preserve_elements: List[str],
    ) -> Dict[str, Any]:
        """
        Tune an option to address a minority concern (Phase C: C3).

        Endpoint: POST /assist/v1/tune-option

        Args:
            option: Option to tune
            concern: Minority concern to address
            profiles: All stakeholder profiles
            decision_context: Context of the decision
            preserve_elements: Elements that must be preserved

        Returns:
            Tuned option with metadata

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "option": option,
            "concern": concern,
            "profiles": profiles,
            "decision_context": decision_context,
            "preserve_elements": preserve_elements,
        }

        logger.info(
            "Requesting option tuning from CEE",
            extra={"option_id": option.get("option_id"), "concern_id": concern.get("concern_id")},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/tune-option",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "CEE option tuning failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def recommend_test_strategy(
        self,
        assumptions: List[Dict[str, Any]],
        option: Dict[str, Any],
        decision_context: str,
        time_to_decision: int,
        available_resources: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Recommend testing strategy for assumptions (Phase C: C4).

        Endpoint: POST /assist/v1/recommend-test-strategy

        Args:
            assumptions: List of assumptions to test
            option: Option these assumptions support
            decision_context: Context of the decision
            time_to_decision: Days until decision needed
            available_resources: Optional resource constraints

        Returns:
            Recommended test strategies for top assumptions

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "assumptions": assumptions,
            "option": option,
            "decision_context": decision_context,
            "time_to_decision": time_to_decision,
            "available_resources": available_resources,
        }

        logger.info(
            "Requesting test strategy recommendations from CEE",
            extra={"num_assumptions": len(assumptions), "days_to_decision": time_to_decision},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/recommend-test-strategy",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "CEE test strategy recommendation failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def generate_lessons_learned(
        self,
        decision_brief: Dict[str, Any],
        actual_outcomes: Dict[str, float],
        assumption_validations: List[Dict[str, Any]],
        decision_context: str,
    ) -> Dict[str, Any]:
        """
        Generate lessons learned from decision retrospective (Phase C: C5).

        Endpoint: POST /assist/v1/generate-lessons-learned

        Args:
            decision_brief: Original decision brief
            actual_outcomes: Actual measured outcomes
            assumption_validations: Results of assumption testing
            decision_context: Context of the decision

        Returns:
            Lessons learned with narrative and recommendations

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "decision_brief": decision_brief,
            "actual_outcomes": actual_outcomes,
            "assumption_validations": assumption_validations,
            "decision_context": decision_context,
        }

        logger.info(
            "Requesting lessons learned generation from CEE",
            extra={"brief_id": decision_brief.get("brief_id")},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/generate-lessons-learned",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "CEE lessons learned generation failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def generate_org_recommendations(
        self,
        retrospectives: List[Dict[str, Any]],
        team_id: str,
    ) -> Dict[str, Any]:
        """
        Generate organizational recommendations from multiple retrospectives (Phase C: C5).

        Endpoint: POST /assist/v1/generate-org-recommendations

        Args:
            retrospectives: List of decision retrospectives
            team_id: Team identifier

        Returns:
            Organizational recommendations and patterns

        Raises:
            httpx.HTTPError: If CEE request fails
        """
        request_payload = {
            "retrospectives": retrospectives,
            "team_id": team_id,
        }

        logger.info(
            "Requesting org recommendations from CEE",
            extra={"team_id": team_id, "num_retrospectives": len(retrospectives)},
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/assist/v1/generate-org-recommendations",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "CEE org recommendations generation failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
