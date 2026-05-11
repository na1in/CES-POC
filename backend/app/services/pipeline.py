"""
CES-24: Pipeline Orchestrator

Runs the full 5-stage processing pipeline for a single payment:
  load → set PROCESSING → parse refs → find customer/policy →
  signal engine → route → scenario handler → persist → commit

Entry point: run_pipeline(payment_id, db)

Retry strategy:
  - 3 attempts total (immediate → +1s → +3s)
  - Retryable: DB operational errors, deadlocks, Claude API timeouts / rate limits
  - Non-retryable: constraint violations, validation errors, unknown errors
  - After exhausting all attempts: status → processing_failed
"""
import asyncio
import logging
import time

import anthropic
import jellyfish
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent.router import route_scenario
from app.services.agent.scenarios import sc1, sc2, sc3, sc4, sc5
from app.services.ingest import parse_reference_fields
from app.services.persist import persist_recommendation
from app.services.signal_engine import run_signal_engine

logger = logging.getLogger(__name__)

RETRY_DELAYS = [1.0, 3.0]  # sleep seconds before attempt 2 and 3

_SCENARIO_HANDLERS = {
    1: sc1.run,
    2: sc2.run,
    3: sc3.run,
    4: sc4.run,
    5: sc5.run,
}


# ── Retry classification ──────────────────────────────────────────────────────

def _is_retryable(exc: Exception) -> bool:
    """
    True for transient failures worth retrying.
    False for errors that will never succeed on retry.
    Unknown exception types default to False (fail fast).
    """
    if isinstance(exc, (IntegrityError, ProgrammingError, ValueError)):
        return False
    if isinstance(exc, (
        anthropic.APITimeoutError,
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
    )):
        return True
    if isinstance(exc, OperationalError):
        # Covers DB timeouts, deadlocks, connection drops (all wrapped by SQLAlchemy)
        return True
    return False


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _load_payment(payment_id: str, db: AsyncSession) -> dict:
    row = await db.execute(
        text("SELECT * FROM payments WHERE payment_id = :id"),
        {"id": payment_id},
    )
    result = row.mappings().one_or_none()
    if result is None:
        raise ValueError(f"Payment {payment_id} not found")
    return dict(result)


async def _find_best_customer(sender_name: str, db: AsyncSession) -> dict | None:
    """
    Scans all active customers and returns the one with the highest
    Jaro-Winkler similarity to sender_name.

    Returns None if no customer exceeds the 0.5 floor (avoids binding
    an unrelated customer when no real match exists — routes to Scenario 4).
    """
    rows = await db.execute(
        text("SELECT customer_id, name FROM customers WHERE status = 'active'")
    )
    customers = [dict(r) for r in rows.mappings()]
    if not customers:
        return None

    best = max(
        customers,
        key=lambda c: jellyfish.jaro_winkler_similarity(
            sender_name.lower(), c["name"].lower()
        ),
    )
    score = jellyfish.jaro_winkler_similarity(sender_name.lower(), best["name"].lower())
    return best if score > 0.5 else None


async def _load_customer_dict(customer_id: str, db: AsyncSession) -> dict:
    """Assembles the customer dict expected by run_signal_engine."""
    customer_row = await db.execute(
        text("SELECT * FROM customers WHERE customer_id = :id"),
        {"id": customer_id},
    )
    customer = customer_row.mappings().one_or_none()
    if customer is None:
        raise ValueError(f"Customer {customer_id} not found")
    customer = dict(customer)

    risk_rows = await db.execute(
        text("SELECT flag_type, is_active FROM risk_flags WHERE customer_id = :id"),
        {"id": customer_id},
    )
    risk_flags = [dict(r) for r in risk_rows.mappings()]

    # Sum outstanding balance + earliest next_due across all active policies
    balance_row = await db.execute(text("""
        SELECT COALESCE(SUM(outstanding_balance), 0) AS total_balance,
               MIN(next_due_date)                    AS next_due_date
        FROM policies
        WHERE customer_id = :cid AND status = 'active'
    """), {"cid": customer_id})
    balance = balance_row.mappings().one()

    # Last 24 payments from any of this customer's policies
    history_rows = await db.execute(text("""
        SELECT ph.amount, ph.sender_account, ph.payment_date
        FROM payment_history ph
        JOIN policies p ON ph.policy_id = p.policy_number
        WHERE p.customer_id = :cid
        ORDER BY ph.payment_date DESC
        LIMIT 24
    """), {"cid": customer_id})
    history = [dict(r) for r in history_rows.mappings()]

    last_payment_date = None
    if history:
        pd = history[0]["payment_date"]
        last_payment_date = pd.date() if hasattr(pd, "date") else pd

    return {
        "customer_name": customer["name"],
        "status": customer["status"],
        "outstanding_balance_cents": int(balance["total_balance"]),
        "next_due_date": balance["next_due_date"],
        "last_payment_date": last_payment_date,
        "historical_sender_accounts": list(
            {r["sender_account"] for r in history if r["sender_account"]}
        ),
        "historical_amounts": [r["amount"] for r in history],
        "risk_flags": risk_flags,
    }


async def _load_active_policies(customer_id: str, db: AsyncSession) -> list[dict]:
    rows = await db.execute(text("""
        SELECT policy_number  AS policy_id,
               policy_number,
               premium_amount AS premium_amount_cents,
               policy_type,
               status
        FROM policies
        WHERE customer_id = :cid AND status = 'active'
    """), {"cid": customer_id})
    return [dict(r) for r in rows.mappings()]


