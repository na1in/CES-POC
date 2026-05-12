"""
Injects a fully-processed mock payment directly into the DB — bypassing the
LLM pipeline. Use this when the Anthropic API key is not configured.

Usage (from backend/):
    python scripts/inject_mock_payment.py

What it does:
  1. Inserts a payment with status=held (so it appears in the Queue Dashboard)
  2. Inserts matching payment_signals row
  3. Inserts a payment_recommendations row
  4. Inserts 2 audit_log entries (received + held)
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _next_id(db: AsyncSession) -> str:
    result = await db.execute(text("SELECT MAX(payment_id) FROM payments"))
    current = result.scalar_one_or_none()
    if current is None:
        return "PMT-001"
    return f"PMT-{int(current.split('-')[1]) + 1:03d}"


async def inject(db: AsyncSession) -> None:
    payment_id = await _next_id(db)
    now = datetime.now(timezone.utc)
    payment_date = datetime(2026, 5, 10, 9, 0, 0, tzinfo=timezone.utc)

    # 1. Payment — status held so queue dashboard picks it up
    await db.execute(text("""
        INSERT INTO payments (
            payment_id, amount, sender_name, sender_account, beneficiary_name,
            payment_method, payment_date, reference_field_1, reference_field_2,
            status, created_timestamp
        ) VALUES (
            :id, :amount, :sender, :account, :bene,
            :method, :date, :ref1, :ref2,
            'held', :now
        )
    """), {
        "id": payment_id,
        "amount": 125000,
        "sender": "Crestwood Insurance Co.",
        "account": "****9912",
        "bene": "Crestwood Insurance Company",
        "method": "ACH",
        "date": payment_date,
        "ref1": "POL-77201",
        "ref2": "MAY-PREMIUM",
        "now": now,
    })

    # 2. Signals
    await db.execute(text("""
        INSERT INTO payment_signals (
            payment_id, computed_at,
            name_similarity_score, policy_match_confidence, customer_match_confidence,
            account_match, amount_match, historical_match,
            jaro_winkler_score, levenshtein_score, soundex_match,
            deterministic_score, used_llm, llm_score,
            amount_variance_pct, is_overpayment, is_underpayment, difference_amount,
            is_multi_period, estimated_periods, historical_consistency_score,
            is_multi_method, multi_method_fraction,
            is_third_party_payment, third_party_relationship,
            payment_timing_quality, days_from_due_date, days_since_last_payment,
            has_risk_flags, account_status, payment_method_risk_level,
            outstanding_balance_cents, outstanding_balance_status,
            is_duplicate_match, duplicate_payment_id,
            hours_since_duplicate, outstanding_balance_justifies, duplicate_amount_difference
        ) VALUES (
            :id, :now,
            83, 88, 81,
            true, true, true,
            85, 80, true,
            83, true, 83,
            0, false, false, 0,
            false, 1, 92,
            false, 0,
            false, '',
            'good', 1, 30,
            false, 'active', 'low',
            0, 'current',
            false, null,
            0, false, 0
        )
    """), {"id": payment_id, "now": now})

    # 3. Recommendation
    reasoning = [
        "Name similarity 83 — gray zone; LLM raised confidence to 83",
        "Policy reference POL-77201 partially matched",
        "Amount matches expected premium exactly",
        "Below auto-apply threshold (90); requires analyst confirmation",
    ]
    await db.execute(text("""
        INSERT INTO payment_recommendations (
            payment_id, recommendation, confidence_score,
            scenario_route, decision_path,
            requires_human_approval, approval_reason,
            reasoning, suggested_action, processing_time_ms,
            decision_attribution, created_at
        ) VALUES (
            :id, 'hold', 83,
            'scenario_1', 'scenario_1_hold_name_mismatch',
            true, 'Name similarity 83 is below auto-apply threshold (90)',
            :reasoning,
            'Verify sender identity; apply to POL-77201 if confirmed',
            310,
            null, :now
        )
    """), {"id": payment_id, "reasoning": reasoning, "now": now})

    # 4. Audit log
    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, details, timestamp)
        VALUES
            (:id, 'received', 'system',
             CAST('{"source": "ingest_api"}'  AS jsonb), :t1),
            (:id, 'held',     'system',
             CAST('{"reason": "name_mismatch", "confidence_score": 83}' AS jsonb), :t2)
    """), {"id": payment_id, "t1": now, "t2": now})

    await db.commit()
    print(f"Injected {payment_id} — Crestwood Insurance Co. $1,250.00 HOLD (confidence 83)")
    print(f"  → Open http://localhost:3000 to see it in the Queue Dashboard")
    print(f"  → Open http://localhost:3000/payments/{payment_id} for the detail view")


async def main() -> None:
    async with Session() as db:
        await inject(db)
    await engine.dispose()


asyncio.run(main())
