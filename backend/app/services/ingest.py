"""
Reference-field parsing: pull the policy number out of the free-text payment references.

This is deterministic (regex), not an LLM call. The evaluation harness measured a regex matching or beating the LLM
parser on policy-number extraction, with none of its failure modes (un-normalised output such as POL90001, missed
plain references, timeouts, run-to-run variation) and without sending reference text to a third party. A pure function
also means the ingest-time parse and the pipeline's parse can never disagree (finding F2).

Output is always normalised to POL-XXXXX. payment_intent and period_count are kept in the return shape for
compatibility but nothing downstream reads them (multi-period detection is computed from amounts in signals/amount.py),
so they carry their defaults.
"""
import logging
import re

logger = logging.getLogger(__name__)

# "POL-90001", "POL90001", "pol 90003", "Policy #90014", "policy no. 90014", "policy number: 90014", "Pol.93010", "P0L-90001".
# The keyword may not run into letters (so "police" / "policyholder" do not match); the number is exactly 5 digits.
_POLICY_RE = re.compile(
    r"(?i)\bp[o0]l(?:icy)?(?![a-z])[\s\-#:.]*(?:(?:no|number|num)\b\.?[\s\-#:.]*)?(\d{5})(?!\d)"
)
_FIVE_DIGITS_RE = re.compile(r"(?<!\d)\d{5}(?!\d)")


async def parse_reference_fields(ref1: str | None, ref2: str | None) -> dict:
    """
    Returns {"extracted_policy_number": "POL-XXXXX" | None, "payment_intent": "unknown", "period_count": 1}. Never raises.

    If the text names two or more different policy numbers the payment is deliberately left unmatched (None) so an
    analyst chooses, instead of silently taking the first.
    """
    result = {"extracted_policy_number": None, "payment_intent": "unknown", "period_count": 1}

    combined = " ".join(filter(None, [ref1, ref2])).strip()
    if not combined:
        return result

    numbers = {m.group(1) for m in _POLICY_RE.finditer(combined)}
    if len(numbers) == 1:
        result["extracted_policy_number"] = f"POL-{next(iter(numbers))}"
    elif len(numbers) > 1:
        logger.info("Reference names %d different policy numbers; leaving the payment unmatched for an analyst", len(numbers))
    elif _FIVE_DIGITS_RE.search(combined):
        # Signal for spotting reference formats the pattern does not cover yet (the text itself is not logged).
        logger.info("Reference contains a 5-digit number but no policy-number pattern matched")
    return result
