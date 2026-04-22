import logging
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

# Days-from-due boundaries (positive = late, negative = early)
_TIMING_BANDS = [
    ("excellent",   -7,   0),
    ("good",         1,   5),
    ("acceptable",   6,  14),
]


def _timing_quality(days_from_due: int) -> str:
    for quality, lo, hi in _TIMING_BANDS:
        if lo <= days_from_due <= hi:
            return quality
    return "poor"


def compute_timing(
    payment_date: datetime,
    next_due_date: date | None,
    last_payment_date: datetime | None,
) -> dict:
    """
    Returns payment_timing_quality and days_since_last_payment.
    """
    timing_quality = "poor"
    days_from_due = None

    if next_due_date is not None:
        pmt_date = payment_date.date() if isinstance(payment_date, datetime) else payment_date
        days_from_due = (pmt_date - next_due_date).days
        timing_quality = _timing_quality(days_from_due)

    days_since_last = None
    if last_payment_date is not None:
        delta = payment_date - last_payment_date
        days_since_last = delta.days

    return {
        "payment_timing_quality": timing_quality,
        "days_since_last_payment": days_since_last,
    }
