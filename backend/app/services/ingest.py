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


async def parse_reference_fields(ref1: str | None, ref2: str | None) -> dict:
    """
    Uses Gemini Flash via OpenRouter to extract structured data from free-text
    reference fields. Returns defaults on any failure — never raises.
    """
    defaults = {"extracted_policy_number": None, "payment_intent": "unknown", "period_count": 1}

    combined = " ".join(filter(None, [ref1, ref2])).strip()
    if not combined:
        return defaults

    prompt = f"""Extract structured payment reference data from this text.

Reference text: "{combined}"

Return a JSON object with exactly these fields:
- extracted_policy_number: string matching pattern POL-XXXXX, or null if not found
- payment_intent: one of "premium", "arrears", "partial", "unknown"
- period_count: integer number of payment periods mentioned (default 1)

Return only valid JSON, no explanation."""

    try:
        response = await _get_client().chat.completions.create(
            model=_MODEL,
            max_tokens=256,
            timeout=3.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:-1])
        parsed = json.loads(text)
        return {
            "extracted_policy_number": parsed.get("extracted_policy_number") or None,
            "payment_intent": parsed.get("payment_intent", "unknown"),
            "period_count": int(parsed.get("period_count", 1)),
        }
    except Exception as exc:
        logger.warning("Reference parse failed, using defaults: %s", exc)
        return defaults
