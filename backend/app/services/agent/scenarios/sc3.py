"""
Scenario 3: High Amount Variance

Entry condition (set by router): name ≥ 75%, variance > 2%.

Variance tiers:
  Tier 2 (2–15%)   → APPLY with approval
  Tier 3 (15–50%)  → HOLD; special cases (multi-period, multi-method, third-party) still HOLD
  Tier 4 (50–100%) → HOLD; special cases still HOLD
  Tier 5 (>100%)   → ESCALATE

Name check: name must be ≥ 90% (name_match_auto_apply threshold).
If name < 90%, escalate — name mismatch overrides the variance path.

context keys expected:
  customer_id: str | None
  policy_id: str | None
  policy_number: str | None
  customer_name: str | None
"""
from app.services.agent.reasoning import get_reasoning

_SCENARIO = 3


def _variance_tier(variance_pct: float) -> int:
    if variance_pct <= 2:
        return 1
    elif variance_pct <= 15:
        return 2
    elif variance_pct <= 50:
        return 3
    elif variance_pct <= 100:
        return 4
    return 5


def _decide(signals: dict, thresholds: dict) -> tuple[str, float, bool, str | None, str]:
    """Returns (recommendation, confidence, requires_approval, approval_reason, decision_path)."""
    name_score = float(signals.get("name_similarity_score", 0))
    variance = abs(float(signals.get("amount_variance_pct") or 0))
    is_multi_period = signals.get("is_multi_period", False)
    is_multi_method = signals.get("is_multi_method", False)
    is_third_party = signals.get("is_third_party_payment", False)
    third_party_rel = signals.get("third_party_relationship") or "unknown"
    estimated_periods = signals.get("estimated_periods", 0)
    multi_method_fraction = signals.get("multi_method_fraction", 0)

    name_auto = float(thresholds.get("name_match_auto_apply", 90))

    # Name must be ≥ 90% for S3 to apply normally
    if name_score < name_auto:
        return (
            "ESCALATE", 20.0, True,
            f"Name similarity {name_score:.0f}% is below 90% — cannot confirm identity for variance review",
            "scenario_3_escalate_name_mismatch",
        )

    tier = _variance_tier(variance)

    if tier <= 1:
        # Shouldn't reach here from router, but handle it
        return "APPLY", 90.0, False, None, "scenario_3_apply_within_tolerance"

    if tier == 2:
        return (
            "APPLY", 88.0, True,
            f"Minor amount variance of {variance:.1f}% requires analyst verification",
            "scenario_3_apply_tier2_minor_variance",
        )

    # Tiers 3 and 4: check special cases
    if tier in (3, 4):
        if is_multi_period:
            return (
                "HOLD", 65.0, True,
                f"Possible multi-period payment (~{estimated_periods}x premium) — analyst must verify intent",
                "scenario_3_hold_multi_period",
            )
        if is_multi_method:
            return (
                "HOLD", 62.0, True,
                f"Possible split payment ({multi_method_fraction:.2f}x of premium across payment methods)",
                "scenario_3_hold_multi_method",
            )
        if is_third_party:
            return (
                "HOLD", 60.0, True,
                f"Third-party payment detected ({third_party_rel}) — verify sender-to-policyholder relationship",
                "scenario_3_hold_third_party",
            )
        confidence = 65.0 if tier == 3 else 48.0
        return (
            "HOLD", confidence, True,
            f"Amount variance of {variance:.1f}% requires investigation",
            f"scenario_3_hold_tier{tier}_variance",
        )

    # Tier 5: extreme variance
    return (
        "ESCALATE", 20.0, True,
        f"Extreme variance of {variance:.1f}% — potential fraud or major processing error",
        "scenario_3_escalate_tier5_extreme",
    )


async def run(payment: dict, signals: dict, context: dict, thresholds: dict) -> dict:
    recommendation, confidence, requires_approval, approval_reason, decision_path = _decide(
        signals, thresholds
    )

    policy_number = context.get("policy_number", "unknown")
    customer_name = context.get("customer_name", "unknown")
    name_score = signals.get("name_similarity_score", 0)
    variance = signals.get("amount_variance_pct") or 0

    context_summary = (
        f"- Sender: {payment.get('sender_name')} vs policyholder: {customer_name} (similarity: {name_score:.0f}%)\n"
        f"- Policy: {policy_number}\n"
        f"- Amount variance: {variance:.1f}%\n"
        f"- Multi-period: {signals.get('is_multi_period')} (estimated {signals.get('estimated_periods', 0)} periods)\n"
        f"- Multi-method: {signals.get('is_multi_method')} (fraction: {signals.get('multi_method_fraction', 0):.2f})\n"
        f"- Third-party: {signals.get('is_third_party_payment')} ({signals.get('third_party_relationship', 'N/A')})\n"
        f"- Historical consistency: {signals.get('historical_consistency_score', 0):.0f}%"
    )

    fallback_reasoning = [
        f"Policy {policy_number} matched, name similarity {name_score:.0f}%",
        f"Amount variance: {variance:.1f}% — {approval_reason or 'see context'}",
        f"Recommendation: {recommendation}",
    ]
    fallback_action = (
        "Verify amount intent with customer and apply to policy once confirmed"
        if recommendation in ("APPLY", "HOLD")
        else "Escalate to investigation queue for fraud review and customer contact"
    )

    reasoning, suggested_action = await get_reasoning(
        _SCENARIO, recommendation, context_summary, fallback_reasoning, fallback_action
    )

    return {
        "recommendation": recommendation,
        "confidence_score": round(confidence, 1),
        "scenario_route": _SCENARIO,
        "decision_path": decision_path,
        "requires_human_approval": requires_approval,
        "approval_reason": approval_reason,
        "reasoning": reasoning,
        "suggested_action": suggested_action,
        "matched_policy_id": context.get("policy_id"),
        "matched_customer_id": context.get("customer_id"),
    }
