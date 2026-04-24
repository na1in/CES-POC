import logging
import statistics

logger = logging.getLogger(__name__)


def compute_amount_variance(payment_amount: int, premium_amount: int) -> dict:
    """
    Computes variance between payment and the policy's expected premium.
    All amounts in cents.
    """
    if premium_amount <= 0:
        return {
            "amount_variance_pct": None,
            "is_overpayment": False,
            "is_underpayment": False,
            "difference_amount": None,
        }

    difference = payment_amount - premium_amount
    variance_pct = abs(difference) / premium_amount * 100

    return {
        "amount_variance_pct": round(variance_pct, 4),
        "is_overpayment": difference > 0,
        "is_underpayment": difference < 0,
        "difference_amount": difference,
    }


def compute_historical_consistency(
    current_amount: int,
    historical_amounts: list[int],
) -> float:
    """
    Z-score outlier detection against last 6 historical payments.
    Returns 100 if fewer than 2 historical records (not enough data to flag).
    Score: z=0 → 100, z=5 → 0, capped at 0.
    """
    if len(historical_amounts) < 2:
        return 100.0

    mean = statistics.mean(historical_amounts)
    stdev = statistics.stdev(historical_amounts)

    if stdev == 0:
        return 100.0

    z_score = abs(current_amount - mean) / stdev
    # z=0→100, z=10→0 (more forgiving than z*20 — small variations stay high)
    score = max(0.0, 100.0 - (z_score * 10.0))
    return round(score, 2)
