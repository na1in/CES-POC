"""
Scenario 4: No Matching Customer

Entry condition (set by router): name similarity < 75% — no customer match found.

Paths:
  HOLD     — third-party payment detected AND a valid policy exists AND amount variance ≤ 15%
  ESCALATE — all other cases (no match, third-party without valid policy, high variance)

context keys expected:
  customer_id: str | None    — best fuzzy match found, if any
  customer_name: str | None  — best fuzzy match name
  policy_id: str | None      — if a policy reference was found in payment
"""
from app.services.agent.reasoning import get_reasoning

_SCENARIO = 4
_MAX_VARIANCE_FOR_THIRD_PARTY_HOLD = 15.0


def _decide(
    signals: dict,
    context: dict,
    thresholds: dict,
) -> tuple[str, float, str | None, str]:
    """Returns (recommendation, confidence, approval_reason, decision_path)."""
    name_score = float(signals.get("name_similarity_score", 0))
    is_third_party = signals.get("is_third_party_payment", False)
    third_party_rel = signals.get("third_party_relationship") or "unknown"
    variance = abs(float(signals.get("amount_variance_pct") or 0))
    has_policy = bool(context.get("policy_id"))

    # Third-party check first: valid policy + detected third-party pattern + reasonable amount
    if is_third_party and has_policy and variance <= _MAX_VARIANCE_FOR_THIRD_PARTY_HOLD:
        return (
            "HOLD", 50.0,
            f"Third-party payment detected ({third_party_rel}) — verify sender relationship to policyholder",
            "scenario_4_hold_third_party",
        )

    # No match — escalate
    return (
        "ESCALATE", 10.0,
        f"No matching customer found (best similarity: {name_score:.0f}%) — manual investigation required",
        "scenario_4_escalate_no_match",
    )


async def run(payment: dict, signals: dict, context: dict, thresholds: dict) -> dict:
    recommendation, confidence, approval_reason, decision_path = _decide(
        signals, context, thresholds
    )

    name_score = signals.get("name_similarity_score", 0)
    best_match_name = context.get("customer_name", "none found")
    is_third_party = signals.get("is_third_party_payment", False)
    third_party_rel = signals.get("third_party_relationship", "N/A")

    context_summary = (
        f"- Sender: {payment.get('sender_name')}\n"
        f"- Best customer match: {best_match_name} ({name_score:.0f}% similarity) — below 75% threshold\n"
        f"- Third-party indicator: {is_third_party} ({third_party_rel})\n"
        f"- Policy reference found: {bool(context.get('policy_id'))}\n"
        f"- Amount variance: {signals.get('amount_variance_pct') or 0:.1f}%\n"
        f"- Payment method: {payment.get('payment_method', 'unknown')}"
    )

    fallback_reasoning = [
        f"No customer match found for '{payment.get('sender_name')}' (best match: {name_score:.0f}%)",
        f"Minimum threshold for matching is 75%",
        f"Third-party indicator: {is_third_party}",
        f"Recommendation: {recommendation} — {approval_reason}",
    ]
    fallback_action = (
        "Hold for analyst to verify third-party relationship to policyholder"
        if recommendation == "HOLD"
        else "Escalate to investigation queue — contact sender to identify intent"
    )

    reasoning, suggested_action = await get_reasoning(
        _SCENARIO, recommendation, context_summary, fallback_reasoning, fallback_action
    )

    return {
        "recommendation": recommendation,
        "confidence_score": round(confidence, 1),
        "scenario_route": _SCENARIO,
        "decision_path": decision_path,
        "requires_human_approval": True,
        "approval_reason": approval_reason,
        "reasoning": reasoning,
        "suggested_action": suggested_action,
        "matched_policy_id": context.get("policy_id"),
        "matched_customer_id": context.get("customer_id"),
    }
