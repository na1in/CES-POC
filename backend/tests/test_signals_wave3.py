from datetime import date, timedelta

import pytest

from app.services.signals.amount import (
    compute_multi_method,
    compute_multi_period,
    compute_third_party,
)
from app.services.signals.risk import (
    compute_account_status,
    compute_balance_snapshot,
    compute_payment_method_risk,
    compute_risk_flags,
    compute_supporting_signals,
)


# ══════════════════════════════════════════════════════════════════════════════
# Risk Flags
# ══════════════════════════════════════════════════════════════════════════════

def test_risk_flags_no_flags():
    result = compute_risk_flags([])
    assert result["has_risk_flags"] is False
    assert result["risk_flag_types"] == []


def test_risk_flags_active_flag():
    result = compute_risk_flags([{"flag_type": "fraud_history", "is_active": True}])
    assert result["has_risk_flags"] is True
    assert "fraud_history" in result["risk_flag_types"]


def test_risk_flags_inactive_flag_ignored():
    result = compute_risk_flags([{"flag_type": "fraud_history", "is_active": False}])
    assert result["has_risk_flags"] is False
    assert result["risk_flag_types"] == []


def test_risk_flags_multiple_active():
    flags = [
        {"flag_type": "fraud_history", "is_active": True},
        {"flag_type": "suspended_account", "is_active": True},
        {"flag_type": "chronic_late_payments", "is_active": False},
    ]
    result = compute_risk_flags(flags)
    assert result["has_risk_flags"] is True
    assert len(result["risk_flag_types"]) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Account Status
# ══════════════════════════════════════════════════════════════════════════════

def test_account_status_active():
    assert compute_account_status("active")["account_status"] == "active"


def test_account_status_inactive():
    assert compute_account_status("inactive")["account_status"] == "inactive"


def test_account_status_closed():
    assert compute_account_status("closed")["account_status"] == "closed"


def test_account_status_pending_maps_to_active():
    assert compute_account_status("pending")["account_status"] == "active"


def test_account_status_none_maps_to_inactive():
    assert compute_account_status(None)["account_status"] == "inactive"


# ══════════════════════════════════════════════════════════════════════════════
# Balance Snapshot
# ══════════════════════════════════════════════════════════════════════════════

def test_balance_current():
    future_due = date.today() + timedelta(days=10)
    result = compute_balance_snapshot(50000, future_due)
    assert result["outstanding_balance_cents"] == 50000
    assert result["outstanding_balance_status"] == "current"


def test_balance_past_due():
    past_due = date.today() - timedelta(days=5)
    result = compute_balance_snapshot(50000, past_due)
    assert result["outstanding_balance_status"] == "past_due"


def test_balance_no_due_date_is_current():
    result = compute_balance_snapshot(0, None)
    assert result["outstanding_balance_status"] == "current"


# ══════════════════════════════════════════════════════════════════════════════
# Payment Method Risk
# ══════════════════════════════════════════════════════════════════════════════

def test_payment_method_risk_ach_is_low():
    assert compute_payment_method_risk("ACH")["payment_method_risk_level"] == "low"


def test_payment_method_risk_credit_card_is_low():
    assert compute_payment_method_risk("Credit Card")["payment_method_risk_level"] == "low"


def test_payment_method_risk_check_is_medium():
    assert compute_payment_method_risk("Check")["payment_method_risk_level"] == "medium"


def test_payment_method_risk_wire_is_medium():
    assert compute_payment_method_risk("Wire")["payment_method_risk_level"] == "medium"


def test_payment_method_risk_unknown_is_high():
    assert compute_payment_method_risk("Bitcoin")["payment_method_risk_level"] == "high"


# ══════════════════════════════════════════════════════════════════════════════
# Supporting Signals
# ══════════════════════════════════════════════════════════════════════════════

