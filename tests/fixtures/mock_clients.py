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

    # Phase C methods
    async def generate_options(
        self,
        profiles: List[Dict[str, Any]],
        decision_context: str,
        disagreement_map: Dict[str, Any],
        generation_mode: str,
        num_options: int = 3,
        seed: str = None,
    ) -> Dict[str, Any]:
        """Mock AI option generation."""
        options = []
        for i in range(num_options):
            options.append({
                "title": f"AI Generated Option {i+1}",
                "description": f"Mock option generated in {generation_mode} mode",
                "expected_outcome": "Positive outcome expected",
                "causal_rationale": "Based on stakeholder profiles and disagreement analysis",
                "addresses_goals": ["revenue", "retention"],
                "trade_offs": [{"dimension": "timeline", "impact": "medium"}],
                "key_assumptions": [
                    {"assumption_id": f"ai_assump_{i+1}", "assumption_text": "Market conditions remain stable"}
                ],
                "tension_addressed": "cost_vs_quality",
                "perspective_weights": {"pm": 0.6, "designer": 0.4},
            })
        return {"options": options, "request_id": f"mock_gen_{uuid4()}"}

    async def synthesize_options(
        self,
        source_options: List[Dict[str, Any]],
        decision_context: str,
        profiles: List[Dict[str, Any]],
        synthesis_goal: str,
    ) -> Dict[str, Any]:
        """Mock option synthesis."""
        return {
            "synthesized_option": {
                "title": "Synthesized Hybrid Option",
                "description": f"Combination of {len(source_options)} options optimized for {synthesis_goal}",
                "expected_outcome": "Best of both worlds",
                "causal_rationale": "Combines strengths while mitigating weaknesses",
                "addresses_goals": ["revenue", "retention", "user_experience"],
                "trade_offs": [{"dimension": "complexity", "impact": "medium"}],
                "key_assumptions": [
                    {"assumption_id": "synth_assump_1", "assumption_text": "Teams can coordinate effectively"}
                ],
                "elements_preserved": ["timeline", "budget"],
                "elements_sacrificed": ["scope"],
                "compatibility_score": 0.85,
            }
        }

    async def tune_option(
        self,
        option: Dict[str, Any],
        concern: Dict[str, Any],
        profiles: List[Dict[str, Any]],
        decision_context: str,
        preserve_elements: List[str],
    ) -> Dict[str, Any]:
        """Mock option tuning."""
        return {
            "tuned_option": {
                "title": f"{option.get('title')} (Tuned)",
                "description": f"Adjusted to address concern: {concern.get('concern_text')[:50]}...",
                "expected_outcome": "Improved stakeholder alignment",
                "causal_rationale": "Modified to address minority concern while preserving core elements",
                "addresses_goals": option.get("addresses_goals", []),
                "trade_offs": option.get("trade_offs", []),
                "key_assumptions": option.get("key_assumptions", []),
                "parameters_adjusted": [{"parameter": "timeline", "original": "6 months", "tuned": "8 months"}],
                "preserved_elements": preserve_elements,
            }
        }

    async def recommend_test_strategy(
        self,
        assumptions: List[Dict[str, Any]],
        option: Dict[str, Any],
        decision_context: str,
        time_to_decision: int,
        available_resources: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Mock test strategy recommendations."""
        recommendations = []
        for i, assumption in enumerate(assumptions[:3]):  # Top 3
            recommendations.append({
                "assumption_id": assumption.get("assumption_id"),
                "priority": i + 1,
                "recommended_method": ["a_b_test", "technical_spike", "user_research"][i % 3],
                "estimated_effort_days": [7, 3, 5][i % 3],
                "estimated_cost": [5000, 2000, 3000][i % 3],
                "rationale": f"High impact assumption requiring validation",
                "alternative_methods": ["prototype", "survey"],
                "expected_confidence_gain": 0.3,
            })
        return {"recommendations": recommendations}

    async def generate_lessons_learned(
        self,
        decision_brief: Dict[str, Any],
        actual_outcomes: Dict[str, float],
        assumption_validations: List[Dict[str, Any]],
        decision_context: str,
    ) -> Dict[str, Any]:
        """Mock lessons learned generation."""
        return {
            "narrative": "The decision performed moderately well. Key assumptions held but outcomes varied from predictions.",
            "lessons_learned": [
                {
                    "lesson": "Market volatility was higher than expected",
                    "impact": "medium",
                    "recommendation": "Build in more buffer for market uncertainty",
                },
                {
                    "lesson": "Cross-team coordination worked better than anticipated",
                    "impact": "positive",
                    "recommendation": "Continue investing in team collaboration",
                },
            ],
        }

    async def generate_org_recommendations(
        self,
        retrospectives: List[Dict[str, Any]],
        team_id: str,
    ) -> Dict[str, Any]:
        """Mock organizational recommendations."""
        return {
            "patterns": [
                "Team consistently underestimates timeline requirements",
                "Strong performance on user-facing features",
            ],
            "strengths": [
                "Excellent cross-functional collaboration",
                "Data-driven decision making",
            ],
            "areas_for_improvement": [
                "Assumption validation before commitment",
                "More realistic timeline estimation",
            ],
            "recommended_changes": [
                "Add mandatory assumption testing phase",
                "Implement rolling retrospectives",
            ],
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