async def _resolve_customer_and_policy(
    payment: dict, db: AsyncSession
) -> tuple[dict, dict | None, list[dict], str | None]:
    """
    Returns (customer_dict, policy_dict|None, active_policies, customer_id|None).

    Resolution order:
      1. extracted_policy_number → look up policy → derive customer via FK
      2. sender_name → best Jaro-Winkler match across active customers
      3. No match → minimal stub dict (signals/router will route to Scenario 4)
    """
    policy_number = payment.get("extracted_policy_number")
    policy: dict | None = None
    customer_id: str | None = None

    if policy_number:
        pol_row = await db.execute(
            text("SELECT policy_number, premium_amount, customer_id FROM policies WHERE policy_number = :pn"),
            {"pn": policy_number},
        )
        pol = pol_row.mappings().one_or_none()
        if pol:
            policy = {
                "policy_number": pol["policy_number"],
                "premium_amount": pol["premium_amount"],
            }
            customer_id = pol["customer_id"]

    if customer_id is None:
        best = await _find_best_customer(payment["sender_name"], db)
        if best:
            customer_id = best["customer_id"]

    if customer_id is None:
        # No match — stub customer so the signal engine can still compute a near-zero similarity
        stub = {
            "customer_name": payment["sender_name"],
            "status": "active",
            "outstanding_balance_cents": 0,
            "next_due_date": None,
            "last_payment_date": None,
            "historical_sender_accounts": [],
            "historical_amounts": [],
            "risk_flags": [],
        }
        return stub, None, [], None

    customer = await _load_customer_dict(customer_id, db)
    active_policies = await _load_active_policies(customer_id, db)
    return customer, policy, active_policies, customer_id


def _build_context(
    customer: dict,
    customer_id: str | None,
    policy: dict | None,
    active_policies: list[dict],
) -> dict:
    return {
        "customer_id": customer_id,
        "customer_name": customer.get("customer_name"),
        "policy_id": policy["policy_number"] if policy else None,
        "policy_number": policy["policy_number"] if policy else None,
        "active_policy_count": len(active_policies),
        "active_policies": active_policies,
    }


# ── Core pipeline ─────────────────────────────────────────────────────────────

async def _process_payment(payment_id: str, db: AsyncSession) -> dict:
    start = time.monotonic()

    payment = await _load_payment(payment_id, db)

    await db.execute(
        text("UPDATE payments SET status = 'processing' WHERE payment_id = :id"),
        {"id": payment_id},
    )

    # Re-parse reference fields to get extracted_policy_number (not persisted at ingest)
    parsed_refs = await parse_reference_fields(
        payment.get("reference_field_1"), payment.get("reference_field_2")
    )
    payment = {**payment, **parsed_refs}

    customer, policy, active_policies, customer_id = await _resolve_customer_and_policy(payment, db)
    signals = await run_signal_engine(payment_id, payment, customer, policy, db)
    routing = await route_scenario(payment, signals, db)
    context = _build_context(customer, customer_id, policy, active_policies)

    handler = _SCENARIO_HANDLERS[routing.scenario]
    recommendation = await handler(payment, signals, context, routing.thresholds)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    await persist_recommendation(payment_id, payment, recommendation, elapsed_ms, db)
    await db.commit()

    logger.info(
        "Pipeline complete: payment=%s scenario=%d recommendation=%s "
        "confidence=%.1f path=%s elapsed_ms=%d",
        payment_id,
        routing.scenario,
        recommendation["recommendation"],
        recommendation["confidence_score"],
        recommendation["decision_path"],
        elapsed_ms,
    )
    return recommendation


# ── Retry wrapper ─────────────────────────────────────────────────────────────

async def _mark_failed(payment_id: str, error_detail: str, db: AsyncSession) -> None:
    """
    Fallback after all retries exhausted or non-retryable error.
    Sets status to processing_failed so the UI can surface it.
    Note: audit_action_type enum does not include 'processing_failed' — the
    status update alone is sufficient for the queue dashboard to show the case.
    """
    try:
        await db.rollback()
        await db.execute(
            text("UPDATE payments SET status = 'processing_failed' WHERE payment_id = :id"),
            {"id": payment_id},
        )
        await db.commit()
        logger.info("Marked %s as processing_failed", payment_id)
    except Exception as mark_exc:
        logger.error("Failed to mark %s as processing_failed: %s", payment_id, mark_exc)


async def run_pipeline(payment_id: str, db: AsyncSession) -> dict:
    """
    Run the full pipeline with retry.

    Returns the recommendation dict on success.
    Raises the last exception after all retries are exhausted.
    """
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            return await _process_payment(payment_id, db)
        except Exception as exc:
            last_exc = exc

            if not _is_retryable(exc):
                logger.error(
                    "Non-retryable pipeline error for %s (attempt %d): %s: %s",
                    payment_id, attempt + 1, type(exc).__name__, exc,
                )
                await _mark_failed(payment_id, str(exc), db)
                raise

            logger.warning(
                "Retryable pipeline error for %s (attempt %d/3): %s: %s",
                payment_id, attempt + 1, type(exc).__name__, exc,
            )
            await db.rollback()

            if attempt < len(RETRY_DELAYS):
                await asyncio.sleep(RETRY_DELAYS[attempt])

    logger.error("All 3 pipeline attempts failed for %s", payment_id)
    await _mark_failed(payment_id, str(last_exc), db)
    raise last_exc  # type: ignore[misc]
