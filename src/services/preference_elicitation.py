"""Preference elicitation service (Phase 2A: ActiVA).

Counterfactual-based value elicitation using active learning and Bayesian updates.
"""

import logging
import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import math

from src.models.preferences import (
    PreferenceElicitationSessionV1,
    CounterfactualScenarioV1,
    PreferenceResponseV1,
    ValueModelV1,
    ValueDimensionV1,
)
from src.clients.llm_client import LLMClient

logger = logging.getLogger(__name__)


class PreferenceElicitationService:
    """Service for eliciting user values through counterfactual scenarios."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize preference elicitation service.

        Args:
            llm_client: LLM client for scenario generation

        Note:
            In production, llm_client should always be provided via dependency
            injection to ensure proper resource cleanup. The fallback is for
            testing only and may leak resources.
        """
        self.llm_client = llm_client or LLMClient()  # Fallback for tests only

        # In-memory storage (in production, use database)
        self.sessions: Dict[str, PreferenceElicitationSessionV1] = {}

    async def start_session(
        self,
        user_id: str,
        decision_context: str,
        value_dimensions: List[str],
        target_convergence: float = 0.9,
        max_questions: int = 7,
    ) -> Tuple[PreferenceElicitationSessionV1, CounterfactualScenarioV1]:
        """Start new preference elicitation session.

        Args:
            user_id: User ID
            decision_context: Decision context
            value_dimensions: Value dimensions to elicit
            target_convergence: Target convergence score
            max_questions: Max questions to ask

        Returns:
            Tuple of (session, first_scenario)
        """
        logger.info(
            f"Starting preference elicitation for user {user_id}",
            extra={
                "decision_context": decision_context[:100],
                "value_dimensions": value_dimensions,
            },
        )

        # Create session
        session = PreferenceElicitationSessionV1(
            user_id=user_id,
            decision_context=decision_context,
            value_dimensions=value_dimensions,
            target_convergence=target_convergence,
            max_questions=max_questions,
        )

        # Initialize uniform prior for value model
        session.value_model = self._initialize_value_model(user_id, value_dimensions)

        # Generate first scenario
        first_scenario = await self._generate_scenario(session)
        session.scenarios_presented.append(first_scenario)

        # Store session
        self.sessions[session.session_id] = session

        logger.info(f"Session {session.session_id} started with first scenario")

        return session, first_scenario

    async def submit_response(
        self,
        session_id: str,
        user_id: str,
        scenario_id: str,
        choice: str,
        strength: float,
        response_time_ms: Optional[int] = None,
    ) -> Tuple[bool, Optional[CounterfactualScenarioV1], bool]:
        """Submit response to a scenario.

        Args:
            session_id: Session ID
            user_id: User ID
            scenario_id: Scenario ID
            choice: User's choice (A, B, or indifferent)
            strength: Strength of preference
            response_time_ms: Response time

        Returns:
            Tuple of (accepted, next_scenario, session_complete)
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.user_id != user_id:
            raise ValueError(f"User {user_id} does not own session {session_id}")

        # Find scenario
        scenario = next(
            (s for s in session.scenarios_presented if s.scenario_id == scenario_id),
            None,
        )
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        # Create response
        response = PreferenceResponseV1(
            scenario_id=scenario_id,
            user_id=user_id,
            choice=choice,
            strength=strength,
            response_time_ms=response_time_ms,
        )
        session.responses.append(response)

        # Update value model using Bayesian update
        self._update_value_model(session, scenario, response)

        # Check convergence
        converged = session.value_model.convergence_score >= session.target_convergence
        max_reached = len(session.responses) >= session.max_questions

        if converged or max_reached:
            # Session complete
            session.status = "converged"
            session.completed_at = datetime.utcnow().isoformat() + "Z"

            logger.info(
                f"Session {session_id} completed",
                extra={
                    "converged": converged,
                    "questions_asked": len(session.responses),
                    "convergence_score": session.value_model.convergence_score,
                },
            )

            return True, None, True

        # Generate next scenario using active learning
        next_scenario = await self._select_next_scenario(session)
        session.scenarios_presented.append(next_scenario)

        logger.info(
            f"Response submitted for scenario {scenario_id}",
            extra={
                "choice": choice,
                "questions_asked": len(session.responses),
                "convergence_score": session.value_model.convergence_score,
            },
        )

        return True, next_scenario, False

    def get_value_model(
        self,
        session_id: str,
        user_id: str,
    ) -> ValueModelV1:
        """Get current value model for a session.

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            Current value model
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.user_id != user_id:
            raise ValueError(f"User {user_id} does not own session {session_id}")

        return session.value_model

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================

    def _initialize_value_model(
        self,
        user_id: str,
        value_dimensions: List[str],
    ) -> ValueModelV1:
        """Initialize value model with uniform prior.

        Args:
            user_id: User ID
            value_dimensions: Value dimensions

        Returns:
            Initial value model with uniform weights
        """
        # Uniform Dirichlet prior (all alphas = 1)
        dimensions = [
            ValueDimensionV1(
                dimension=dim,
                weight=1.0 / len(value_dimensions),  # Uniform
                confidence=0.0,  # No confidence yet
                alpha=1.0,  # Uniform prior
                samples_count=0,
            )
            for dim in value_dimensions
        ]

        return ValueModelV1(
            user_id=user_id,
            dimensions=dimensions,
            convergence_score=0.0,
            questions_asked=0,
        )

    async def _generate_scenario(
        self,
        session: PreferenceElicitationSessionV1,
    ) -> CounterfactualScenarioV1:
        """Generate a counterfactual scenario.

        Args:
            session: Elicitation session

        Returns:
            Generated scenario
        """
        # Select dimensions to discriminate (highest uncertainty)
        dimensions = self._select_discriminating_dimensions(session)

        # Generate scenario via LLM
        prompt = f"""Generate a counterfactual scenario for value elicitation.

Decision context: {session.decision_context}

Value dimensions to discriminate: {', '.join(dimensions)}

Create two alternative outcomes (A and B) that differ primarily on these dimensions.
Each outcome should be realistic and relevant to the decision context.

Return JSON:
{{
  "question": "Brief question prompt",
  "option_a": "Description of outcome A",
  "option_b": "Description of outcome B",
  "option_a_values": {{"dimension": score_0_to_1, ...}},
  "option_b_values": {{"dimension": score_0_to_1, ...}}
}}

Make sure option A and B differ significantly on {dimensions[0]}.
"""

        try:
            response_text = await self.llm_client._call_llm(prompt)
            scenario_data = self.llm_client._parse_synthesis_response(response_text)

            if scenario_data and len(scenario_data) > 0:
                data = scenario_data[0] if isinstance(scenario_data, list) else scenario_data

                # Compute expected information gain
                eig = self._compute_expected_information_gain(
                    dimensions,
                    data.get("option_a_values", {}),
                    data.get("option_b_values", {}),
                )

                return CounterfactualScenarioV1(
                    question=data.get("question", "Which outcome do you prefer?"),
                    option_a=data.get("option_a", "Option A"),
                    option_b=data.get("option_b", "Option B"),
                    option_a_values=data.get("option_a_values", {}),
                    option_b_values=data.get("option_b_values", {}),
                    discriminating_dimensions=dimensions,
                    expected_information_gain=eig,
                )

        except Exception as e:
            logger.warning(f"LLM scenario generation failed: {e}, using fallback")

        # Fallback: create simple synthetic scenario
        return self._create_fallback_scenario(session, dimensions)

    def _create_fallback_scenario(
        self,
        session: PreferenceElicitationSessionV1,
        dimensions: List[str],
    ) -> CounterfactualScenarioV1:
        """Create a simple fallback scenario.

        Args:
            session: Elicitation session
            dimensions: Discriminating dimensions

        Returns:
            Fallback scenario
        """
        dim1 = dimensions[0]
        dim2 = dimensions[1] if len(dimensions) > 1 else dimensions[0]

        option_a_values = {dim: 0.3 for dim in session.value_dimensions}
        option_a_values[dim1] = 0.9

        option_b_values = {dim: 0.3 for dim in session.value_dimensions}
        option_b_values[dim2] = 0.9

        return CounterfactualScenarioV1(
            question=f"Which outcome do you prefer for {session.decision_context}?",
            option_a=f"High {dim1}, moderate {dim2}",
            option_b=f"Moderate {dim1}, high {dim2}",
            option_a_values=option_a_values,
            option_b_values=option_b_values,
            discriminating_dimensions=[dim1, dim2],
            expected_information_gain=0.5,
        )

    def _select_discriminating_dimensions(
        self,
        session: PreferenceElicitationSessionV1,
    ) -> List[str]:
        """Select dimensions with highest uncertainty for next question.

        Args:
            session: Elicitation session

        Returns:
            List of dimension names (up to 2)
        """
        # Sort dimensions by confidence (ascending = highest uncertainty first)
        sorted_dims = sorted(
            session.value_model.dimensions,
            key=lambda d: d.confidence,
        )

        # Return top 2 most uncertain dimensions
        return [d.dimension for d in sorted_dims[:2]]

    async def _select_next_scenario(
        self,
        session: PreferenceElicitationSessionV1,
    ) -> CounterfactualScenarioV1:
        """Select next scenario using active learning.

        Args:
            session: Elicitation session

        Returns:
            Next scenario to present
        """
        # For now, just generate a new scenario
        # In a full implementation, this would:
        # 1. Generate multiple candidate scenarios
        # 2. Compute expected information gain for each
        # 3. Select the one with highest EIG

        return await self._generate_scenario(session)

    def _update_value_model(
        self,
        session: PreferenceElicitationSessionV1,
        scenario: CounterfactualScenarioV1,
        response: PreferenceResponseV1,
    ) -> None:
        """Update value model using Bayesian update.

        Args:
            session: Elicitation session
            scenario: Scenario user responded to
            response: User's response
        """
        # Simplified Bayesian update using Dirichlet-multinomial model
        #
        # For a full ActiVA implementation, this would:
        # 1. Compute likelihood of response given current model
        # 2. Update Dirichlet posterior parameters
        # 3. Compute new mean weights from posterior
        # 4. Update confidence intervals

        if response.choice == "indifferent":
            # Indifferent response doesn't update model much
            return

        # Determine which dimensions were preferred
        preferred_values = (
            scenario.option_a_values if response.choice == "A" else scenario.option_b_values
        )
        not_preferred_values = (
            scenario.option_b_values if response.choice == "A" else scenario.option_a_values
        )

        # Update alphas for discriminating dimensions
        for dim_name in scenario.discriminating_dimensions:
            dim_obj = next(
                (d for d in session.value_model.dimensions if d.dimension == dim_name),
                None,
            )
            if not dim_obj:
                continue

            # Compute value difference
            value_diff = preferred_values.get(dim_name, 0.5) - not_preferred_values.get(
                dim_name, 0.5
            )

            # Update alpha proportional to value difference and response strength
            update_size = abs(value_diff) * response.strength * 0.5

            dim_obj.alpha += update_size
            dim_obj.samples_count += 1

        # Recompute weights from alphas (Dirichlet mean)
        total_alpha = sum(d.alpha for d in session.value_model.dimensions)
        for dim_obj in session.value_model.dimensions:
            dim_obj.weight = dim_obj.alpha / total_alpha

            # Compute confidence from sample count and alpha
            # Higher alpha + more samples = higher confidence
            dim_obj.confidence = min(
                1.0,
                (dim_obj.alpha - 1.0) / 5.0 * (1.0 + dim_obj.samples_count / 10.0),
            )

        # Compute overall convergence score (average confidence)
        avg_confidence = sum(d.confidence for d in session.value_model.dimensions) / len(
            session.value_model.dimensions
        )
        session.value_model.convergence_score = avg_confidence
        session.value_model.questions_asked = len(session.responses)

        logger.debug(
            f"Updated value model",
            extra={
                "convergence_score": session.value_model.convergence_score,
                "weights": {d.dimension: round(d.weight, 3) for d in session.value_model.dimensions},
            },
        )

    def _compute_expected_information_gain(
        self,
        dimensions: List[str],
        option_a_values: Dict[str, float],
        option_b_values: Dict[str, float],
    ) -> float:
        """Compute expected information gain for a scenario.

        Args:
            dimensions: Discriminating dimensions
            option_a_values: Values for option A
            option_b_values: Values for option B

        Returns:
            Expected information gain (0-1)
        """
        # Simplified EIG: larger differences = more informative
        total_diff = 0.0
        for dim in dimensions:
            val_a = option_a_values.get(dim, 0.5)
            val_b = option_b_values.get(dim, 0.5)
            total_diff += abs(val_a - val_b)

        # Normalize by number of dimensions
        avg_diff = total_diff / len(dimensions)

        return min(1.0, avg_diff)
