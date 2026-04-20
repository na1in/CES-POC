"""
Seed script — idempotent, safe to re-run.
Usage (from backend/):  python scripts/seed.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed_users(db: AsyncSession) -> None:
    await db.execute(text("""
        INSERT INTO users (user_id, name, email, role) VALUES
            ('USR-0001', 'Priya Sharma',   'priya@ces.internal',   'analyst'),
            ('USR-0002', 'Damien Torres',  'damien@ces.internal',  'investigator'),
            ('USR-0003', 'Lorraine Chen',  'lorraine@ces.internal','director'),
            ('USR-0004', 'Marcus Webb',    'marcus@ces.internal',  'admin')
        ON CONFLICT (user_id) DO NOTHING
    """))


async def seed_customers(db: AsyncSession) -> None:
    await db.execute(text("""
        INSERT INTO customers (customer_id, name, account_number, status) VALUES
            -- Clean customer — good for Scenario 1 auto-apply tests
            ('CUST-0001', 'Robert Johnson',  'ACC-10001', 'active'),
            -- Second clean customer — good for Scenario 2 tests
            ('CUST-0002', 'Maria Rodriguez', 'ACC-10002', 'active'),
            -- Customer with fraud_history risk flag — triggers Scenario 1 hold path
            ('CUST-0003', 'James Wilson',    'ACC-10003', 'active'),
            -- Inactive customer — account_status signal = inactive
            ('CUST-0004', 'Sarah Lee',       'ACC-10004', 'inactive'),
            -- Customer with chronic late payments flag
            ('CUST-0005', 'David Chen',      'ACC-10005', 'active')
        ON CONFLICT (customer_id) DO NOTHING
    """))

    # Risk flags — only insert if not already present for the customer
    await db.execute(text("""
        INSERT INTO risk_flags (customer_id, flag_type, notes)
        SELECT 'CUST-0003', 'fraud_history', 'Flagged 2025-11: disputed charge investigation'
        WHERE NOT EXISTS (
            SELECT 1 FROM risk_flags WHERE customer_id = 'CUST-0003' AND flag_type = 'fraud_history'
        )
    """))
    await db.execute(text("""
        INSERT INTO risk_flags (customer_id, flag_type, notes)
        SELECT 'CUST-0005', 'chronic_late_payments', '4 late payments in last 12 months'
        WHERE NOT EXISTS (
            SELECT 1 FROM risk_flags WHERE customer_id = 'CUST-0005' AND flag_type = 'chronic_late_payments'
        )
    """))


async def seed_policies(db: AsyncSession) -> None:
    await db.execute(text("""
        INSERT INTO policies
            (policy_number, customer_id, policy_type, premium_amount, premium_frequency,
             status, outstanding_balance, next_due_date)
        VALUES
            -- Robert Johnson: Auto policy $1,500/mo, balance current
            ('POL-00001', 'CUST-0001', 'Auto',   150000, 'monthly',    'active',   0,      '2026-05-01'),
            -- Robert Johnson: second policy (Home) — for Scenario 2 ambiguous multi-policy test
            ('POL-00002', 'CUST-0001', 'Home',    95000, 'monthly',    'active',   0,      '2026-05-01'),
            -- Maria Rodriguez: Home policy $1,200/mo
            ('POL-00003', 'CUST-0002', 'Home',   120000, 'monthly',    'active',   0,      '2026-05-01'),
            -- James Wilson: Life policy $2,000/mo (has risk flag — Sc1 hold path)
            ('POL-00004', 'CUST-0003', 'Life',   200000, 'monthly',    'active',   0,      '2026-05-01'),
            -- Sarah Lee: Health policy $800/mo — policy inactive (account inactive)
            ('POL-00005', 'CUST-0004', 'Health',  80000, 'monthly',    'inactive', 0,      NULL),
            -- David Chen: quarterly Auto policy $4,500/quarter — for multi-period tests
            ('POL-00006', 'CUST-0005', 'Auto',   450000, 'quarterly',  'active',  45000,  '2026-05-15')
        ON CONFLICT (policy_number) DO NOTHING
    """))


async def seed_payment_history(db: AsyncSession) -> None:
    """6 months of on-time payments for each active policy — establishes historical patterns."""
    await db.execute(text("""
        INSERT INTO payment_history (policy_id, payment_date, amount, payment_method, sender_account, status)
        SELECT * FROM (VALUES
            -- POL-00001 (Robert Johnson Auto, $1,500/mo via ACH)
            ('POL-00001', '2025-11-01 10:00:00+00'::timestamptz, 150000, 'ACH', 'ACC-10001', 'applied'::payment_history_status),
            ('POL-00001', '2025-12-01 09:45:00+00'::timestamptz, 150000, 'ACH', 'ACC-10001', 'applied'::payment_history_status),
            ('POL-00001', '2026-01-01 10:15:00+00'::timestamptz, 150000, 'ACH', 'ACC-10001', 'applied'::payment_history_status),
            ('POL-00001', '2026-02-01 09:50:00+00'::timestamptz, 150000, 'ACH', 'ACC-10001', 'applied'::payment_history_status),
            ('POL-00001', '2026-03-01 10:05:00+00'::timestamptz, 150000, 'ACH', 'ACC-10001', 'applied'::payment_history_status),
            ('POL-00001', '2026-04-01 10:00:00+00'::timestamptz, 150000, 'ACH', 'ACC-10001', 'applied'::payment_history_status),

            -- POL-00003 (Maria Rodriguez Home, $1,200/mo via Credit Card)
            ('POL-00003', '2025-11-02 14:00:00+00'::timestamptz, 120000, 'Credit Card', 'ACC-10002', 'applied'::payment_history_status),
            ('POL-00003', '2025-12-02 14:00:00+00'::timestamptz, 120000, 'Credit Card', 'ACC-10002', 'applied'::payment_history_status),
            ('POL-00003', '2026-01-02 14:00:00+00'::timestamptz, 120000, 'Credit Card', 'ACC-10002', 'applied'::payment_history_status),
            ('POL-00003', '2026-02-02 14:00:00+00'::timestamptz, 120000, 'Credit Card', 'ACC-10002', 'applied'::payment_history_status),
            ('POL-00003', '2026-03-02 14:00:00+00'::timestamptz, 120000, 'Credit Card', 'ACC-10002', 'applied'::payment_history_status),
            ('POL-00003', '2026-04-02 14:00:00+00'::timestamptz, 120000, 'Credit Card', 'ACC-10002', 'applied'::payment_history_status),

            -- POL-00004 (James Wilson Life, $2,000/mo via Check — has risk flag)
            ('POL-00004', '2025-11-05 11:00:00+00'::timestamptz, 200000, 'Check', 'ACC-10003', 'applied'::payment_history_status),
            ('POL-00004', '2025-12-05 11:00:00+00'::timestamptz, 200000, 'Check', 'ACC-10003', 'applied'::payment_history_status),
            ('POL-00004', '2026-01-05 11:00:00+00'::timestamptz, 200000, 'Check', 'ACC-10003', 'applied'::payment_history_status),
            ('POL-00004', '2026-02-05 11:00:00+00'::timestamptz, 200000, 'Check', 'ACC-10003', 'applied'::payment_history_status),
            ('POL-00004', '2026-03-05 11:00:00+00'::timestamptz, 200000, 'Check', 'ACC-10003', 'applied'::payment_history_status),
            ('POL-00004', '2026-04-05 11:00:00+00'::timestamptz, 200000, 'Check', 'ACC-10003', 'applied'::payment_history_status),

            -- POL-00006 (David Chen Auto quarterly, $4,500/quarter — 2 payments)
            ('POL-00006', '2025-11-15 09:00:00+00'::timestamptz, 450000, 'ACH', 'ACC-10005', 'applied'::payment_history_status),
            ('POL-00006', '2026-02-15 09:00:00+00'::timestamptz, 450000, 'ACH', 'ACC-10005', 'applied'::payment_history_status)
        ) AS v(policy_id, payment_date, amount, payment_method, sender_account, status)
        WHERE NOT EXISTS (
            SELECT 1 FROM payment_history ph
            WHERE ph.policy_id = v.policy_id AND ph.payment_date = v.payment_date
        )
    """))


async def seed_configuration_thresholds(db: AsyncSession) -> None:
    await db.execute(text("""
        INSERT INTO configuration_thresholds (parameter_name, parameter_value, description) VALUES
            ('name_match_auto_apply',           '90',  'Min name similarity % for Scenario 1 auto-apply'),
            ('name_match_hold',                 '75',  'Min name similarity % to hold vs escalate'),
            ('name_gray_zone_lower',            '70',  'Below this score skip LLM — clear mismatch'),
            ('name_gray_zone_upper',            '92',  'Above this score skip LLM — clear match'),
            ('amount_tolerance_auto',            '2',  'Max variance % for auto-approve (Scenario 1)'),
            ('duplicate_window_hours',          '72',  'Lookback window for duplicate detection (hours)'),
            ('duplicate_amount_tolerance_cents','200', 'Max cent difference for duplicate match ($2.00)'),
            ('multi_period_tolerance',           '5',  'Tolerance % for multi-period payment detection')
        ON CONFLICT (parameter_name) DO NOTHING
    """))


async def main() -> None:
    async with Session() as db:
        print("Seeding users...")
        await seed_users(db)

        print("Seeding customers + risk flags...")
        await seed_customers(db)

        print("Seeding policies...")
        await seed_policies(db)

        print("Seeding payment history...")
        await seed_payment_history(db)

        print("Seeding configuration thresholds...")
        await seed_configuration_thresholds(db)

        await db.commit()

    await engine.dispose()
    print("\nDone. Test logins:")
    print("  USR-0001  Priya Sharma    (analyst)")
    print("  USR-0002  Damien Torres   (investigator)")
    print("  USR-0003  Lorraine Chen   (director)")
    print("  USR-0004  Marcus Webb     (admin)")


if __name__ == "__main__":
    asyncio.run(main())
