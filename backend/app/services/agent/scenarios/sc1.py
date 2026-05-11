"""
Scenario 1: Strong Policy Match

Entry condition (set by router): policy reference present, name ≥ 75%, variance ≤ 2%.

Paths:
  APPLY (no approval)  — name > 90%, variance ≤ 2%, no risk flags, active account, low-risk method
  HOLD (approval req.) — name 75–90%  OR  risk flags present  OR  high-risk payment method
  ESCALATE             — safety net only; router should have filtered these out

context keys expected:
  customer_id: str | None
  policy_id: str | None
  policy_number: str | None
  customer_name: str | None
"""
from app.services.agent.reasoning import get_reasoning

_SCENARIO = 1


def _decide(signals: dict, thresholds: dict) -> tuple[str, float, bool, str | None, str]:
    """Pure decision logic — no I/O."""
    name_score = float(signals.get("name_similarity_score", 0))
    variance = abs(float(signals.get("amount_variance_pct", 0)))
    has_risk = signals.get("has_risk_flags", False)
    account_status = signals.get("account_status", "inactive")
    method_risk = signals.get("payment_method_risk_level", "high")

    name_auto = float(thresholds.get("name_match_auto_apply", 90))
    name_hold = float(thresholds.get("name_match_hold", 75))
    amount_tol = float(thresholds.get("amount_tolerance_auto", 2))

    is_auto_apply = (
        name_score > name_auto
        and variance <= amount_tol
        and not has_risk
        and account_status == "active"
        and method_risk == "low"
    )

    if is_auto_apply:
        confidence = min(100.0, 85.0 + name_score * 0.15)
        return "APPLY", confidence, False, None, "scenario_1_auto_apply"

    if name_score >= name_hold:
        if has_risk:
            reason = "Risk flags present — requires analyst review before applying"
            path = "scenario_1_hold_risk_flags"
            confidence = 60.0
        elif method_risk in ("medium", "high"):
            reason = f"Payment method risk level is {method_risk} — requires verification"
            path = "scenario_1_hold_high_risk_method"
            confidence = 65.0
        elif account_status != "active":
            reason = f"Account status is {account_status} — cannot auto-apply"
            path = "scenario_1_hold_inactive_account"
            confidence = 60.0
        else:
            # Name in gray zone 75–90%
            confidence = 60.0 + (name_score - name_hold) / (name_auto - name_hold) * 20.0
            reason = f"Name similarity {name_score:.0f}% is below auto-apply threshold ({name_auto:.0f}%) — requires approval"
            path = "scenario_1_hold_gray_zone_name"
        return "HOLD", confidence, True, reason, path

    return "ESCALATE", 20.0, True, "Name similarity below minimum threshold", "scenario_1_escalate_low_name"


async def run(payment: dict, signals: dict, context: dict, thresholds: dict) -> dict:
    recommendation, confidence, requires_approval, approval_reason, decision_path = _decide(
        signals, thresholds
    )

    policy_number = context.get("policy_number", "unknown")
    customer_name = context.get("customer_name", "unknown")
    name_score = signals.get("name_similarity_score", 0)
    variance = signals.get("amount_variance_pct", 0)

    context_summary = (
        f"- Sender: {payment.get('sender_name')} vs policyholder: {customer_name} (similarity: {name_score:.0f}%)\n"
        f"- Policy reference: {policy_number}\n"
        f"- Amount variance: {variance:.1f}%\n"
        f"- Risk flags: {signals.get('has_risk_flags', False)}\n"
        f"- Account status: {signals.get('account_status', 'unknown')}\n"
        f"- Payment method risk: {signals.get('payment_method_risk_level', 'unknown')}"
    )

    fallback_reasoning = [
        f"Policy {policy_number} matched in payment reference",
        f"Name similarity: {name_score:.0f}% ({payment.get('sender_name')} vs {customer_name})",
        f"Amount variance: {variance:.1f}%",
        f"Recommendation: {recommendation} — {approval_reason or 'all criteria met'}",
    ]
    fallback_action = (
        f"Apply payment to policy {policy_number}"
        if recommendation == "APPLY"
        else f"Review payment for policy {policy_number} and approve or reject"
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
