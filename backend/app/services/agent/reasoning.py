"""
Shared Claude Sonnet client for generating analyst-facing reasoning.

All scenario handlers call get_reasoning() to produce the human-readable
reasoning list and suggested_action. Decision logic is always done in code
first — Claude only generates explanatory text, never makes the decision.
"""
import json
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def get_reasoning(
    scenario_num: int,
    recommendation: str,
    context_summary: str,
    fallback_reasoning: list[str],
    fallback_action: str,
) -> tuple[list[str], str]:
    """
    Calls Claude Sonnet to generate analyst-facing reasoning and a suggested action.

    Args:
        scenario_num: 1–5, used for logging only.
        recommendation: "APPLY", "HOLD", or "ESCALATE" — the already-decided outcome.
        context_summary: Key facts about the payment formatted as plain text bullet points.
        fallback_reasoning: Returned as-is if the Claude call fails.
        fallback_action: Returned as-is if the Claude call fails.

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
        response = await _get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            timeout=10.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        parsed = json.loads(text)
        reasoning = parsed.get("reasoning") or fallback_reasoning
        action = parsed.get("suggested_action") or fallback_action
        return reasoning, action
    except Exception as exc:
        logger.warning("Scenario %d reasoning call failed, using fallback: %s", scenario_num, exc)
        return fallback_reasoning, fallback_action
