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
            ('CUST-0005', 'David Chen',      'ACC-10005', 'active'),
            -- CUST-0006..0011: no scenario logic depends on these — they only exist so the 6
            -- "applied"/"hold" dashboard-filler payments in seed_historical_payments() each have a
            -- genuinely distinct, real, matchable identity instead of recycling CUST-0001/0002/0005 a
            -- second time (which made every Closed Cases list look like the same 3 people).
            ('CUST-0006', 'Angela Foster',    'ACC-10006', 'active'),
            ('CUST-0007', 'Kevin Nakamura',   'ACC-10007', 'active'),
            ('CUST-0008', 'Priscilla Ortiz',  'ACC-10008', 'active'),
            ('CUST-0009', 'Ben Whitfield',    'ACC-10009', 'active'),
            ('CUST-0010', 'Natalie Reyes',    'ACC-10010', 'active'),
            ('CUST-0011', 'Omar Haddad',      'ACC-10011', 'active')
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
    """
    next_due_date is relative to CURRENT_DATE (not a fixed date) so a payment ingested "today" — via
    demo_payments.py or a live demo — always computes a sensible Payment Timing Quality signal instead
    of comparing against a due date that recedes further into the past every time nobody re-seeds.
    ON CONFLICT DO UPDATE (not DO NOTHING) so re-running seed.py refreshes these dates even when the
    policy rows already exist — otherwise a re-seed silently keeps the stale due date forever.
    """
    await db.execute(text("""
        INSERT INTO policies
            (policy_number, customer_id, policy_type, premium_amount, premium_frequency,
             status, outstanding_balance, next_due_date)
        VALUES
            -- Robert Johnson: Auto policy $1,500/mo, balance current, due in 3 days
            ('POL-00001', 'CUST-0001', 'Auto',   150000, 'monthly',    'active',   0,      CURRENT_DATE + 3),
            -- Robert Johnson: second policy (Home) — for Scenario 2 ambiguous multi-policy test
            ('POL-00002', 'CUST-0001', 'Home',    95000, 'monthly',    'active',   0,      CURRENT_DATE + 3),
            -- Maria Rodriguez: Home policy $1,200/mo, due in 5 days
            ('POL-00003', 'CUST-0002', 'Home',   120000, 'monthly',    'active',   0,      CURRENT_DATE + 5),
            -- James Wilson: Life policy $2,000/mo (has risk flag — Sc1 hold path), due in 2 days
            ('POL-00004', 'CUST-0003', 'Life',   200000, 'monthly',    'active',   0,      CURRENT_DATE + 2),
            -- Sarah Lee: Health policy $800/mo — policy inactive (account inactive)
            ('POL-00005', 'CUST-0004', 'Health',  80000, 'monthly',    'inactive', 0,      NULL),
            -- David Chen: quarterly Auto policy $4,500/quarter — past due by 5 days (matches its
            -- existing $450 outstanding balance) — for multi-period tests
            ('POL-00006', 'CUST-0005', 'Auto',   450000, 'quarterly',  'active',  45000,  CURRENT_DATE - 5),
            -- POL-00007..00012: one policy each for CUST-0006..0011 (see seed_customers) — premiums
            -- match the amounts already used in seed_historical_payments() exactly, or by the stated
            -- variance, so an opened audit report tells a consistent story.
            ('POL-00007', 'CUST-0006', 'Auto',   150000, 'monthly',    'active',   0,      CURRENT_DATE + 6),
            ('POL-00008', 'CUST-0007', 'Home',   120000, 'monthly',    'active',   0,      CURRENT_DATE + 8),
            ('POL-00009', 'CUST-0008', 'Life',   200000, 'monthly',    'active',   0,      CURRENT_DATE + 4),
            ('POL-00010', 'CUST-0009', 'Auto',   150000, 'monthly',    'active',   0,      CURRENT_DATE + 7),
            ('POL-00011', 'CUST-0010', 'Health', 150000, 'monthly',    'active',   0,      CURRENT_DATE + 9),
            ('POL-00012', 'CUST-0011', 'Home',   200000, 'monthly',    'active',   0,      CURRENT_DATE + 6)
        ON CONFLICT (policy_number) DO UPDATE SET next_due_date = EXCLUDED.next_due_date
    """))


