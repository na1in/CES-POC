"""
Shared Gemini Flash client (via OpenRouter) for generating analyst-facing reasoning.

All scenario handlers call get_reasoning() to produce the human-readable
reasoning list and suggested_action. Decision logic is always done in code
first — the LLM only generates explanatory text, never makes the decision.
"""
import json
import logging

import openai

from app.config import settings

logger = logging.getLogger(__name__)

_client: openai.AsyncOpenAI | None = None

_MODEL = "google/gemini-2.5-flash"
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _get_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=_OPENROUTER_BASE,
        )
    return _client


async def get_reasoning(
    scenario_num: int,
    recommendation: str,
    context_summary: str,
    fallback_reasoning: list[str],
    fallback_action: str,
) -> tuple[list[str], str]:
    """
    Calls Gemini Flash via OpenRouter to generate analyst-facing reasoning
    and a suggested action.

    Args:
        scenario_num: 1–5, used for logging only.
        recommendation: "APPLY", "HOLD", or "ESCALATE" — the already-decided outcome.
        context_summary: Key facts about the payment formatted as plain text bullet points.
        fallback_reasoning: Returned as-is if the LLM call fails.
        fallback_action: Returned as-is if the LLM call fails.

    Returns:
        (reasoning_list, suggested_action) — always succeeds.
    """
    prompt = f"""You are an insurance payment exception analyst assistant reviewing an unidentified payment.

The system has determined the recommendation is: {recommendation}

Key facts about this payment:
{context_summary}

Write concise analyst-facing reasoning (3–6 bullet points) explaining why this recommendation was made, and a single-sentence suggested action for the analyst to take next.

Return ONLY valid JSON, no explanation or code fences:
{{"reasoning": ["point 1", "point 2"], "suggested_action": "single sentence"}}"""

    try:
        response = await _get_client().chat.completions.create(
            model=_MODEL,
            max_tokens=512,
            timeout=15.0,
            messages=[{"role": "user", "content": prompt}],
            extra_body={"thinking": {"type": "disabled"}},
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:-1])
        parsed = json.loads(text)
        reasoning = parsed.get("reasoning") or fallback_reasoning
        action = parsed.get("suggested_action") or fallback_action
        return reasoning, action
    except Exception as exc:
        logger.warning("Scenario %d reasoning call failed, using fallback: %s", scenario_num, exc)
        return fallback_reasoning, fallback_action
