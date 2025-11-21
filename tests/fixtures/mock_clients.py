"""Mock clients for testing."""

from typing import Dict, List, Any
from uuid import uuid4


class MockCEEClient:
    """Mock CEE client for testing without real CEE service."""

    async def extract_profile(
        self,
        user_input: Dict[str, Any],
        role: str,
        decision_context: str,
        goal_dimensions: List[str],
        seed: str,
    ) -> Dict[str, Any]:
        """Mock profile extraction."""
        # Simple mock extraction based on keywords
        desired_outcome = user_input.get("desired_outcome", "").lower()

        goal_weights = {}
        for dim in goal_dimensions:
            if dim in desired_outcome or dim.replace("_", " ") in desired_outcome:
                goal_weights[dim] = 0.8
            else:
                goal_weights[dim] = 0.5

        # Detect risk tolerance
        if "conservative" in desired_outcome or "safe" in desired_outcome:
            risk_tolerance = "conservative"
        elif "aggressive" in desired_outcome or "bold" in desired_outcome:
            risk_tolerance = "aggressive"
        else:
            risk_tolerance = "moderate"

        # Detect time horizon
        if "week" in desired_outcome:
            time_horizon = "weekly"
        elif "month" in desired_outcome:
            time_horizon = "monthly"
        elif "year" in desired_outcome:
            time_horizon = "annual"
        else:
            time_horizon = "quarterly"

        return {
            "goal_weights": goal_weights,
            "risk_tolerance": risk_tolerance,
            "time_horizon": time_horizon,
            "must_have_constraints": user_input.get("key_concerns", [])[:2],
            "red_lines": [],
            "confidence": 0.85,
        }

    async def explain_validation(
        self,
        option: Dict[str, Any],
        validation_result: Dict[str, Any],
        audience_role: str,
        tier: int = 1,
    ) -> Dict[str, Any]:
        """Mock validation explanation."""
        return {
            "explanation": f"Option {option.get('title')} has been validated. "
            f"Status: {validation_result.get('validation_status')}"
        }

    async def generate_shared_ground_summary(
        self, profiles: List[Dict[str, Any]], decision_context: str
    ) -> Dict[str, Any]:
        """Mock shared ground summary."""
        return {
            "summary": f"Team aligns on key priorities based on {len(profiles)} perspectives."
        }

    async def generate_disagreement_summary(
        self, profiles: List[Dict[str, Any]], decision_context: str
    ) -> Dict[str, Any]:
        """Mock disagreement summary."""
        return {
            "summary": f"Primary tensions identified across {len(profiles)} stakeholders."
        }

    async def close(self) -> None:
        """Mock close."""
        pass


class MockISLClient:
    """Mock ISL client for testing without real ISL service."""

    async def validate_option(
        self,
        option: Dict[str, Any],
        outcome_metrics: List[str],
        time_horizon: str,
    ) -> Dict[str, Any]:
        """Mock option validation."""
        # Generate mock predictions
        predicted_outcomes = {}
        for metric in outcome_metrics:
            predicted_outcomes[metric] = {
                "p10": 0.08,
                "p50": 0.12,
                "p90": 0.18,
                "unit": "%",
                "confidence": "medium",
            }

        # Mock assumptions
        key_assumptions = []
        for assumption in option.get("key_assumptions", []):
            key_assumptions.append({
                "assumption_id": assumption.get("assumption_id", str(uuid4())),
                "assumption_text": assumption.get("assumption_text", "Test assumption"),
                "evidence_strength": "medium",
                "impact_if_wrong": "medium",
                "source": "mock_isl",
            })

        return {
            "validation_status": "validated",
            "is_identifiable": True,
            "predicted_outcomes": predicted_outcomes,
            "assumptions": key_assumptions,
            "warnings": [],
            "request_id": f"mock_req_{uuid4()}",
        }

    async def sensitivity_analysis(
        self,
        validation_id: str,
        factor: str,
        baseline_value: float,
        alternative_value: float,
    ) -> Dict[str, Any]:
        """Mock sensitivity analysis."""
        # Simple mock: 10% change
        delta = abs(alternative_value - baseline_value) * 0.1
        delta_percent = delta / baseline_value if baseline_value != 0 else 0

        return {
            "factor_tested": factor,
            "baseline_outcome": baseline_value,
            "alternative_outcome": baseline_value + delta,
            "delta": delta,
            "delta_percent": delta_percent,
            "explanation": f"Changing {factor} from {baseline_value} to {alternative_value} "
            f"results in {delta_percent:.1%} impact",
        }

    async def close(self) -> None:
        """Mock close."""
        pass
