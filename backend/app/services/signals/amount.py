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


def compute_multi_period(
    payment_amount: int,
    premium_amount: int,
    tolerance_pct: float = 5.0,
) -> dict:
    """
    Checks if payment ≈ N × premium for N in 2..12.
    Returns is_multi_period and estimated_periods.
    """
    if premium_amount <= 0:
        return {"is_multi_period": False, "estimated_periods": 0}

    for period_count in range(2, 13):
        expected_amount = premium_amount * period_count
        variance = abs(payment_amount - expected_amount) / expected_amount * 100
        if variance <= tolerance_pct:
            return {"is_multi_period": True, "estimated_periods": period_count}

    return {"is_multi_period": False, "estimated_periods": 0}


def compute_multi_method(
    payment_amount: int,
    premium_amount: int,
    tolerance_pct: float = 5.0,
) -> dict:
    """
    Checks if payment ≈ premium / N for N in 2, 3, 4 (split premium across banks).
    Returns is_multi_method and multi_method_fraction.
    """
    if premium_amount <= 0:
        return {"is_multi_method": False, "multi_method_fraction": 0.0}

    for denominator in [2, 3, 4]:
        expected_amount = premium_amount / denominator
        variance = abs(payment_amount - expected_amount) / expected_amount * 100
        if variance <= tolerance_pct:
            fraction = round(payment_amount / premium_amount, 3)
            return {"is_multi_method": True, "multi_method_fraction": fraction}

    return {"is_multi_method": False, "multi_method_fraction": 0.0}


def compute_third_party(
    sender_name: str,
    customer_name: str,
    name_similarity_score: float,
    reference_text: str | None,
) -> dict:
    """
    Flags if payment is from a third party (employer, family, escrow, etc.).
    Sender is third-party if name similarity < 50% AND (keyword match OR beneficiary mismatch).
    """
    THIRD_PARTY_KEYWORDS = ["employer", "payroll", "escrow", "family", "on behalf", "trust", "poa"]

    if name_similarity_score >= 50.0:
        return {"is_third_party_payment": False, "third_party_relationship": None}

    reference_lower = (reference_text or "").lower()
    matched_keyword = next(
        (keyword for keyword in THIRD_PARTY_KEYWORDS if keyword in reference_lower),
        None,
    )

    is_third_party = matched_keyword is not None or sender_name.strip().lower() != customer_name.strip().lower()

    return {
        "is_third_party_payment": is_third_party,
        "third_party_relationship": matched_keyword if is_third_party else None,
    }
