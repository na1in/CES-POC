"""
Scenario 5: Duplicate Payment Detection

Entry condition (set by router): is_duplicate_match = True.
Scenario 5 runs first on every payment — before any other scenario.

Match criteria (already verified by duplicate.py):
  - 3 exact fields: sender_name, payment_method, policy_reference
  - Amount within $2 tolerance (200 cents)
  - Within configured duplicate_window_hours (default 72h)

Paths:
  HOLD     — outstanding_balance_cents > 0 (balance may justify second payment)
  ESCALATE — outstanding_balance_cents = 0 (no justification for duplicate)

context keys expected:
  customer_id: str | None
  policy_id: str | None
  policy_number: str | None
"""
from app.services.agent.reasoning import get_reasoning

_SCENARIO = 5


def _decide(signals: dict) -> tuple[str, float, str, str]:
    """Returns (recommendation, confidence, approval_reason, decision_path)."""
    balance = signals.get("outstanding_balance_cents", 0) or 0
    hours = float(signals.get("hours_since_duplicate") or 0)
    diff_cents = signals.get("duplicate_amount_difference", 0) or 0
    orig_id = signals.get("duplicate_payment_id") or "unknown"

    diff_dollars = diff_cents / 100

    if balance > 0:
        balance_dollars = balance / 100
        return (
            "HOLD", 60.0,
            f"Potential duplicate of {orig_id} ({hours:.1f}h ago, ±${diff_dollars:.2f}) "
            f"but outstanding balance of ${balance_dollars:.2f} may justify payment",
            "scenario_5_hold_balance_justifies",
        )

    return (
        "ESCALATE", 0.0,
        f"Duplicate of {orig_id} detected {hours:.1f}h ago (amount diff: ${diff_dollars:.2f}) — policy has $0 outstanding balance",
        "scenario_5_escalate_true_duplicate",
    )


async def run(payment: dict, signals: dict, context: dict, thresholds: dict) -> dict:
    recommendation, confidence, approval_reason, decision_path = _decide(signals)

    orig_id = signals.get("duplicate_payment_id", "unknown")
    hours = signals.get("hours_since_duplicate", 0) or 0
    diff_cents = signals.get("duplicate_amount_difference", 0) or 0
    balance = signals.get("outstanding_balance_cents", 0) or 0
    policy_number = context.get("policy_number", "unknown")

    context_summary = (
        f"- Original payment: {orig_id} ({hours:.1f} hours ago)\n"
        f"- Current payment: {payment.get('payment_id')}\n"
        f"- Amount difference: ${diff_cents / 100:.2f} (within $2.00 tolerance)\n"
        f"- Match on: sender name, payment method, policy reference\n"
        f"- Policy: {policy_number}\n"
        f"- Outstanding balance: ${balance / 100:.2f}"
    )

    fallback_reasoning = [
        f"Duplicate match detected: payment {orig_id} was received {hours:.1f} hours ago",
        f"All three critical fields match: sender name, payment method, and policy reference",
        f"Amount difference: ${diff_cents / 100:.2f} (within $2.00 tolerance)",
        f"Outstanding balance: ${balance / 100:.2f} — {'may justify payment' if balance > 0 else 'no justification for second payment'}",
    ]
    fallback_action = (
        "Hold and contact customer to clarify whether second payment was intentional"
        if recommendation == "HOLD"
        else "Escalate as likely duplicate — contact customer immediately to prevent double charge"
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
