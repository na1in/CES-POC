"""
Scenario 2: Customer Match, No Policy Reference

Entry condition (set by router): name ≥ 75%, variance ≤ 2%, no policy reference extracted.

All paths require human approval.

The strong-match test is the name similarity score (spec: "name match ≥90%: strong match"). The blended
customer_match_confidence is not used for it: it caps an exact name at 60 unless account AND history also match, so a
missing sender account vetoed a 100% name match. Account/amount/history signals only support the <90% path.

Amount variance: with no policy identified the signal engine has no premium, so amount_variance_pct is None here. The
variance is then taken from the customer's active policies (the single policy, or the policy the amount matches).
When it still cannot be computed the payment is HELD, not applied: a missing variance used to be read as 0%, which
could APPLY a payment far below premium (finding F3). For the same reason amount_match, a supporting signal the signal
engine can never set in this scenario, is derived here from the active policies' premiums.

Risk flags: an APPLY for a customer with risk flags becomes HOLD, as in Scenario 1 ("risk flag present → HOLD
regardless of other scores"). The Scenario 2 specification did not say; without this a flagged customer paying with no
policy reference could be recommended for APPLY.

Paths:
  APPLY (approval req.) — strong customer match (≥90%) + single policy OR amount disambiguates
                          OR weak match + 2+ supporting signals + single policy
                          (unless the customer has risk flags → HOLD)
  HOLD                  — multiple policies can't be disambiguated, OR variance > 15%, OR variance can't be computed,
                          OR risk flags
  ESCALATE              — weak match + fewer than 2 supporting signals

context keys expected:
  customer_id: str | None
  customer_name: str | None
  active_policy_count: int          — number of active policies for this customer
  active_policies: list[dict]       — each: {policy_id, policy_number, premium_amount_cents}
"""
from app.services.agent.reasoning import get_reasoning

_SCENARIO = 2
_MAX_VARIANCE_FOR_APPLY = 15.0


def _policy_variance(payment_amount_cents: int, policy: dict) -> float | None:
    """Percent variance of the payment from one policy's premium, or None if the premium is unknown."""
    premium = policy.get("premium_amount_cents") or 0
    if premium <= 0:
        return None
    return abs(payment_amount_cents - premium) / premium * 100


def _matching_policies(payment_amount_cents: int, active_policies: list[dict]) -> list[dict]:
    """Policies whose premium is within 15% of the payment amount."""
    result = []
    for p in active_policies:
        variance = _policy_variance(payment_amount_cents, p)
        if variance is not None and variance <= _MAX_VARIANCE_FOR_APPLY:
            result.append(p)
    return result


def _decide(
    payment: dict,
    signals: dict,
    context: dict,
    thresholds: dict,
) -> tuple[str, float, str | None, str, str | None]:
    """
    Returns (recommendation, confidence, approval_reason, decision_path, matched_policy_id).
    """
    recommendation, confidence, reason, path, policy_id = _decide_by_match(payment, signals, context, thresholds)
    if recommendation == "APPLY" and signals.get("has_risk_flags"):
        return (
            "HOLD", 60.0,
            "Risk flags present — requires analyst review before applying",
            "scenario_2_hold_risk_flag",
            policy_id,
        )
    return recommendation, confidence, reason, path, policy_id