async def seed_payment_history(db: AsyncSession) -> None:
    """
    6 months of on-time payments for each active policy — establishes historical patterns. Dated
    relative to now() (most recent one 25 days back), not fixed calendar months, so a fresh seed
    always looks current and days_since_last_payment stays a believable "since last month's premium"
    instead of drifting further into the past every time nobody re-seeds.

    Relative dates can't be deduplicated by exact timestamp match (they're different on every run), so
    this deletes the previous seed-shaped rows first — bounded to > 15 days old, which is well clear of
    anything _apply_ledger() would have just inserted for a payment approved minutes ago in a live demo
    session (those stay put; only the old seed pattern is replaced).
    """
    await db.execute(text("""
        DELETE FROM payment_history
        WHERE policy_id IN ('POL-00001', 'POL-00003', 'POL-00004', 'POL-00006')
          AND payment_date < now() - interval '15 days'
    """))
    await db.execute(text("""
        INSERT INTO payment_history (policy_id, payment_date, amount, payment_method, sender_account, status)
        VALUES
            -- POL-00001 (Robert Johnson Auto, $1,500/mo via ACH)
            ('POL-00001', now() - interval '205 days', 150000, 'ACH', 'ACC-10001', 'applied'),
            ('POL-00001', now() - interval '175 days', 150000, 'ACH', 'ACC-10001', 'applied'),
            ('POL-00001', now() - interval '145 days', 150000, 'ACH', 'ACC-10001', 'applied'),
            ('POL-00001', now() - interval '115 days', 150000, 'ACH', 'ACC-10001', 'applied'),
            ('POL-00001', now() - interval '55 days',  150000, 'ACH', 'ACC-10001', 'applied'),
            ('POL-00001', now() - interval '25 days',  150000, 'ACH', 'ACC-10001', 'applied'),

            -- POL-00003 (Maria Rodriguez Home, $1,200/mo via Credit Card)
            ('POL-00003', now() - interval '204 days', 120000, 'Credit Card', 'ACC-10002', 'applied'),
            ('POL-00003', now() - interval '174 days', 120000, 'Credit Card', 'ACC-10002', 'applied'),
            ('POL-00003', now() - interval '144 days', 120000, 'Credit Card', 'ACC-10002', 'applied'),
            ('POL-00003', now() - interval '114 days', 120000, 'Credit Card', 'ACC-10002', 'applied'),
            ('POL-00003', now() - interval '54 days',  120000, 'Credit Card', 'ACC-10002', 'applied'),
            ('POL-00003', now() - interval '24 days',  120000, 'Credit Card', 'ACC-10002', 'applied'),

            -- POL-00004 (James Wilson Life, $2,000/mo via Check — has risk flag)
            ('POL-00004', now() - interval '200 days', 200000, 'Check', 'ACC-10003', 'applied'),
            ('POL-00004', now() - interval '170 days', 200000, 'Check', 'ACC-10003', 'applied'),
            ('POL-00004', now() - interval '140 days', 200000, 'Check', 'ACC-10003', 'applied'),
            ('POL-00004', now() - interval '110 days', 200000, 'Check', 'ACC-10003', 'applied'),
            ('POL-00004', now() - interval '50 days',  200000, 'Check', 'ACC-10003', 'applied'),
            ('POL-00004', now() - interval '20 days',  200000, 'Check', 'ACC-10003', 'applied'),

            -- POL-00006 (David Chen Auto quarterly, $4,500/quarter — 2 payments, ~90 days apart)
            ('POL-00006', now() - interval '115 days', 450000, 'ACH', 'ACC-10005', 'applied'),
            ('POL-00006', now() - interval '25 days',  450000, 'ACH', 'ACC-10005', 'applied')
    """))


#: Seed fixtures use the same uniform PMT-NNN format as real payments (a high, reserved block so they
#: never collide with demo_payments.py's low sequential numbers) instead of the PMT-ESC-*/PMT-H-*
#: naming this project used until 2026-09-27. That naming was a plain string a test author could read
#: at a glance, but it broke the documented "PMT-XXX" ID convention badly enough that
#: _next_payment_id() had to carry a regex specifically to skip these rows when computing the next
#: number. The semantic name now lives here instead, in one place both Python and the E2E specs import.
ESCALATED_CASE_ID = "PMT-900"


async def seed_escalated_payment(db: AsyncSession) -> None:
    """
    One pre-held Scenario 4 payment (unknown sender, no customer match).
    AI recommends ESCALATE — Priya must manually escalate it to the investigator.

    payment_date is relative to now() so a fresh seed always looks like a case that showed up
    yesterday, not one from whatever month seed.py last happened to be run.
    """
    await db.execute(text("""
        INSERT INTO payments
            (payment_id, amount, sender_name, payment_method, payment_date,
             status, investigation_due_date)
        VALUES
            (:id, 75000, 'Unknown Corp LLC', 'Wire',
             now() - interval '18 hours', 'held',
             NULL)
        ON CONFLICT (payment_id) DO NOTHING
    """), {"id": ESCALATED_CASE_ID})

    await db.execute(text("""
        INSERT INTO payment_recommendations
            (payment_id, recommendation, confidence_score, scenario_route,
             decision_path, requires_human_approval, reasoning, suggested_action)
        SELECT :id, 'escalate', 22.0, 'scenario_4',
               'No customer match found; third-party check negative → ESCALATE',
               true,
               ARRAY['Sender name does not match any known customer.',
                     'No policy reference provided.',
                     'Amount does not correspond to any active policy premium.'],
               'Route to investigator for manual outreach'
        WHERE NOT EXISTS (
            SELECT 1 FROM payment_recommendations WHERE payment_id = :id
        )
    """), {"id": ESCALATED_CASE_ID})

    await db.execute(text("""
        INSERT INTO audit_log
            (payment_id, action_type, actor, actor_user_id, details, timestamp)
        SELECT :id, 'recommendation_made', 'system', NULL,
               '{"recommendation": "ESCALATE", "scenario_route": "scenario_4"}'::jsonb, now()
        WHERE NOT EXISTS (
            SELECT 1 FROM audit_log
            WHERE payment_id = :id AND action_type = 'recommendation_made'
        )
    """), {"id": ESCALATED_CASE_ID})


