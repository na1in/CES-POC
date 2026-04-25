import logging
from datetime import date

logger = logging.getLogger(__name__)

PAYMENT_METHOD_RISK = {
    "ACH": "low",
    "Credit Card": "low",
    "Check": "medium",
    "Wire": "medium",
}

ACCOUNT_STATUS_MAP = {
    "active": "active",
    "inactive": "inactive",
    "closed": "closed",
    "pending": "active",
}


def compute_risk_flags(risk_flag_rows: list[dict]) -> dict:
    """
    Summarises active risk flags for a customer.
    Each row is a dict with at least {"flag_type": str, "is_active": bool}.
    """
    active_flags = [row["flag_type"] for row in risk_flag_rows if row.get("is_active")]
    return {
        "has_risk_flags": len(active_flags) > 0,
        "risk_flag_types": active_flags,
    }


def compute_account_status(customer_status: str | None) -> dict:
    """Maps DB customer status to the account_status enum used in payment_signals."""
    mapped = ACCOUNT_STATUS_MAP.get(customer_status or "", "inactive")
    return {"account_status": mapped}


def compute_balance_snapshot(
    outstanding_balance_cents: int,
    next_due_date: date | None,
) -> dict:
    """Snapshots balance and determines if it is current or past due."""
    from datetime import date as date_type
    today = date_type.today()
    balance_status = "current"
    if next_due_date is not None and next_due_date < today:
        balance_status = "past_due"

    return {
        "outstanding_balance_cents": outstanding_balance_cents,
        "outstanding_balance_status": balance_status,
    }


def compute_payment_method_risk(payment_method: str) -> dict:
    """Pure lookup — no DB required."""
    risk_level = PAYMENT_METHOD_RISK.get(payment_method, "high")
    return {"payment_method_risk_level": risk_level}


def compute_supporting_signals(
    sender_account: str | None,
    historical_sender_accounts: list[str],
    amount_variance_pct: float | None,
    historical_consistency_score: float,
    amount_tolerance_pct: float = 2.0,
    historical_match_threshold: float = 70.0,
) -> dict:
    """
    Three boolean supporting signals:
    - account_match: sender_account appears in payment history
    - amount_match: variance within tolerance
    - historical_match: historical_consistency_score >= threshold
    """
    account_match = (
        sender_account is not None and
        sender_account in historical_sender_accounts
    )
    amount_match = (
        amount_variance_pct is not None and
        amount_variance_pct <= amount_tolerance_pct
    )
    historical_match = historical_consistency_score >= historical_match_threshold

    return {
        "account_match": account_match,
        "amount_match": amount_match,
        "historical_match": historical_match,
    }
