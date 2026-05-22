"""
Demo Restore Script — resets the database to clean seed state.

Deletes all demo-generated data (payments, annotations, documents, audit logs,
governance records, anomalies, change requests, payment history entries added
during demo) and resets configuration thresholds to their defaults.

Then re-runs seed.py to restore the base seed data (users, customers, policies,
payment history, PMT-ESC-001, default thresholds).

Run with: python scripts/demo_restore.py
Safe to run multiple times — idempotent.
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

# Seed payments that must not be deleted
SEED_PAYMENT_IDS = {
    "PMT-ESC-001",
    "PMT-H-001", "PMT-H-002", "PMT-H-003", "PMT-H-004",
    "PMT-H-005", "PMT-H-006", "PMT-H-007", "PMT-H-008", "PMT-H-009",
}

# Default threshold values (matches seed.py)
DEFAULT_THRESHOLDS = {
    "name_match_auto_apply":            "90",
    "name_match_hold":                  "75",
    "name_gray_zone_lower":             "70",
    "name_gray_zone_upper":             "92",
    "amount_tolerance_auto":             "2",
    "duplicate_window_hours":           "72",
    "duplicate_amount_tolerance_cents": "200",
    "multi_period_tolerance":            "5",
}


async def delete_demo_payments(db: AsyncSession) -> int:
    """Remove all payments except seed data, plus all their related records."""
    result = await db.execute(text("""
        SELECT payment_id FROM payments
        WHERE payment_id != ALL(:seed_ids)
    """), {"seed_ids": list(SEED_PAYMENT_IDS)})
    demo_ids = [row[0] for row in result.fetchall()]

    if not demo_ids:
        return 0

    id_list = tuple(demo_ids)

    await db.execute(text("DELETE FROM audit_log WHERE payment_id = ANY(:ids)"),
                     {"ids": demo_ids})
    await db.execute(text("DELETE FROM case_annotations WHERE payment_id = ANY(:ids)"),
                     {"ids": demo_ids})
    await db.execute(text("DELETE FROM case_documents WHERE payment_id = ANY(:ids)"),
                     {"ids": demo_ids})
    await db.execute(text("DELETE FROM payment_signals WHERE payment_id = ANY(:ids)"),
                     {"ids": demo_ids})
    await db.execute(text("DELETE FROM payment_recommendations WHERE payment_id = ANY(:ids)"),
                     {"ids": demo_ids})
    await db.execute(text("DELETE FROM payments WHERE payment_id = ANY(:ids)"),
                     {"ids": demo_ids})
    return len(demo_ids)


async def reset_seed_escalated_payment(db: AsyncSession) -> None:
    """Restore PMT-ESC-001 to its original held state (AI recommends escalate, awaiting Priya's action)."""
    # Remove any annotations/audit entries added during the demo
    await db.execute(text("""
        DELETE FROM case_annotations WHERE payment_id = 'PMT-ESC-001'
    """))
    # Keep only the original recommendation_made audit entry
    await db.execute(text("""
        DELETE FROM audit_log
        WHERE payment_id = 'PMT-ESC-001'
          AND action_type != 'recommendation_made'
    """))
    # Reset status back to held (Priya must manually escalate)
    await db.execute(text("""
        UPDATE payments
        SET status = 'held',
            investigation_due_date = NULL
        WHERE payment_id = 'PMT-ESC-001'
    """))


async def reset_thresholds(db: AsyncSession) -> None:
    """Reset all configuration thresholds to seed defaults."""
    for name, value in DEFAULT_THRESHOLDS.items():
        await db.execute(text("""
            UPDATE configuration_thresholds
            SET parameter_value = :value
            WHERE parameter_name = :name
        """), {"name": name, "value": value})


async def delete_governance_data(db: AsyncSession) -> None:
    """Remove governance reviews and anomaly flags created during demo."""
    await db.execute(text("DELETE FROM governance_reviews"))
    await db.execute(text("DELETE FROM anomaly_flags"))


async def delete_config_change_requests(db: AsyncSession) -> None:
    """Remove all config change requests created during demo."""
    await db.execute(text("DELETE FROM configuration_change_requests"))


async def reset_policy_balances(db: AsyncSession) -> None:
    """
    Reset policy outstanding_balance to seed values.
    Approve actions during demo may have reduced balances.
    """
    seed_balances = {
        "POL-00001": 0,
        "POL-00002": 0,
        "POL-00003": 0,
        "POL-00004": 0,
        "POL-00005": 0,
        "POL-00006": 45000,
    }
    for policy_number, balance in seed_balances.items():
        await db.execute(text("""
            UPDATE policies
            SET outstanding_balance = :balance, modified_date = now()
            WHERE policy_number = :policy_number
        """), {"balance": balance, "policy_number": policy_number})


async def delete_demo_payment_history(db: AsyncSession) -> None:
    """
    Remove payment_history entries added by approve actions during demo.
    Seed entries are identified by their fixed payment_dates.
    """
    await db.execute(text("""
        DELETE FROM payment_history
        WHERE payment_date > '2026-04-30'::timestamptz
    """))


async def main() -> None:
    print("CES Demo Restore — resetting to seed state\n")

    async with Session() as db:
        print("Deleting demo payment history entries...")
        await delete_demo_payment_history(db)

        print("Deleting demo payments + related records...")
        count = await delete_demo_payments(db)
        print(f"  Removed {count} demo payment(s)")

        print("Resetting PMT-ESC-001 to held state (AI recommends escalate, awaiting Priya)...")
        await reset_seed_escalated_payment(db)

        print("Resetting configuration thresholds to defaults...")
        await reset_thresholds(db)

        print("Deleting governance reviews and anomaly flags...")
        await delete_governance_data(db)

        print("Deleting config change requests...")
        await delete_config_change_requests(db)

        print("Resetting policy outstanding balances...")
        await reset_policy_balances(db)

        await db.commit()

    await engine.dispose()
    print("\nDone. Database restored to clean seed state.")
    print("You can now run demo_payments.py to start a fresh demo session.")


if __name__ == "__main__":
    asyncio.run(main())