#: Reserved PMT-9xx block, same reasoning as ESCALATED_CASE_ID above — real PMT-XXX shape, just far
#: enough from demo_payments.py's low sequential numbers that the two can never collide.
HISTORICAL_CASE_IDS = [f"PMT-{n}" for n in range(901, 910)]  # PMT-901 .. PMT-909


async def seed_historical_payments(db: AsyncSession) -> None:
    """
    Pre-resolved payments representing the last 72 hours of activity.
    These populate the Governance and Admin dashboards without requiring
    demo_actions.py to run. They are preserved by demo_restore.py.
    """
    h1, h2, h3, h4, h5, h6, h7, h8, h9 = HISTORICAL_CASE_IDS
    await db.execute(text("""
        INSERT INTO payments
            (payment_id, amount, sender_name, sender_account, payment_method,
             payment_date, status, matched_customer_id, matched_policy_id)
        VALUES
            -- Applied after human review (scenario 1 — strong policy match). Each uses its own
            -- CUST-0006..0011 identity (see seed_customers/seed_policies) — sender_name,
            -- sender_account, matched_customer_id and matched_policy_id all agree, unlike the previous
            -- version of this data, where two rows had sender_name 'David Chen' but every ID field
            -- pointing at James Wilson's actual account/policy — a real inconsistency an opened audit
            -- report would have shown as a mismatched sender/policyholder.
            (:h1, 150000, 'Angela Foster',   'ACC-10006', 'ACH',
             now() - interval '70 hours', 'applied', 'CUST-0006', 'POL-00007'),
            (:h2, 120000, 'Kevin Nakamura',  'ACC-10007', 'Credit Card',
             now() - interval '54 hours', 'applied', 'CUST-0007', 'POL-00008'),
            (:h3, 200000, 'Priscilla Ortiz', 'ACC-10008', 'ACH',
             now() - interval '50 hours', 'applied', 'CUST-0008', 'POL-00009'),
            (:h4, 150000, 'Ben Whitfield',   'ACC-10009', 'ACH',
             now() - interval '34 hours', 'applied', 'CUST-0009', 'POL-00010'),
            -- Applied via human override (analyst overrode hold rec)
            (:h5, 162000, 'Natalie Reyes',   'ACC-10010', 'Check',
             now() - interval '30 hours', 'applied', 'CUST-0010', 'POL-00011'),
            (:h6, 210000, 'Omar Haddad',     'ACC-10011', 'Wire',
             now() - interval '14 hours', 'applied', 'CUST-0011', 'POL-00012'),
            -- Escalated by human (Priya escalated to Damien) — genuinely unmatched, no customer/policy
            (:h7, 75000,  'Unknown Sender',  NULL,        'Wire',
             now() - interval '66 hours', 'escalated', NULL, NULL),
            (:h8, 300000, 'Acme Corp LLC',   NULL,        'Wire',
             now() - interval '10 hours', 'escalated', NULL, NULL),
            -- Returned to sender (Damien resolved) — a duplicate payment, deliberately not tied to any
            -- one customer's identity (the sender is exactly who they say, "Duplicate Payer" is a
            -- placeholder for "we returned this because it was a repeat"), so no matched_customer_id
            (:h9, 90000,  'Duplicate Payer', NULL,        'ACH',
             now() - interval '46 hours', 'returned', NULL, NULL)
        ON CONFLICT (payment_id) DO NOTHING
    """), {"h1": h1, "h2": h2, "h3": h3, "h4": h4, "h5": h5, "h6": h6, "h7": h7, "h8": h8, "h9": h9})

    await db.execute(text("""
        INSERT INTO payment_recommendations
            (payment_id, recommendation, confidence_score, scenario_route,
             decision_path, requires_human_approval, reasoning, suggested_action,
             decision_attribution)
        VALUES
            (:h1, 'apply',    95.0, 'scenario_1', 'Strong policy match → APPLY',
             true, ARRAY['Name match 97%', 'Amount within 1% tolerance', 'Policy active'],
             'Apply to POL-00007', 'human_confirmed'),
            (:h2, 'apply',    88.0, 'scenario_2', 'Customer match, no policy ref → APPLY',
             true, ARRAY['Customer match 94%', 'Account verified', 'Historical pattern matches'],
             'Apply to customer account', 'human_confirmed'),
            (:h3, 'apply',    91.0, 'scenario_1', 'Strong policy match → APPLY',
             true, ARRAY['Name match 99%', 'Amount exact', 'Active policy'],
             'Apply to POL-00009', 'human_confirmed'),
            (:h4, 'apply',    96.0, 'scenario_1', 'Strong policy match → APPLY',
             true, ARRAY['Name match 100%', 'Amount within tolerance', 'Low risk method'],
             'Apply to POL-00010', 'human_confirmed'),
            (:h5, 'hold',     72.0, 'scenario_3', 'Amount variance 8% → HOLD',
             true, ARRAY['Name match 91%', 'Amount 8% over expected premium', 'Manual review needed'],
             'Hold for analyst review', 'human_override'),
            (:h6, 'hold',     65.0, 'scenario_3', 'Amount variance 5% → HOLD',
             true, ARRAY['Name match 95%', 'Amount 5% over expected', 'Quarterly adjustment possible'],
             'Hold for analyst review', 'human_override'),
            (:h7, 'escalate', 12.0, 'scenario_4', 'No customer match → ESCALATE',
             true, ARRAY['Sender name unknown', 'No policy reference', 'No account match'],
             'Route to investigator', 'human_confirmed'),
            (:h8, 'escalate', 8.0,  'scenario_4', 'No customer match → ESCALATE',
             true, ARRAY['Corporate sender unrecognized', 'Amount does not match any policy'],
             'Route to investigator', 'human_confirmed'),
            (:h9, 'escalate', 0.0,  'scenario_5', 'Duplicate detected, $0 balance → ESCALATE',
             true, ARRAY['Exact duplicate of prior payment', 'Policy balance is $0'],
             'Return to sender', 'human_confirmed')
        ON CONFLICT (payment_id) DO NOTHING
    """), {"h1": h1, "h2": h2, "h3": h3, "h4": h4, "h5": h5, "h6": h6, "h7": h7, "h8": h8, "h9": h9})

    # The escalated/returned H-series cases were escalated by Priya. Without an
    # 'escalated' audit row carrying a real actor, the investigator queue's
    # "Escalated By" column renders blank — the API reads it from the latest
    # audit_log row via a LATERAL join.
    await db.execute(text("""
        INSERT INTO audit_log
            (payment_id, action_type, actor, actor_user_id, details, timestamp)
        SELECT v.payment_id, 'escalated', u.name, u.user_id,
               jsonb_build_object('reason', v.reason, 'escalated_to', 'investigator'),
               p.payment_date + interval '2 hours'
        FROM (VALUES
                (:h7, 'no_customer_match'),
                (:h8, 'no_customer_match'),
                (:h9, 'duplicate_zero_balance')
             ) AS v(payment_id, reason)
        JOIN payments p ON p.payment_id = v.payment_id
        CROSS JOIN (SELECT user_id, name FROM users WHERE user_id = 'USR-0001') u
        WHERE NOT EXISTS (
            SELECT 1 FROM audit_log a
            WHERE a.payment_id = v.payment_id AND a.action_type = 'escalated'
        )
    """), {"h7": h7, "h8": h8, "h9": h9})


async def seed_configuration_thresholds(db: AsyncSession) -> None:
    await db.execute(text("""
        INSERT INTO configuration_thresholds (parameter_name, parameter_value, description) VALUES
            ('name_match_auto_apply',           '90',  'Min name similarity % for an Apply recommendation (Scenario 1)'),
            ('name_match_hold',                 '75',  'Min name similarity % to hold vs escalate'),
            ('name_gray_zone_lower',            '70',  'Below this score skip LLM — clear mismatch'),
            ('name_gray_zone_upper',            '92',  'Above this score skip LLM — clear match'),
            ('amount_tolerance_auto',            '2',  'Max variance % for an Apply recommendation (Scenario 1)'),
            ('duplicate_window_hours',          '72',  'Lookback window for duplicate detection (hours)'),
            ('duplicate_amount_tolerance_cents','200', 'Max cent difference for duplicate match ($2.00)'),
            ('multi_period_tolerance',           '5',  'Tolerance % for multi-period payment detection')
        ON CONFLICT (parameter_name) DO UPDATE SET description = EXCLUDED.description
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

        print("Seeding escalated payment for investigation tests...")
        await seed_escalated_payment(db)

        print("Seeding historical payments for governance dashboard...")
        await seed_historical_payments(db)

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
