"""
Experiment-only reference parsers, so the evaluation can price and measure an LLM parser even though production no
longer has one. Nothing here is imported by backend/app.

  llm_parse        The parser production used until 2026-09-26: a single Gemini call with the prompt, model, limits and
                   failure behaviour copied from backend/app/services/ingest.py at commit 9390122 (results are used as
                   returned, un-normalised, exactly as production used them).
  regex_then_llm   The "keep the LLM as a fallback" design: the app's own deterministic parser first; only when it finds
                   no policy number is the LLM asked. The LLM's answer is accepted only if it is a well-formed policy
                   number (POL-XXXXX or POL XXXXX) whose five digits appear in the text, and is normalised to POL-XXXXX,
                   so the fallback cannot invent a policy number.

Used by run_eval.py --llm parse-llm | parse-fallback. run_eval wraps _get_client to record tokens and time.
"""
import json
import logging
import re

import openai

from app.config import settings
from app.services.ingest import parse_reference_fields as regex_parse  # the app's deterministic parser

logger = logging.getLogger(__name__)

_MODEL = "google/gemini-2.5-flash"
_client: openai.AsyncOpenAI | None = None


def _get_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=settings.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    return _client


async def llm_parse(ref1: str | None, ref2: str | None) -> dict:
    """Verbatim behaviour of the production parser at commit 9390122. Returns defaults on any failure."""
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
            timeout=10.0,
            messages=[{"role": "user", "content": prompt}],
            extra_body={"thinking": {"type": "disabled"}},
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
    except Exception as exc:  # noqa: BLE001 - production swallowed everything and used the defaults
        logger.warning("Reference parse failed, using defaults: %s", exc)
        return defaults


_WELL_FORMED = re.compile(r"(?i)^\s*pol[-\s]?(\d{5})\s*$")


async def regex_then_llm(ref1: str | None, ref2: str | None) -> dict:
    """Regex first; the LLM only when the regex finds nothing (and there is text to read)."""
    result = await regex_parse(ref1, ref2)
    if result["extracted_policy_number"] is not None:
        return result
    combined = " ".join(filter(None, [ref1, ref2])).strip()
    if not combined:
        return result

    answer = (await llm_parse(ref1, ref2)).get("extracted_policy_number")
    match = _WELL_FORMED.match(str(answer)) if answer else None
    if match and match.group(1) in combined:  # the digits must be in the text: no invented numbers
        return {**result, "extracted_policy_number": f"POL-{match.group(1)}"}
    return result
