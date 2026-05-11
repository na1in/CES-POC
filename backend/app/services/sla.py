"""
SLA service — deadline computation and breach detection.

check_and_mark_breaches(db) should be called periodically (every 60s in lifespan).
It scans for escalated/pending_sender_response payments whose investigation_due_date
has passed, sets sla_breached=true, and writes an audit log entry.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.persist import _SLA_HOURS

logger = logging.getLogger(__name__)

_SLA_POLL_INTERVAL_SECONDS = 60
_BREACH_STATUSES = ("escalated", "pending_sender_response")


def compute_due_date(from_time: datetime, sla_hours: int = _SLA_HOURS) -> datetime:
    """Return the SLA deadline given a starting timestamp."""
    return from_time + timedelta(hours=sla_hours)


async def check_and_mark_breaches(db: AsyncSession) -> int:
    """
    Mark all overdue escalated/pending_sender_response payments as sla_breached.
    Returns count of newly breached payments.
    """
    now = datetime.now(timezone.utc)

    rows = await db.execute(text("""
        SELECT payment_id FROM payments
        WHERE status = ANY(CAST(:statuses AS payment_status[]))
          AND investigation_due_date IS NOT NULL
          AND investigation_due_date < :now
          AND sla_breached = false
    """), {"statuses": list(_BREACH_STATUSES), "now": now})
    breached = [r[0] for r in rows]

    if not breached:
        return 0

    await db.execute(text("""
        UPDATE payments
        SET sla_breached = true
        WHERE payment_id = ANY(:ids)
    """), {"ids": breached})

    for pid in breached:
        await db.execute(text("""
            INSERT INTO audit_log (payment_id, action_type, actor, details, timestamp)
            VALUES (:pid, 'sla_breached', 'system',
                    CAST(:details AS jsonb), :ts)
        """), {
            "pid": pid,
            "details": f'{{"payment_id": "{pid}", "breached_at": "{now.isoformat()}"}}',
            "ts": now,
        })

    await db.commit()
    logger.info("SLA breach check: marked %d payment(s) as sla_breached", len(breached))
    return len(breached)


async def run_sla_monitor(session_factory) -> None:
    """
    Background task: poll for SLA breaches every _SLA_POLL_INTERVAL_SECONDS.
    Pass AsyncSessionLocal from app.database as session_factory.
    """
    logger.info("SLA monitor started (interval=%ds)", _SLA_POLL_INTERVAL_SECONDS)
    while True:
        await asyncio.sleep(_SLA_POLL_INTERVAL_SECONDS)
        try:
            async with session_factory() as db:
                count = await check_and_mark_breaches(db)
                if count:
                    logger.info("SLA monitor: %d new breach(es) detected", count)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("SLA monitor error: %s", exc)
