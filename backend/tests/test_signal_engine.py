"""
Integration tests for run_signal_engine.

Each test inserts a minimal payment row (FK required by payment_signals), runs
the engine, then queries the DB to verify the snapshot was written correctly.
The rollback_only fixture ensures no data leaks between tests.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.signal_engine import run_signal_engine


# ── Shared test data ──────────────────────────────────────────────────────────

def _base_payment(payment_id: str, amount: int = 150000) -> dict:
    return {
        "amount": amount,
        "payment_method": "ACH",
        "payment_date": datetime(2026, 4, 24, 10, 0, 0, tzinfo=timezone.utc),
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-001",
        "reference_1": "Policy POL-00001",
        "reference_2": None,
        "extracted_policy_number": "POL-00001",
    }


def _base_customer() -> dict:
    return {
        "customer_name": "Robert Johnson",
        "status": "active",
        "outstanding_balance_cents": 0,
        "next_due_date": date(2026, 4, 24),
        "last_payment_date": datetime(2026, 3, 24, tzinfo=timezone.utc),
        "historical_sender_accounts": ["ACC-001"],
        "historical_amounts": [150000, 150000, 150000],
        "risk_flags": [],
    }


def _base_policy() -> dict:
    return {
        "policy_number": "POL-00001",
        "premium_amount": 150000,
    }


async def _insert_payment(db: AsyncSession, payment_id: str, amount: int = 150000) -> None:
    await db.execute(text("""
        INSERT INTO payments (
            payment_id, amount, sender_name, sender_account, beneficiary_name,
            payment_method, payment_date, reference_field_1, status, created_timestamp
        ) VALUES (
            :payment_id, :amount, 'Robert Johnson', 'ACC-001', 'Robert Johnson',
            'ACH', '2026-04-24 10:00:00+00', 'Policy POL-00001', 'received',
            '2026-04-24 10:00:00+00'
        )
    """), {"payment_id": payment_id, "amount": amount})


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_signal_engine_inserts_payment_signals_row(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-001")

    await run_signal_engine(
        payment_id="PMT-SE-001",
        payment=_base_payment("PMT-SE-001"),
        customer=_base_customer(),
        policy=_base_policy(),
        db=db,
    )

    row = (await db.execute(
        text("SELECT payment_id FROM payment_signals WHERE payment_id = 'PMT-SE-001'")
    )).fetchone()
    assert row is not None


async def test_signal_engine_writes_audit_log(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-002")

    await run_signal_engine(
        payment_id="PMT-SE-002",
        payment=_base_payment("PMT-SE-002"),
        customer=_base_customer(),
        policy=_base_policy(),
        db=db,
    )

    row = (await db.execute(text("""
        SELECT action_type FROM audit_log
        WHERE payment_id = 'PMT-SE-002' AND action_type = 'signals_computed'
    """))).fetchone()
    assert row is not None


async def test_signal_engine_name_similarity_stored(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-003")

    await run_signal_engine(
        payment_id="PMT-SE-003",
        payment=_base_payment("PMT-SE-003"),
        customer=_base_customer(),
        policy=_base_policy(),
        db=db,
    )

    row = (await db.execute(text("""
        SELECT name_similarity_score, deterministic_score
        FROM payment_signals WHERE payment_id = 'PMT-SE-003'
    """))).fetchone()
    assert row.name_similarity_score > 90.0
    assert row.deterministic_score is not None


async def test_signal_engine_timing_quality_stored(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-004")

    customer = _base_customer()
    customer["next_due_date"] = date(2026, 4, 24)  # payment is on due date → excellent

    await run_signal_engine(
        payment_id="PMT-SE-004",
        payment=_base_payment("PMT-SE-004"),
        customer=customer,
        policy=_base_policy(),
        db=db,
    )

    row = (await db.execute(text("""
        SELECT payment_timing_quality, days_from_due_date
        FROM payment_signals WHERE payment_id = 'PMT-SE-004'
    """))).fetchone()
    assert str(row.payment_timing_quality) == "excellent"
    assert row.days_from_due_date == 0


async def test_signal_engine_account_status_stored(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-005")

    await run_signal_engine(
        payment_id="PMT-SE-005",
        payment=_base_payment("PMT-SE-005"),
        customer=_base_customer(),
        policy=_base_policy(),
        db=db,
    )

    row = (await db.execute(text("""
        SELECT account_status, payment_method_risk_level
        FROM payment_signals WHERE payment_id = 'PMT-SE-005'
    """))).fetchone()
    assert str(row.account_status) == "active"
    assert str(row.payment_method_risk_level) == "low"


async def test_signal_engine_no_policy_stores_zero_confidence(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-006")

    await run_signal_engine(
        payment_id="PMT-SE-006",
        payment=_base_payment("PMT-SE-006"),
        customer=_base_customer(),
        policy=None,  # no policy matched
        db=db,
    )

    row = (await db.execute(text("""
        SELECT policy_match_confidence, is_multi_period, is_multi_method
        FROM payment_signals WHERE payment_id = 'PMT-SE-006'
    """))).fetchone()
    assert row.policy_match_confidence == 0.0
    assert row.is_multi_period is False
    assert row.is_multi_method is False


async def test_signal_engine_risk_flags_stored(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-007")

    customer = _base_customer()
    customer["risk_flags"] = [
        {"flag_type": "fraud_history", "is_active": True},
        {"flag_type": "chronic_late_payments", "is_active": False},
    ]

    await run_signal_engine(
        payment_id="PMT-SE-007",
        payment=_base_payment("PMT-SE-007"),
        customer=customer,
        policy=_base_policy(),
        db=db,
    )

    row = (await db.execute(text("""
        SELECT has_risk_flags, risk_flag_types
        FROM payment_signals WHERE payment_id = 'PMT-SE-007'
    """))).fetchone()
    assert row.has_risk_flags is True
    assert "fraud_history" in row.risk_flag_types


async def test_signal_engine_outstanding_balance_justifies_duplicate(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-008")

    # Insert a prior payment to trigger duplicate detection
    await db.execute(text("""
        INSERT INTO payments (
            payment_id, amount, sender_name, sender_account, beneficiary_name,
            payment_method, payment_date, status, created_timestamp
        ) VALUES (
            'PMT-SE-008-PRIOR', 150000, 'Robert Johnson', 'ACC-001', 'Robert Johnson',
            'ACH', '2026-04-23 10:00:00+00', 'received', '2026-04-23 10:00:00+00'
        )
    """))

    customer = _base_customer()
    customer["outstanding_balance_cents"] = 150000  # balance > 0

    signals = await run_signal_engine(
        payment_id="PMT-SE-008",
        payment=_base_payment("PMT-SE-008"),
        customer=customer,
        policy=_base_policy(),
        db=db,
    )

    assert signals["is_duplicate_match"] is True
    assert signals["outstanding_balance_justifies"] is True


async def test_signal_engine_returns_signals_dict(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-009")

    signals = await run_signal_engine(
        payment_id="PMT-SE-009",
        payment=_base_payment("PMT-SE-009"),
        customer=_base_customer(),
        policy=_base_policy(),
        db=db,
    )

    # Verify all key groups are present in the returned dict
    assert "name_similarity_score" in signals
    assert "policy_match_confidence" in signals
    assert "customer_match_confidence" in signals
    assert "amount_variance_pct" in signals
    assert "is_multi_period" in signals
    assert "is_multi_method" in signals
    assert "is_third_party_payment" in signals
    assert "payment_timing_quality" in signals
    assert "has_risk_flags" in signals
    assert "account_status" in signals
    assert "is_duplicate_match" in signals


async def test_signal_engine_multi_period_detected(db: AsyncSession):
    await _insert_payment(db, "PMT-SE-010", amount=300000)

    payment = _base_payment("PMT-SE-010", amount=300000)  # 2× the $150 premium

    signals = await run_signal_engine(
        payment_id="PMT-SE-010",
        payment=payment,
        customer=_base_customer(),
        policy=_base_policy(),
        db=db,
    )

    assert signals["is_multi_period"] is True
    assert signals["estimated_periods"] == 2