def test_supporting_signals_all_true():
    result = compute_supporting_signals(
        sender_account="ACC-001",
        historical_sender_accounts=["ACC-001", "ACC-002"],
        amount_variance_pct=1.0,
        historical_consistency_score=90.0,
    )
    assert result == {"account_match": True, "amount_match": True, "historical_match": True}


def test_supporting_signals_account_not_in_history():
    result = compute_supporting_signals(
        sender_account="ACC-999",
        historical_sender_accounts=["ACC-001"],
        amount_variance_pct=1.0,
        historical_consistency_score=90.0,
    )
    assert result["account_match"] is False


def test_supporting_signals_high_variance_fails_amount_match():
    result = compute_supporting_signals(
        sender_account="ACC-001",
        historical_sender_accounts=["ACC-001"],
        amount_variance_pct=5.0,
        historical_consistency_score=90.0,
    )
    assert result["amount_match"] is False


def test_supporting_signals_low_consistency_fails_historical_match():
    result = compute_supporting_signals(
        sender_account="ACC-001",
        historical_sender_accounts=["ACC-001"],
        amount_variance_pct=1.0,
        historical_consistency_score=50.0,
    )
    assert result["historical_match"] is False


# ══════════════════════════════════════════════════════════════════════════════
# Multi-Period
# ══════════════════════════════════════════════════════════════════════════════

def test_multi_period_single_premium():
    result = compute_multi_period(150000, 150000)
    assert result["is_multi_period"] is False


def test_multi_period_two_periods():
    result = compute_multi_period(300000, 150000)
    assert result["is_multi_period"] is True
    assert result["estimated_periods"] == 2


def test_multi_period_three_periods():
    result = compute_multi_period(450000, 150000)
    assert result["is_multi_period"] is True
    assert result["estimated_periods"] == 3


def test_multi_period_within_tolerance():
    result = compute_multi_period(299000, 150000)  # ~0.33% off 2x
    assert result["is_multi_period"] is True
    assert result["estimated_periods"] == 2


def test_multi_period_no_premium():
    result = compute_multi_period(300000, 0)
    assert result["is_multi_period"] is False


# ══════════════════════════════════════════════════════════════════════════════
# Multi-Method
# ══════════════════════════════════════════════════════════════════════════════

def test_multi_method_half_premium():
    result = compute_multi_method(75000, 150000)
    assert result["is_multi_method"] is True
    assert result["multi_method_fraction"] == 0.5


def test_multi_method_third_premium():
    result = compute_multi_method(50000, 150000)
    assert result["is_multi_method"] is True


def test_multi_method_full_premium_not_split():
    result = compute_multi_method(150000, 150000)
    assert result["is_multi_method"] is False


def test_multi_method_no_premium():
    result = compute_multi_method(75000, 0)
    assert result["is_multi_method"] is False


# ══════════════════════════════════════════════════════════════════════════════
# Third-Party
# ══════════════════════════════════════════════════════════════════════════════

def test_third_party_same_person_not_flagged():
    result = compute_third_party("Robert Johnson", "Robert Johnson", 100.0, None)
    assert result["is_third_party_payment"] is False


def test_third_party_high_similarity_not_flagged():
    result = compute_third_party("Rob Johnson", "Robert Johnson", 85.0, None)
    assert result["is_third_party_payment"] is False


def test_third_party_employer_keyword():
    result = compute_third_party("Acme Corp", "Robert Johnson", 10.0, "payment from employer payroll")
    assert result["is_third_party_payment"] is True
    assert result["third_party_relationship"] == "employer"


def test_third_party_escrow_keyword():
    result = compute_third_party("First Bank Escrow", "Robert Johnson", 5.0, "escrow disbursement")
    assert result["is_third_party_payment"] is True
    assert result["third_party_relationship"] == "escrow"


def test_third_party_different_name_no_keyword():
    result = compute_third_party("Jane Doe", "Robert Johnson", 20.0, None)
    assert result["is_third_party_payment"] is True
    assert result["third_party_relationship"] is None
