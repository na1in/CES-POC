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


async def parse_reference_fields(ref1: str | None, ref2: str | None) -> dict:
    """
    Uses Claude Haiku to extract structured data from free-text reference fields.
    Returns defaults on any failure — never raises.
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
        response = await _get_client().messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            timeout=3.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        parsed = json.loads(text)
        return {
            "extracted_policy_number": parsed.get("extracted_policy_number") or None,
            "payment_intent": parsed.get("payment_intent", "unknown"),
            "period_count": int(parsed.get("period_count", 1)),
        }
    except Exception as exc:
        logger.warning("Reference parse failed, using defaults: %s", exc)
        return defaults
