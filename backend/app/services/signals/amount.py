import logging

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
