import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.signals.amount import (
    compute_amount_variance,
    compute_historical_consistency,
    compute_multi_method,
    compute_multi_period,
    compute_third_party,
)
from app.services.signals.duplicate import compute_duplicate
from app.services.signals.matching import (
    compute_customer_match_confidence,
    compute_name_similarity,
    compute_policy_match_confidence,
)
from app.services.signals.risk import (
    compute_account_status,
    compute_balance_snapshot,
    compute_payment_method_risk,
    compute_risk_flags,
    compute_supporting_signals,
)
from app.services.signals.temporal import compute_timing

logger = logging.getLogger(__name__)


async def run_signal_engine(
    payment_id: str,
    payment: dict,
    customer: dict,
    policy: dict | None,
    db: AsyncSession,
) -> dict:
    """
    Orchestrates all 3 signal waves, persists results to payment_signals, and
    writes a signals_computed audit log entry.

    Does NOT commit — caller owns the transaction.

    payment keys:
        amount, payment_method, payment_date, sender_name, sender_account,
        reference_1, reference_2, extracted_policy_number

    customer keys:
        customer_name, status, outstanding_balance_cents, next_due_date,
        last_payment_date, historical_sender_accounts, historical_amounts,
        risk_flags  (list of {flag_type: str, is_active: bool})

    policy keys (None if no policy match yet):
        policy_number, premium_amount
    """
    premium_amount: int = (policy or {}).get("premium_amount") or 0
    policy_number: str | None = (policy or {}).get("policy_number")
    reference_text = " ".join(
        part for part in [payment.get("reference_1"), payment.get("reference_2")] if part
    ) or None

    # ── Wave 1: async I/O signals (run concurrently) ──────────────────────────
    name_sim, dup = await asyncio.gather(
        compute_name_similarity(payment["sender_name"], customer["customer_name"]),
        compute_duplicate(
            db=db,
            payment_id=payment_id,
            sender_name=payment["sender_name"],
            sender_account=payment.get("sender_account"),
            payment_method=payment["payment_method"],
            payment_date=payment["payment_date"],
            amount=payment["amount"],
        ),
    )

    timing = compute_timing(
        payment_date=payment["payment_date"],
        next_due_date=customer.get("next_due_date"),
        last_payment_date=customer.get("last_payment_date"),
    )
    variance = compute_amount_variance(payment["amount"], premium_amount)

    # ── Wave 2: sync signals (depend on Wave 1 outputs) ───────────────────────
    consistency_score = compute_historical_consistency(
        payment["amount"],
        customer.get("historical_amounts") or [],
    )
    multi_period = compute_multi_period(payment["amount"], premium_amount)
    multi_method = compute_multi_method(payment["amount"], premium_amount)
    third_party = compute_third_party(
        sender_name=payment["sender_name"],
        customer_name=customer["customer_name"],
        name_similarity_score=name_sim["name_similarity_score"],
        reference_text=reference_text,
    )

    # ── Wave 3: pure function signals ─────────────────────────────────────────
    risk_flags = compute_risk_flags(customer.get("risk_flags") or [])
    account_status = compute_account_status(customer.get("status"))
    balance_snapshot = compute_balance_snapshot(
        customer.get("outstanding_balance_cents") or 0,
        customer.get("next_due_date"),
    )
    method_risk = compute_payment_method_risk(payment["payment_method"])
    supporting = compute_supporting_signals(
        sender_account=payment.get("sender_account"),
        historical_sender_accounts=customer.get("historical_sender_accounts") or [],
        amount_variance_pct=variance["amount_variance_pct"],
        historical_consistency_score=consistency_score,
    )
    policy_confidence = compute_policy_match_confidence(
        name_similarity_score=name_sim["name_similarity_score"],
        extracted_policy_number=payment.get("extracted_policy_number"),
        actual_policy_number=policy_number,
        amount_variance_pct=variance["amount_variance_pct"],
    )
    customer_confidence = compute_customer_match_confidence(
        name_similarity_score=name_sim["name_similarity_score"],
        account_match=supporting["account_match"],
        historical_match=supporting["historical_match"],
    )

    # days_from_due_date — temporal.py returns quality string, we store the raw int too
    days_from_due_date: int | None = None
    if customer.get("next_due_date") is not None:
        pmt_date = (
            payment["payment_date"].date()
            if isinstance(payment["payment_date"], datetime)
            else payment["payment_date"]
        )
        days_from_due_date = (pmt_date - customer["next_due_date"]).days

    # outstanding_balance_justifies — only meaningful when a duplicate is detected
    outstanding_balance_justifies = (
        dup["is_duplicate_match"]
        and (customer.get("outstanding_balance_cents") or 0) > 0
    )

    # duplicate_amount_difference is NOT NULL DEFAULT 0 in the schema;
    # compute_duplicate returns None when no duplicate is found.
    if dup.get("duplicate_amount_difference") is None:
        dup["duplicate_amount_difference"] = 0

    # ── Assemble full signals dict ────────────────────────────────────────────
    signals: dict = {
        "payment_id": payment_id,
        **name_sim,
        "policy_match_confidence": policy_confidence,
        "customer_match_confidence": customer_confidence,
        **supporting,
        **variance,
        **multi_period,
        **multi_method,
        **third_party,
        "historical_consistency_score": consistency_score,
        **timing,
        "days_from_due_date": days_from_due_date,
        **risk_flags,
        **account_status,
        **balance_snapshot,
        **method_risk,
        **dup,
        "outstanding_balance_justifies": outstanding_balance_justifies,
    }

    # ── Persist to payment_signals ────────────────────────────────────────────
    # risk_flag_types is a custom enum array — pass as comma-separated text and
    # reconstruct in SQL so asyncpg doesn't need to know the custom type.
    risk_flag_types_str = ",".join(signals["risk_flag_types"]) if signals["risk_flag_types"] else ""

    await db.execute(text("""
        INSERT INTO payment_signals (
            payment_id,
            name_similarity_score, policy_match_confidence, customer_match_confidence,
            account_match, amount_match, historical_match,
            jaro_winkler_score, levenshtein_score, soundex_match,
            deterministic_score, used_llm, llm_score,
            amount_variance_pct, is_overpayment, is_underpayment, difference_amount,
            is_multi_period, estimated_periods,
            historical_consistency_score,
            is_multi_method, multi_method_fraction,
            is_third_party_payment, third_party_relationship,
            payment_timing_quality, days_from_due_date, days_since_last_payment,
            has_risk_flags, risk_flag_types,
            account_status, payment_method_risk_level,
            outstanding_balance_cents, outstanding_balance_status,
            is_duplicate_match, duplicate_payment_id, hours_since_duplicate,
            outstanding_balance_justifies, duplicate_amount_difference
        ) VALUES (
            :payment_id,
            :name_similarity_score, :policy_match_confidence, :customer_match_confidence,
            :account_match, :amount_match, :historical_match,
            :jaro_winkler_score, :levenshtein_score, :soundex_match,
            :deterministic_score, :used_llm, :llm_score,
            :amount_variance_pct, :is_overpayment, :is_underpayment, :difference_amount,
            :is_multi_period, :estimated_periods,
            :historical_consistency_score,
            :is_multi_method, :multi_method_fraction,
            :is_third_party_payment, :third_party_relationship,
            CAST(:payment_timing_quality AS payment_timing_quality),
            :days_from_due_date, :days_since_last_payment,
            :has_risk_flags,
            CAST(string_to_array(NULLIF(:risk_flag_types_str, ''), ',') AS risk_flag_type[]),
            CAST(:account_status AS account_status),
            CAST(:payment_method_risk_level AS payment_method_risk_level),
            :outstanding_balance_cents, :outstanding_balance_status,
            :is_duplicate_match, :duplicate_payment_id, :hours_since_duplicate,
            :outstanding_balance_justifies, :duplicate_amount_difference
        )
    """), {
        **signals,
        "risk_flag_types_str": risk_flag_types_str,
    })

    # ── Write audit log entry ─────────────────────────────────────────────────
    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, details)
        VALUES (:payment_id, 'signals_computed', 'system', CAST(:details AS jsonb))
    """), {
        "payment_id": payment_id,
        "details": json.dumps({
            "name_similarity_score": signals["name_similarity_score"],
            "policy_match_confidence": signals["policy_match_confidence"],
            "customer_match_confidence": signals["customer_match_confidence"],
            "is_duplicate_match": signals["is_duplicate_match"],
            "has_risk_flags": signals["has_risk_flags"],
        }),
    })

    return signals
