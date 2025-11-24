"""ISL (Inference Service Layer) client integration.

TAE calls ISL for all causal validation.
"""

import httpx
import logging
from typing import Dict, List, Any, Optional

from src.config import settings
from src.models.enums import ValidationStatus

logger = logging.getLogger(__name__)


class ISLClient:
    """Client for ISL service integration.

    Usage:
        async with ISLClient() as client:
            validation = await client.validate_option(...)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize ISL client."""
        self.base_url = base_url or settings.isl_base_url
        self.api_key = api_key or settings.isl_api_key
        self.timeout = timeout or settings.isl_timeout
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

    async def validate_option(
        self,
        option: Dict[str, Any],
        outcome_metrics: List[str],
        time_horizon: str,
    ) -> Dict[str, Any]:
        """
        Validate option causally with ISL.

        Endpoint: POST /api/v1/causal/validate

        Returns stable assumption_ids matching ISL graph nodes.

        Args:
            option: Option dict with causal structure
            outcome_metrics: Metrics to predict
            time_horizon: Time horizon for predictions

        Returns:
            Validation result with status, outcomes, assumptions

        Raises:
            httpx.HTTPError: If ISL request fails
        """
        # Extract causal structure from option
        causal_graph = self._extract_causal_graph(option)
        interventions = self._extract_interventions(option)

        request_payload = {
            "causal_graph": causal_graph,
            "interventions": interventions,
            "outcome_metrics": outcome_metrics,
            "time_horizon": time_horizon,
        }

        logger.info(
            "Requesting validation from ISL",
            extra={
                "option_id": option.get("option_id"),
                "metrics": outcome_metrics,
                "horizon": time_horizon,
            },
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/causal/validate",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "X-Request-ID": f"tae-validate-{option.get('option_id')}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )

            response.raise_for_status()
            result = response.json()

            logger.info(
                "ISL validation successful",
                extra={
                    "option_id": option.get("option_id"),
                    "is_identifiable": result.get("is_identifiable", False),
                },
            )

            return {
                "validation_status": ValidationStatus.VALIDATED,
                "is_identifiable": result.get("is_identifiable", False),
                "predicted_outcomes": result.get("predicted_outcomes", {}),
                "key_assumptions": result.get("assumptions", []),
                "warnings": result.get("warnings", []),
                "isl_response": result,
                "isl_request_id": result.get("request_id"),
            }

        except httpx.TimeoutException as e:
            logger.warning(
                "ISL validation timed out",
                extra={"option_id": option.get("option_id"), "timeout": self.timeout},
            )
            return {
                "validation_status": ValidationStatus.UNAVAILABLE,
                "is_identifiable": False,
                "predicted_outcomes": {},
                "key_assumptions": [],
                "warnings": [f"ISL validation timed out after {self.timeout}s"],
                "isl_response": {},
                "isl_request_id": None,
            }

        except httpx.HTTPError as e:
            logger.error(
                "ISL validation failed",
                extra={"option_id": option.get("option_id"), "error": str(e)},
                exc_info=True,
            )
            return {
                "validation_status": ValidationStatus.INVALID,
                "is_identifiable": False,
                "predicted_outcomes": {},
                "key_assumptions": [],
                "warnings": [f"ISL validation failed: {str(e)}"],
                "isl_response": {},
                "isl_request_id": None,
            }

    async def sensitivity_analysis(
        self,
        validation_id: str,
        factor: str,
        baseline_value: float,
        alternative_value: float,
    ) -> Dict[str, Any]:
        """
        Request sensitivity analysis on specific factor.

        Endpoint: POST /api/v1/analysis/sensitivity

        Args:
            validation_id: ID of previous validation
            factor: Factor to test
            baseline_value: Baseline value for factor
            alternative_value: Alternative value to test

        Returns:
            Sensitivity result with outcome deltas

        Raises:
            httpx.HTTPError: If ISL request fails
        """
        request_payload = {
            "validation_id": validation_id,
            "factor": factor,
            "baseline_value": baseline_value,
            "alternative_value": alternative_value,
        }

        logger.info(
            "Requesting sensitivity analysis from ISL",
            extra={
                "validation_id": validation_id,
                "factor": factor,
                "baseline": baseline_value,
                "alternative": alternative_value,
            },
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/analysis/sensitivity",
                json=request_payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )

            response.raise_for_status()
            result = response.json()

            logger.info(
                "ISL sensitivity analysis successful",
                extra={
                    "validation_id": validation_id,
                    "delta_percent": result.get("delta_percent", 0),
                },
            )

            return {
                "factor_tested": factor,
                "baseline_outcome": result.get("baseline_outcome", 0),
                "alternative_outcome": result.get("alternative_outcome", 0),
                "outcome_delta": result.get("delta", 0),
                "outcome_delta_percent": result.get("delta_percent", 0),
                "explanation": result.get("explanation", ""),
            }

        except httpx.HTTPError as e:
            logger.error(
                "ISL sensitivity analysis failed",
                extra={"validation_id": validation_id, "error": str(e)},
                exc_info=True,
            )
            raise

    def _extract_causal_graph(self, option: Dict[str, Any]) -> Dict[str, Any]:
        """Extract causal structure from option description."""
        # If option has scenario_link, use that model
        if option.get("scenario_link"):
            return {
                "model_id": option["scenario_link"]["model_id"],
                "parameter_deltas": option["scenario_link"].get("parameter_deltas", {}),
            }

        # Otherwise, construct from causal_rationale
        # (This requires NLP parsing - in real implementation, delegate to CEE if needed)
        return {
            "nodes": self._parse_nodes(option.get("causal_rationale", "")),
            "edges": self._parse_edges(option.get("causal_rationale", "")),
        }

    def _extract_interventions(self, option: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract interventions from option."""
        # In real implementation, parse from description/rationale
        # For now, return empty list as placeholder
        return []

    def _parse_nodes(self, rationale: str) -> List[str]:
        """Parse causal nodes from rationale text."""
        # Placeholder - real implementation would use NLP
        return []

    def _parse_edges(self, rationale: str) -> List[Dict[str, str]]:
        """Parse causal edges from rationale text."""
        # Placeholder - real implementation would use NLP
        return []

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
