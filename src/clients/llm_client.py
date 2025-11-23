"""LLM client for consensus synthesis generation.

Uses OpenAI API for generating creative synthesis options.
Can be swapped for other LLM providers.
"""

import logging
import json
from typing import List, Dict, Any, Optional
import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM-powered synthesis generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        timeout: int = 60,
    ):
        """Initialize LLM client.

        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Model name (gpt-4, gpt-3.5-turbo, etc.)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or getattr(settings, "openai_api_key", None)
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def generate_synthesis_options(
        self,
        decision_context: str,
        perspectives: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        num_options: int = 3,
    ) -> List[Dict[str, Any]]:
        """Generate creative synthesis options from team perspectives.

        Uses LLM to propose novel options that satisfy multiple constraints
        rather than just averaging positions.

        Args:
            decision_context: Background context for decision
            perspectives: Team member perspectives with causal graphs
            conflicts: Identified conflicts
            num_options: Number of synthesis options to generate

        Returns:
            List of synthesis option dictionaries
        """
        logger.info(
            f"Generating {num_options} synthesis options via LLM",
            extra={"num_perspectives": len(perspectives), "num_conflicts": len(conflicts)},
        )

        # Build prompt
        prompt = self._build_synthesis_prompt(
            decision_context, perspectives, conflicts, num_options
        )

        # Call LLM
        try:
            response = await self._call_llm(prompt)
            options = self._parse_synthesis_response(response)
            return options[:num_options]

        except Exception as e:
            logger.error(f"LLM synthesis generation failed: {e}", exc_info=True)
            # Return empty list on failure (graceful degradation)
            return []

    def _build_synthesis_prompt(
        self,
        decision_context: str,
        perspectives: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        num_options: int,
    ) -> str:
        """Build LLM prompt for synthesis generation.

        Args:
            decision_context: Decision background
            perspectives: Team perspectives
            conflicts: Identified conflicts
            num_options: Number of options to generate

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a consensus builder helping a team make a decision. Your goal is to generate creative synthesis options that satisfy multiple stakeholder constraints, NOT just average their positions.

**Decision Context:**
{decision_context}

**Team Perspectives:**
"""

        for i, perspective in enumerate(perspectives, 1):
            prompt += f"\n{i}. **{perspective['user_id']}** (causal quality: {perspective.get('quality_score', 0.5):.2f})\n"
            prompt += f"   Position: {perspective.get('reasoning', '')[:200]}\n"
            prompt += f"   Causal graph: {perspective.get('graph_summary', 'Not provided')}\n"

        if conflicts:
            prompt += "\n**Identified Conflicts:**\n"
            for i, conflict in enumerate(conflicts, 1):
                prompt += f"\n{i}. {conflict.get('type', 'unknown')} conflict: {conflict.get('description', '')}\n"

        prompt += f"""

**Your Task:**
Generate {num_options} creative synthesis options that:
1. **Satisfy multiple constraints** from different stakeholders (not just averaging)
2. **Introduce new causal mechanisms** that weren't in original perspectives
3. **Are Pareto-efficient** (improve some outcomes without worsening others)
4. **Are novel** (creative score > 0.5, not just obvious compromises)

For each option, provide:
- **description**: Natural language description (1-2 sentences)
- **causal_mechanism**: How this option achieves outcomes (causal reasoning)
- **satisfies_constraints**: Which stakeholder needs are met (list of user_ids)
- **nodes_added**: New variables introduced to causal graph
- **edges_added**: New causal edges (format: "A → B")
- **mediators_introduced**: Mediating variables (on path between decision and outcome)

Return response as JSON array of options.

Example response format:
```json
[
  {{
    "description": "Implement UX improvements first, then staged 20% price increase over 6 months",
    "causal_mechanism": "UX improvements increase perceived value, reducing price sensitivity before increase",
    "satisfies_constraints": ["pm_001", "designer_002", "engineer_003"],
    "nodes_added": ["perceived_value", "ux_improvements"],
    "edges_added": ["ux_improvements → perceived_value", "perceived_value → price_sensitivity"],
    "mediators_introduced": ["perceived_value"]
  }}
]
```

Generate {num_options} creative synthesis options now:
"""

        return prompt

    async def _call_llm(self, prompt: str) -> str:
        """Call OpenAI API with prompt.

        Args:
            prompt: Prompt string

        Returns:
            LLM response text

        Raises:
            httpx.HTTPError: If API call fails
        """
        if not self.api_key:
            logger.warning("No OpenAI API key configured, using mock response")
            return self._mock_llm_response()

        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a consensus builder expert in causal reasoning and creative problem-solving.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )

            response.raise_for_status()
            result = response.json()

            return result["choices"][0]["message"]["content"]

        except httpx.HTTPError as e:
            logger.error(f"OpenAI API call failed: {e}", exc_info=True)
            raise

    def _mock_llm_response(self) -> str:
        """Generate mock LLM response for testing without API key.

        Returns:
            Mock JSON response
        """
        return """```json
[
  {
    "description": "Pilot quality improvements with select customers, then implement phased 15% price increase based on demonstrated value",
    "causal_mechanism": "Quality improvements reduce churn risk, creating headroom for modest price increase while maintaining customer satisfaction",
    "satisfies_constraints": ["pm_001", "engineer_002"],
    "nodes_added": ["customer_satisfaction", "demonstrated_value"],
    "edges_added": ["quality → customer_satisfaction", "customer_satisfaction → price_acceptance"],
    "mediators_introduced": ["customer_satisfaction"]
  },
  {
    "description": "Bundle new premium features with price increase, positioning as product tier upgrade rather than price change",
    "causal_mechanism": "Premium features create new value proposition, reducing perception of price increase as price increase",
    "satisfies_constraints": ["pm_001", "designer_003"],
    "nodes_added": ["premium_features", "value_proposition"],
    "edges_added": ["premium_features → value_proposition", "value_proposition → willingness_to_pay"],
    "mediators_introduced": ["value_proposition"]
  },
  {
    "description": "Implement revenue-based pricing model that scales with customer success, aligning price with value delivered",
    "causal_mechanism": "Usage-based pricing ties cost to value, reducing price sensitivity and churn while enabling revenue growth",
    "satisfies_constraints": ["pm_001", "engineer_002", "designer_003"],
    "nodes_added": ["usage_based_pricing", "value_alignment"],
    "edges_added": ["usage_based_pricing → value_alignment", "value_alignment → churn"],
    "mediators_introduced": ["value_alignment"]
  }
]
```"""

    def _parse_synthesis_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into synthesis options.

        Args:
            response: LLM response text (JSON or markdown-wrapped JSON)

        Returns:
            List of synthesis option dictionaries
        """
        # Extract JSON from markdown code blocks if present
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            json_str = response[start:end].strip()
        else:
            json_str = response.strip()

        try:
            options = json.loads(json_str)
            return options if isinstance(options, list) else []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return []

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
