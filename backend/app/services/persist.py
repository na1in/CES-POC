"""
CES-23: Persist Layer

Single-transaction save of the AI agent recommendation. Caller owns the
transaction and must commit (or roll back) after this function returns.

Transaction steps:
  1. INSERT payment_recommendations
  2. UPDATE payments — status, matched IDs, investigation_due_date
  3. Auto-apply ledger (only when recommendation=APPLY and no approval needed):
       INSERT payment_history + UPDATE policy outstanding_balance
  4. INSERT audit_log (recommendation_made)
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Default SLA window for escalated payments (hours until Damien's deadline).
# Overridden by CES-27 (sla.py) once that service is built.
_SLA_HOURS = 72


def _target_status(recommendation: str, requires_human_approval: bool) -> str:
    """
    Every payment lands in 'held' for Priya to review — no auto-apply.
    Human approval is always required regardless of match quality.
    """
    return "held"


async def persist_recommendation(
    payment_id: str,
    payment: dict,
    recommendation: dict,
    processing_time_ms: int,
    db: AsyncSession,
) -> None:
    """
    Persist the recommendation in a single logical transaction block.
    Does NOT commit — caller is responsible.

    payment keys used: amount, payment_method, payment_date, sender_account
    recommendation keys: recommendation, confidence_score, scenario_route,
        decision_path, requires_human_approval, approval_reason, reasoning,
        suggested_action, matched_policy_id, matched_customer_id
    """
    rec = recommendation["recommendation"]          # "APPLY" / "HOLD" / "ESCALATE"
    requires_approval = recommendation.get("requires_human_approval", True)
    status = _target_status(rec, requires_approval)

    scenario_num = recommendation.get("scenario_route", 1)
    scenario_route_val = f"scenario_{scenario_num}"
    rec_lower = rec.lower()

    now = datetime.now(timezone.utc)
    investigation_due_date = (now + timedelta(hours=_SLA_HOURS)) if status == "escalated" else None

    # ── 1. INSERT payment_recommendations ─────────────────────────────────────
    # reasoning is TEXT[] in Postgres — pass as a Python list; asyncpg handles it.
    await db.execute(text("""
        INSERT INTO payment_recommendations (
            payment_id, recommendation, confidence_score, scenario_route,
            decision_path, requires_human_approval, approval_reason,
            reasoning, suggested_action, processing_time_ms,
            decision_attribution, created_at
        ) VALUES (
            :payment_id,
            CAST(:recommendation AS recommendation),
            :confidence_score,
            CAST(:scenario_route AS scenario_route),
            :decision_path,
            :requires_human_approval,
            :approval_reason,
            :reasoning,
            :suggested_action,
            :processing_time_ms,
            NULL,
            :created_at
        )
    """), {
        "payment_id": payment_id,
        "recommendation": rec_lower,
        "confidence_score": recommendation.get("confidence_score", 0.0),
        "scenario_route": scenario_route_val,
        "decision_path": recommendation.get("decision_path"),
        "requires_human_approval": requires_approval,
        "approval_reason": recommendation.get("approval_reason"),
        "reasoning": recommendation.get("reasoning") or [],
        "suggested_action": recommendation.get("suggested_action"),
        "processing_time_ms": processing_time_ms,
        "created_at": now,
    })

    # ── 2. UPDATE payments ─────────────────────────────────────────────────────
    await db.execute(text("""
        UPDATE payments SET
            status                 = CAST(:status AS payment_status),
            matched_customer_id    = :matched_customer_id,
            matched_policy_id      = :matched_policy_id,
            investigation_due_date = :investigation_due_date
        WHERE payment_id = :payment_id
    """), {
        "payment_id": payment_id,
        "status": status,
        "matched_customer_id": recommendation.get("matched_customer_id"),
        "matched_policy_id": recommendation.get("matched_policy_id"),
        "investigation_due_date": investigation_due_date,
    })

    # ── 3. Auto-apply ledger ───────────────────────────────────────────────────
    if status == "applied":
        matched_policy_id = recommendation.get("matched_policy_id")
        if matched_policy_id:
            await db.execute(text("""
                INSERT INTO payment_history (
                    policy_id, payment_date, amount, payment_method, sender_account, status
                ) VALUES (
                    :policy_id, :payment_date, :amount, :payment_method, :sender_account, 'applied'
                )
            """), {
                "policy_id": matched_policy_id,
                "payment_date": payment.get("payment_date") or now,
                "amount": payment.get("amount", 0),
                "payment_method": payment.get("payment_method", ""),
                "sender_account": payment.get("sender_account"),
            })

            await db.execute(text("""
                UPDATE policies
                SET outstanding_balance = GREATEST(0, outstanding_balance - :amount),
                    modified_date = now()
                WHERE policy_number = :policy_number
            """), {
                "policy_number": matched_policy_id,
                "amount": payment.get("amount", 0),
            })

    # ── 4. INSERT audit_log ────────────────────────────────────────────────────
    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, details, timestamp)
        VALUES (
            :payment_id,
            'recommendation_made',
            'system',
            CAST(:details AS jsonb),
            :timestamp
        )
    """), {
        "payment_id": payment_id,
        "details": json.dumps({
            "recommendation": rec,
            "confidence_score": recommendation.get("confidence_score"),
            "scenario_route": scenario_route_val,
            "decision_path": recommendation.get("decision_path"),
            "auto_applied": status == "applied",
        }),
        "timestamp": now,
    })

    logger.info(
        "Persisted recommendation for %s: %s → status=%s scenario=%s",
        payment_id, rec, status, scenario_route_val,
    )
