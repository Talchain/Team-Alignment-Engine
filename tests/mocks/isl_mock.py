"""Mock ISL (Inference Service Layer) server for testing.

Provides deterministic responses for causal validation without requiring actual ISL service.
Supports configurable latency and error injection for testing fault scenarios.
"""

import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class MockISLServer:
    """Lightweight ISL simulator for deterministic testing."""

    def __init__(
        self,
        default_latency_ms: int = 0,
        error_rate: float = 0.0,
        identifiable_rate: float = 0.8,
    ):
        """
        Initialize mock ISL server.

        Args:
            default_latency_ms: Simulated processing delay (milliseconds)
            error_rate: Probability of returning errors (0.0-1.0)
            identifiable_rate: Probability of causal graphs being identifiable (0.0-1.0)
        """
        self.app = FastAPI(title="Mock ISL Server", version="1.0.0")
        self.default_latency_ms = default_latency_ms
        self.error_rate = error_rate
        self.identifiable_rate = identifiable_rate
        self.validation_history: List[Dict[str, Any]] = []

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all ISL API endpoints."""

        @self.app.post("/api/v1/causal/validate")
        async def validate_causal_graph(
            payload: Dict[str, Any],
            x_api_key: str = Header(..., alias="X-API-Key"),
            x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
        ) -> JSONResponse:
            """
            Validate causal graph and predict outcomes.

            Mock implementation returns deterministic results based on input hash.
            """
            # Simulate processing delay
            if self.default_latency_ms > 0:
                await asyncio.sleep(self.default_latency_ms / 1000.0)

            # Validate API key
            if not x_api_key or len(x_api_key) < 16:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid or missing API key",
                )

            # Extract request data
            causal_graph = payload.get("causal_graph", {})
            interventions = payload.get("interventions", [])
            outcome_metrics = payload.get("outcome_metrics", [])
            time_horizon = payload.get("time_horizon", "quarterly")

            # Generate deterministic request ID
            request_id = x_request_id or f"mock-isl-{uuid4()}"

            # Check for error injection
            import random
            if random.random() < self.error_rate:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Mock ISL error injection",
                )

            # Deterministic identifiability based on graph hash
            graph_hash = self._hash_graph(causal_graph)
            is_identifiable = (int(graph_hash, 16) % 100) < (self.identifiable_rate * 100)

            # Generate mock validation result
            result = self._generate_validation_result(
                causal_graph=causal_graph,
                interventions=interventions,
                outcome_metrics=outcome_metrics,
                time_horizon=time_horizon,
                is_identifiable=is_identifiable,
                request_id=request_id,
            )

            # Store in history
            self.validation_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "payload": payload,
                "result": result,
            })

            return JSONResponse(content=result, status_code=status.HTTP_200_OK)

        @self.app.post("/api/v1/analysis/sensitivity")
        async def sensitivity_analysis(
            payload: Dict[str, Any],
            x_api_key: str = Header(..., alias="X-API-Key"),
            x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
        ) -> JSONResponse:
            """
            Perform sensitivity analysis on validated graph.

            Mock implementation returns deterministic sensitivity metrics.
            """
            # Simulate processing delay
            if self.default_latency_ms > 0:
                await asyncio.sleep(self.default_latency_ms / 1000.0)

            # Validate API key
            if not x_api_key or len(x_api_key) < 16:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid or missing API key",
                )

            validation_id = payload.get("validation_id")
            factor = payload.get("factor")
            baseline_value = payload.get("baseline_value", 0.0)
            alternative_value = payload.get("alternative_value", 0.0)

            request_id = x_request_id or f"mock-isl-sens-{uuid4()}"

            # Check for error injection
            import random
            if random.random() < self.error_rate:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Mock ISL sensitivity analysis error",
                )

            # Generate mock sensitivity result
            result = self._generate_sensitivity_result(
                validation_id=validation_id,
                factor=factor,
                baseline_value=baseline_value,
                alternative_value=alternative_value,
                request_id=request_id,
            )

            return JSONResponse(content=result, status_code=status.HTTP_200_OK)

        @self.app.get("/api/v1/health")
        async def health_check() -> JSONResponse:
            """Health check endpoint."""
            return JSONResponse(
                content={
                    "status": "healthy",
                    "service": "mock-isl",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                status_code=status.HTTP_200_OK,
            )

        @self.app.get("/mock/history")
        async def get_validation_history() -> JSONResponse:
            """Return validation history (mock-only endpoint for testing)."""
            return JSONResponse(
                content={
                    "total_validations": len(self.validation_history),
                    "history": self.validation_history,
                },
                status_code=status.HTTP_200_OK,
            )

        @self.app.post("/mock/reset")
        async def reset_state() -> JSONResponse:
            """Reset mock server state (mock-only endpoint for testing)."""
            self.validation_history.clear()
            return JSONResponse(
                content={"status": "reset", "message": "Mock server state cleared"},
                status_code=status.HTTP_200_OK,
            )

        @self.app.post("/mock/configure")
        async def configure_behavior(config: Dict[str, Any]) -> JSONResponse:
            """Configure mock behavior (mock-only endpoint for testing)."""
            if "latency_ms" in config:
                self.default_latency_ms = config["latency_ms"]
            if "error_rate" in config:
                self.error_rate = max(0.0, min(1.0, config["error_rate"]))
            if "identifiable_rate" in config:
                self.identifiable_rate = max(0.0, min(1.0, config["identifiable_rate"]))

            return JSONResponse(
                content={
                    "status": "configured",
                    "current_config": {
                        "latency_ms": self.default_latency_ms,
                        "error_rate": self.error_rate,
                        "identifiable_rate": self.identifiable_rate,
                    },
                },
                status_code=status.HTTP_200_OK,
            )

    def _hash_graph(self, graph: Dict[str, Any]) -> str:
        """Generate deterministic hash of causal graph structure."""
        import json

        # Serialize graph to stable JSON
        graph_str = json.dumps(graph, sort_keys=True)
        return hashlib.sha256(graph_str.encode()).hexdigest()

    def _generate_validation_result(
        self,
        causal_graph: Dict[str, Any],
        interventions: List[Dict[str, Any]],
        outcome_metrics: List[str],
        time_horizon: str,
        is_identifiable: bool,
        request_id: str,
    ) -> Dict[str, Any]:
        """Generate deterministic validation result based on inputs."""
        # Extract nodes and edges from graph
        nodes = causal_graph.get("nodes", [])
        edges = causal_graph.get("edges", [])

        # Generate assumptions from graph structure
        assumptions = []
        for i, edge in enumerate(edges[:5]):  # Limit to 5 assumptions
            source = edge.get("source", f"node_{i}")
            target = edge.get("target", f"outcome_{i}")
            assumptions.append({
                "assumption_id": f"a{i+1}",
                "assumption_text": f"{source} causally affects {target}",
                "validated": is_identifiable,
                "confidence": 0.7 + (i * 0.05),
                "evidence_level": "medium" if is_identifiable else "weak",
            })

        # Generate predicted outcomes
        predicted_outcomes = {}
        if is_identifiable:
            for metric in outcome_metrics:
                # Deterministic outcome based on metric name hash
                metric_hash = int(hashlib.md5(metric.encode()).hexdigest(), 16)
                base_value = (metric_hash % 100) / 100.0  # 0.0-1.0
                predicted_outcomes[metric] = {
                    "point_estimate": base_value,
                    "confidence_interval": [base_value * 0.8, base_value * 1.2],
                    "confidence_level": 0.85,
                }

        # Generate warnings
        warnings = []
        if not is_identifiable:
            warnings.append("Causal graph is not identifiable - confounding may exist")
        if len(nodes) < 3:
            warnings.append("Limited graph complexity - predictions may be unreliable")

        # Determine data sufficiency
        data_sufficiency = "sufficient" if is_identifiable else "insufficient"

        # Quality concerns
        quality_concerns = []
        if len(edges) < 2:
            quality_concerns.append("Sparse causal structure")

        # Sensitivity factors
        sensitivity_factors = {}
        for assumption in assumptions[:2]:
            factor_id = assumption["assumption_id"]
            sensitivity_factors[factor_id] = (
                0.3 + (int(hashlib.md5(factor_id.encode()).hexdigest(), 16) % 50) / 100.0
            )

        return {
            "request_id": request_id,
            "is_identifiable": is_identifiable,
            "validation_status": "validated" if is_identifiable else "uncertain",
            "data_sufficiency": data_sufficiency,
            "predicted_outcomes": predicted_outcomes,
            "assumptions": assumptions,
            "warnings": warnings,
            "quality_concerns": quality_concerns,
            "sensitivity_factors": sensitivity_factors,
            "time_horizon": time_horizon,
            "validated_at": datetime.utcnow().isoformat(),
        }

    def _generate_sensitivity_result(
        self,
        validation_id: str,
        factor: str,
        baseline_value: float,
        alternative_value: float,
        request_id: str,
    ) -> Dict[str, Any]:
        """Generate deterministic sensitivity analysis result."""
        # Calculate deterministic impact based on factor hash
        factor_hash = int(hashlib.md5(factor.encode()).hexdigest(), 16)
        impact_multiplier = 0.5 + (factor_hash % 100) / 100.0  # 0.5-1.5

        delta = alternative_value - baseline_value
        outcome_delta = delta * impact_multiplier

        return {
            "request_id": request_id,
            "validation_id": validation_id,
            "factor": factor,
            "baseline_value": baseline_value,
            "alternative_value": alternative_value,
            "sensitivity_score": abs(impact_multiplier),
            "outcome_delta": outcome_delta,
            "confidence": 0.75,
            "recommendation": (
                "High sensitivity - small changes significantly impact outcomes"
                if abs(impact_multiplier) > 1.0
                else "Low sensitivity - factor has limited impact"
            ),
            "analyzed_at": datetime.utcnow().isoformat(),
        }


# Factory function for easy test usage
def create_mock_isl_server(
    latency_ms: int = 0,
    error_rate: float = 0.0,
    identifiable_rate: float = 0.8,
) -> MockISLServer:
    """
    Create a configured MockISLServer instance.

    Args:
        latency_ms: Simulated processing delay in milliseconds
        error_rate: Probability of errors (0.0-1.0)
        identifiable_rate: Probability of identifiable graphs (0.0-1.0)

    Returns:
        Configured MockISLServer instance

    Example:
        >>> mock_isl = create_mock_isl_server(latency_ms=100, error_rate=0.1)
        >>> # Use mock_isl.app with FastAPI TestClient
    """
    return MockISLServer(
        default_latency_ms=latency_ms,
        error_rate=error_rate,
        identifiable_rate=identifiable_rate,
    )
