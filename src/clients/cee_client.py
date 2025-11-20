"""CEE (Cognitive Enhancement Engine) client integration.

TAE NEVER calls LLMs directly. All LLM work goes through CEE.
"""

import httpx
import logging
from typing import Dict, List, Any, Optional

from src.config import settings

logger = logging.getLogger(__name__)


class CEEClient:
    """Client for CEE service integration."""

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
        self.client = httpx.AsyncClient(timeout=self.timeout)

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

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