def _decide_by_match(
    payment: dict,
    signals: dict,
    context: dict,
    thresholds: dict,
) -> tuple[str, float, str | None, str, str | None]:
    name_score = float(signals.get("name_similarity_score", 0))
    account_match = bool(signals.get("account_match", False))
    historical_match = bool(signals.get("historical_match", False))

    name_auto = float(thresholds.get("name_match_auto_apply", 90))
    amount_tol = float(thresholds.get("amount_tolerance_auto", 2))

    active_policy_count = context.get("active_policy_count", 0)
    active_policies = context.get("active_policies") or []
    payment_amount_cents = payment.get("amount", 0)

    policy_variances = [v for v in (_policy_variance(payment_amount_cents, p) for p in active_policies) if v is not None]

    # Variance from the signal engine when a policy was identified, otherwise from the customer's own policy.
    signal_variance = signals.get("amount_variance_pct")
    if signal_variance is not None:
        variance: float | None = abs(float(signal_variance))
    elif active_policy_count == 1 and active_policies:
        variance = _policy_variance(payment_amount_cents, active_policies[0])
    else:
        variance = None

    amount_match = bool(signals.get("amount_match", False)) or (bool(policy_variances) and min(policy_variances) <= amount_tol)
    supporting_count = sum([account_match, amount_match, historical_match])

    matched_policy_id: str | None = None

    if name_score >= name_auto:
        # Strong customer match path
        if active_policy_count == 1:
            if variance is None:
                return (
                    "HOLD", 65.0,
                    "Amount cannot be verified — the policy premium is unknown",
                    "scenario_2_hold_amount_unverified",
                    None,
                )
            if variance <= _MAX_VARIANCE_FOR_APPLY:
                matched_policy_id = active_policies[0].get("policy_id") if active_policies else None
                return (
                    "APPLY", 85.0,
                    "Policy number not provided — requires analyst verification",
                    "scenario_2_apply_single_policy",
                    matched_policy_id,
                )
            else:
                return (
                    "HOLD", 70.0,
                    f"Amount variance {variance:.1f}% exceeds 15% threshold for auto-route",
                    "scenario_2_hold_high_variance",
                    None,
                )

        elif active_policy_count > 1:
            matches = _matching_policies(payment_amount_cents, active_policies)
            if len(matches) == 1:
                matched_policy_id = matches[0].get("policy_id")
                match_variance = variance if variance is not None else _policy_variance(payment_amount_cents, matches[0])
                if match_variance is not None and match_variance <= _MAX_VARIANCE_FOR_APPLY:
                    return (
                        "APPLY", 82.0,
                        "Amount uniquely identifies one policy — requires analyst verification",
                        "scenario_2_apply_amount_disambiguates",
                        matched_policy_id,
                    )
                else:
                    return (
                        "HOLD", 68.0,
                        "Amount matches one policy but variance is high",
                        "scenario_2_hold_amount_match_high_variance",
                        None,
                    )
            else:
                return (
                    "HOLD", 72.0,
                    f"Customer has {active_policy_count} active policies — analyst must select correct one",
                    "scenario_2_hold_ambiguous_policies",
                    None,
                )

        else:
            return (
                "HOLD", 65.0,
                "No active policies found for matched customer",
                "scenario_2_hold_no_active_policies",
                None,
            )

    else:
        # Weak match — need supporting signals
        if supporting_count >= 2:
            if active_policy_count == 1 and variance is not None and variance <= _MAX_VARIANCE_FOR_APPLY:
                matched_policy_id = active_policies[0].get("policy_id") if active_policies else None
                return (
                    "APPLY", 75.0,
                    f"Weak name match compensated by {supporting_count} supporting signals",
                    "scenario_2_apply_supporting_signals",
                    matched_policy_id,
                )
            else:
                return (
                    "HOLD", 65.0,
                    "Weak name match with supporting signals but policy selection is ambiguous",
                    "scenario_2_hold_weak_match_ambiguous",
                    None,
                )
        else:
            return (
                "ESCALATE", 35.0,
                f"Insufficient confidence: name match {name_score:.0f}% with only {supporting_count} supporting signal(s)",
                "scenario_2_escalate_insufficient_confidence",
                None,
            )


async def run(payment: dict, signals: dict, context: dict, thresholds: dict) -> dict:
    recommendation, confidence, approval_reason, decision_path, matched_policy_id = _decide(
        payment, signals, context, thresholds
    )

    customer_name = context.get("customer_name", "unknown")
    name_score = signals.get("name_similarity_score", 0)
    active_policy_count = context.get("active_policy_count", 0)
    variance = signals.get("amount_variance_pct")
    variance_text = f"{variance:.1f}%" if variance is not None else "n/a (no policy identified)"

    context_summary = (
        f"- Sender: {payment.get('sender_name')} vs customer: {customer_name} (name similarity: {name_score:.0f}%)\n"
        f"- No policy reference in payment\n"
        f"- Customer has {active_policy_count} active policies\n"
        f"- Amount variance: {variance_text}\n"
        f"- Risk flags: {signals.get('has_risk_flags', False)}\n"
        f"- Supporting signals: account_match={signals.get('account_match')}, "
        f"amount_match={signals.get('amount_match')}, historical_match={signals.get('historical_match')}"
    )

    fallback_reasoning = [
        f"Customer identified as {customer_name} with {name_score:.0f}% name similarity",
        f"No policy reference provided in payment",
        f"Customer has {active_policy_count} active policy/ies",
        f"Recommendation: {recommendation} — {approval_reason or 'see context'}",
    ]
    fallback_action = (
        "Apply payment to identified policy after analyst verification"
        if recommendation == "APPLY"
        else "Hold for analyst to select correct policy and verify customer intent"
        if recommendation == "HOLD"
        else "Escalate — insufficient evidence to identify customer or policy"
    )

    reasoning, suggested_action = await get_reasoning(
        _SCENARIO, recommendation, context_summary, fallback_reasoning, fallback_action
    )

    matched_pid = matched_policy_id or context.get("policy_id")

    return {
        "recommendation": recommendation,
        "confidence_score": round(confidence, 1),
        "scenario_route": _SCENARIO,
        "decision_path": decision_path,
        "requires_human_approval": True,
        "approval_reason": approval_reason,
        "reasoning": reasoning,
        "suggested_action": suggested_action,
        "matched_policy_id": matched_pid,
        "matched_customer_id": context.get("customer_id"),
    }
