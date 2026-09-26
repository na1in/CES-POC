import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def compute_duplicate(
    db: AsyncSession,
    payment_id: str,
    sender_name: str,
    reference: str | None,
    payment_method: str,
    payment_date: datetime,
    amount: int,
    window_hours: int = 72,
    amount_tolerance_cents: int = 200,
) -> dict:
    """
    Checks for a duplicate payment within the configured window.
    Match criteria (docs/Final_Scenario_Definitions.md, Scenario 5): same sender_name,
    payment_method and policy reference (reference_field_1), within window_hours, amount
    within amount_tolerance_cents.

    The sender's account is deliberately not a criterion: a duplicate can arrive from another
    bank account or card, and the account says nothing about which policy is being paid.
    The reference is compared as written rather than through the LLM reference parser, so this
    check does not inherit the parser's run-to-run variation.
    """
    # The window is symmetric (+/- window_hours around this payment's date): a duplicate can be processed before or
    # after the original, and a payment months away is not "within 72 hours" (the query used to bound only the lower
    # side, so any later-dated payment counted). The amount test is in the WHERE clause so the nearest payment with a
    # different amount cannot hide a real duplicate behind LIMIT 1.
    result = await db.execute(text("""
        SELECT payment_id, amount, payment_date
        FROM payments
        WHERE sender_name = :sender_name
          AND reference_field_1 IS NOT DISTINCT FROM :reference
          AND payment_method = :payment_method
          AND payment_date >= :window_start
          AND payment_date <= :window_end
          AND ABS(amount - :amount) <= :tolerance
          AND payment_id != :payment_id
          AND status != 'returned'
        ORDER BY ABS(EXTRACT(EPOCH FROM (payment_date - :payment_date)))
        LIMIT 1
    """), {
        "sender_name": sender_name,
        "reference": reference,
        "payment_method": payment_method,
        "window_start": payment_date - timedelta(hours=window_hours),
        "window_end": payment_date + timedelta(hours=window_hours),
        "payment_date": payment_date,
        "amount": amount,
        "tolerance": amount_tolerance_cents,
        "payment_id": payment_id,
    })

    row = result.fetchone()

    if row is None:
        return {
            "is_duplicate_match": False,
            "duplicate_payment_id": None,
            "hours_since_duplicate": None,
            "duplicate_amount_difference": None,
        }

    duplicate_payment_id, duplicate_amount, duplicate_date = row
    duplicate_amount_difference = abs(amount - duplicate_amount)
    hours_since_duplicate = abs((payment_date - duplicate_date).total_seconds()) / 3600

    return {
        "is_duplicate_match": True,
        "duplicate_payment_id": duplicate_payment_id,
        "hours_since_duplicate": round(hours_since_duplicate, 2),
        "duplicate_amount_difference": duplicate_amount_difference,
    }
