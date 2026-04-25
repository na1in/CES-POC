import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def compute_duplicate(
    db: AsyncSession,
    payment_id: str,
    sender_name: str,
    sender_account: str | None,
    payment_method: str,
    payment_date: datetime,
    amount: int,
    window_hours: int = 72,
    amount_tolerance_cents: int = 200,
) -> dict:
    """
    Checks for a duplicate payment within the configured window.
    Match criteria: same sender_name + sender_account + payment_method,
    within window_hours, amount within amount_tolerance_cents.
    """
    result = await db.execute(text("""
        SELECT payment_id, amount, payment_date
        FROM payments
        WHERE sender_name = :sender_name
          AND sender_account IS NOT DISTINCT FROM :sender_account
          AND payment_method = :payment_method
          AND payment_date >= :cutoff
          AND payment_id != :payment_id
          AND status NOT IN ('returned', 'processing_failed')
        ORDER BY payment_date DESC
        LIMIT 1
    """), {
        "sender_name": sender_name,
        "sender_account": sender_account,
        "payment_method": payment_method,
        "cutoff": payment_date - __import__("datetime").timedelta(hours=window_hours),
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

    if duplicate_amount_difference > amount_tolerance_cents:
        return {
            "is_duplicate_match": False,
            "duplicate_payment_id": None,
            "hours_since_duplicate": None,
            "duplicate_amount_difference": None,
        }

    hours_since_duplicate = abs((payment_date - duplicate_date).total_seconds()) / 3600

    return {
        "is_duplicate_match": True,
        "duplicate_payment_id": duplicate_payment_id,
        "hours_since_duplicate": round(hours_since_duplicate, 2),
        "duplicate_amount_difference": duplicate_amount_difference,
    }
