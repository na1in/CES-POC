import json
import logging

import jellyfish

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy Anthropic client (same pattern as ingest.py)
_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _deterministic_score(a: str, b: str) -> float:
    """Hybrid of Jaro-Winkler (50%), Levenshtein (30%), Soundex bonus (10%), normalised to 100."""
    a, b = a.strip().lower(), b.strip().lower()
    if not a or not b:
        return 0.0

    jw = jellyfish.jaro_winkler_similarity(a, b) * 100
    max_len = max(len(a), len(b))
    lev = (1 - jellyfish.levenshtein_distance(a, b) / max_len) * 100 if max_len > 0 else 100.0
    sdx = jellyfish.soundex(a) == jellyfish.soundex(b)

    raw = jw * 0.5 + lev * 0.3 + (10.0 if sdx else 0.0)
    # Scale so max possible (100*0.5 + 100*0.3 + 10) = 90 → normalise to 100
    return min(raw / 0.9, 100.0)


async def _llm_score(a: str, b: str) -> float | None:
    """Call Claude Haiku for gray-zone names. Returns 0-100 or None on failure."""
    prompt = (
        f"Are these two names likely the same person?\n"
        f"Name A: {a}\nName B: {b}\n"
        "Consider nicknames, middle names, abbreviations, and cultural variations.\n"
        'Return JSON only: {"score": 0-100, "reasoning": "one sentence"}'
    )
    try:
        response = await _get_client().messages.create(
            model="claude-haiku-4-5",
            max_tokens=128,
            timeout=3.0,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = json.loads(response.content[0].text.strip())
        return float(parsed["score"])
    except Exception as exc:
        logger.warning("LLM name match failed, using deterministic score: %s", exc)
        return None


async def compute_name_similarity(
    sender_name: str,
    customer_name: str,
    gray_zone_lower: float = 70.0,
    gray_zone_upper: float = 92.0,
) -> dict:
    """
    Returns a dict with all algorithm breakdown fields ready to store in payment_signals.
    """
    a = sender_name.strip().lower()
    b = customer_name.strip().lower()

    jw = jellyfish.jaro_winkler_similarity(a, b) * 100
    max_len = max(len(a), len(b))
    lev = (1 - jellyfish.levenshtein_distance(a, b) / max_len) * 100 if max_len > 0 else 100.0
    sdx = jellyfish.soundex(a) == jellyfish.soundex(b)

    raw = jw * 0.5 + lev * 0.3 + (10.0 if sdx else 0.0)
    det_score = min(raw / 0.9, 100.0)

    used_llm = False
    llm_score = None
    final_score = det_score

    if gray_zone_lower <= det_score <= gray_zone_upper:
        llm_score = await _llm_score(sender_name, customer_name)
        if llm_score is not None:
            used_llm = True
            final_score = max(det_score, llm_score)

    return {
        "jaro_winkler_score": round(jw, 2),
        "levenshtein_score": round(lev, 2),
        "soundex_match": sdx,
        "deterministic_score": round(det_score, 2),
        "used_llm": used_llm,
        "llm_score": round(llm_score, 2) if llm_score is not None else None,
        "name_similarity_score": round(final_score, 2),
    }
