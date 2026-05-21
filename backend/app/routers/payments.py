import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, StrictInt, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.services.ingest import parse_reference_fields
from app.services.pipeline import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

ALLOWED_PAYMENT_METHODS = {"ACH", "Check", "Credit Card", "Wire"}


# ── Request / Response schemas ────────────────────────────────────────────────

class IngestRequest(BaseModel):
    amount: StrictInt
    sender_name: str
    sender_account: str | None = None
    beneficiary_name: str | None = None
    payment_method: str
    payment_date: datetime
    reference_field_1: str | None = None
    reference_field_2: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive_integer(cls, v):
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            raise ValueError("amount must be a positive integer (cents)")
        return v

    @field_validator("payment_method")
    @classmethod
    def payment_method_must_be_valid(cls, v):
        if v not in ALLOWED_PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {sorted(ALLOWED_PAYMENT_METHODS)}")
        return v


class IngestResponse(BaseModel):
    payment_id: str
    status: str
    created_timestamp: datetime


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _next_payment_id(db: AsyncSession) -> str:
    # Only consider numeric IDs (e.g. PMT-001) — skips seeded non-numeric ones like PMT-ESC-001
    result = await db.execute(text("""
        SELECT MAX(CAST(split_part(payment_id, '-', 2) AS INTEGER))
        FROM payments
        WHERE payment_id ~ '^PMT-[0-9]+$'
    """))
    current_max = result.scalar_one_or_none()
    next_num = (current_max or 0) + 1
    return f"PMT-{next_num:03d}"


# ── Endpoints ─────────────────────────────────────────────────────────────────

async def _run_pipeline_bg(payment_id: str) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await run_pipeline(payment_id, db)
        except Exception:
            logger.exception("Background pipeline failed for %s", payment_id)


@router.post("/ingest", status_code=status.HTTP_201_CREATED, response_model=IngestResponse)
async def ingest_payment(
    body: IngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Parse free-text references with Claude Haiku (never raises)
    parsed = await parse_reference_fields(body.reference_field_1, body.reference_field_2)

    payment_id = await _next_payment_id(db)
    now = datetime.now(timezone.utc)

    await db.execute(text("""
        INSERT INTO payments (
            payment_id, amount, sender_name, sender_account, beneficiary_name,
            payment_method, payment_date, reference_field_1, reference_field_2,
            status, created_timestamp
        ) VALUES (
            :payment_id, :amount, :sender_name, :sender_account, :beneficiary_name,
            :payment_method, :payment_date, :ref1, :ref2,
            'received', :created_timestamp
        )
    """), {
        "payment_id": payment_id,
        "amount": body.amount,
        "sender_name": body.sender_name,
        "sender_account": body.sender_account,
        "beneficiary_name": body.beneficiary_name,
        "payment_method": body.payment_method,
        "payment_date": body.payment_date,
        "ref1": body.reference_field_1,
        "ref2": body.reference_field_2,
        "created_timestamp": now,
    })

    audit_details = json.dumps({
        "amount": body.amount,
        "sender_name": body.sender_name,
        "payment_method": body.payment_method,
        "extracted_policy_number": parsed["extracted_policy_number"],
    })
    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, details, timestamp)
        VALUES (:payment_id, 'received', 'system', CAST(:details AS jsonb), :timestamp)
    """), {
        "payment_id": payment_id,
        "details": audit_details,
        "timestamp": now,
    })

    await db.commit()
    logger.info("Ingested %s — %s %s", payment_id, body.sender_name, body.amount)

    background_tasks.add_task(_run_pipeline_bg, payment_id)

    return IngestResponse(payment_id=payment_id, status="received", created_timestamp=now)


# ── GET /api/payments ─────────────────────────────────────────────────────────

_VALID_SORT = {
    "confidence_score": "pr.confidence_score DESC NULLS LAST",
    "has_risk_flags":   "ps.has_risk_flags DESC NULLS LAST",
    "payment_method":   "p.payment_method ASC",
    "payment_date":     "p.payment_date DESC",
}
_DEFAULT_SORT = "p.payment_date DESC"


@router.get("")
async def list_payments(
    status_filter: Optional[str] = Query(None, alias="status"),
    scenario: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List payments with optional filters, sorted and paginated."""
    conditions = []
    params: dict = {}

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",") if s.strip()]
        if len(statuses) == 1:
            conditions.append("p.status = CAST(:status AS payment_status)")
            params["status"] = statuses[0]
        elif len(statuses) > 1:
            placeholders = ", ".join(f"CAST(:status_{i} AS payment_status)" for i in range(len(statuses)))
            conditions.append(f"p.status IN ({placeholders})")
            for i, s in enumerate(statuses):
                params[f"status_{i}"] = s
    if scenario:
        conditions.append("pr.scenario_route = CAST(:scenario AS scenario_route)")
        params["scenario"] = scenario
    if from_date:
        conditions.append("p.payment_date >= :from_date")
        params["from_date"] = from_date
    if to_date:
        conditions.append("p.payment_date <= :to_date")
        params["to_date"] = to_date
    if search:
        conditions.append("p.sender_name ILIKE :search")
        params["search"] = f"%{search}%"

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    order_clause = _VALID_SORT.get(sort_by or "", _DEFAULT_SORT)

    offset = (page - 1) * page_size
    params["page_size"] = page_size
    params["offset"] = offset

    count_row = await db.execute(text(f"""
        SELECT COUNT(*) FROM payments p
        LEFT JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
        LEFT JOIN payment_signals ps ON ps.payment_id = p.payment_id
        {where_clause}
    """), params)
    total = count_row.scalar_one()

    rows = await db.execute(text(f"""
        SELECT
            p.payment_id, p.amount, p.sender_name, p.sender_account,
            p.beneficiary_name, p.payment_method, p.payment_date, p.status,
            p.reference_field_1, p.reference_field_2,
            p.matched_customer_id, p.matched_policy_id,
            p.investigation_due_date, p.sla_breached, p.created_timestamp,
            pr.recommendation      AS rec_recommendation,
            pr.confidence_score    AS rec_confidence_score,
            pr.scenario_route      AS rec_scenario_route,
            pr.decision_path       AS rec_decision_path,
            pr.requires_human_approval AS rec_requires_human_approval,
            pr.approval_reason     AS rec_approval_reason,
            pr.reasoning           AS rec_reasoning,
            pr.suggested_action    AS rec_suggested_action,
            pr.processing_time_ms  AS rec_processing_time_ms,
            pr.decision_attribution AS rec_decision_attribution,
            pr.created_at          AS rec_created_at,
            ps.has_risk_flags      AS sig_has_risk_flags,
            ps.payment_method_risk_level AS sig_pm_risk,
            ps.name_similarity_score AS sig_name_sim,
            ps.account_status      AS sig_account_status,
            esc.actor              AS escalated_by
        FROM payments p
        LEFT JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
        LEFT JOIN payment_signals ps ON ps.payment_id = p.payment_id
        LEFT JOIN LATERAL (
            SELECT actor FROM audit_log
            WHERE payment_id = p.payment_id AND action_type = 'escalated'
            ORDER BY timestamp DESC LIMIT 1
        ) esc ON true
        {where_clause}
        ORDER BY {order_clause}
        LIMIT :page_size OFFSET :offset
    """), params)

    data = []
    for r in rows.mappings():
        row = dict(r)
        payment_fields = [
            "payment_id", "amount", "sender_name", "sender_account", "beneficiary_name",
            "payment_method", "payment_date", "status", "reference_field_1", "reference_field_2",
            "matched_customer_id", "matched_policy_id", "investigation_due_date",
            "sla_breached", "created_timestamp", "escalated_by",
        ]
        payment = {k: row[k] for k in payment_fields if k in row}
        recommendation = None
        if row.get("rec_recommendation") is not None:
            recommendation = {
                "payment_id":            row["payment_id"],
                "recommendation":        row["rec_recommendation"],
                "confidence_score":      row["rec_confidence_score"],
                "scenario_route":        row["rec_scenario_route"],
                "decision_path":         row["rec_decision_path"],
                "requires_human_approval": row["rec_requires_human_approval"],
                "approval_reason":       row["rec_approval_reason"],
                "reasoning":             row["rec_reasoning"] or [],
                "suggested_action":      row["rec_suggested_action"],
                "processing_time_ms":    row["rec_processing_time_ms"],
                "decision_attribution":  row["rec_decision_attribution"],
                "created_at":            row["rec_created_at"],
            }
        signals = None
        if row.get("sig_has_risk_flags") is not None:
            signals = {
                "payment_id": row["payment_id"],
                "risk": {
                    "has_risk_flags":            row["sig_has_risk_flags"],
                    "payment_method_risk_level": row["sig_pm_risk"],
                    "account_status":            row["sig_account_status"],
                },
                "matching": {"name_similarity_score": row["sig_name_sim"]},
            }
        data.append({"payment": payment, "recommendation": recommendation, "signals": signals})

    return {"payments": data, "total": total, "page": page, "page_size": page_size}


# ── GET /api/payments/{id} ────────────────────────────────────────────────────

@router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Full payment detail: payment + signals (by category) + recommendation + audit + annotations + documents."""
    payment_row = await db.execute(
        text("SELECT * FROM payments WHERE payment_id = :id"),
        {"id": payment_id},
    )
    payment = payment_row.mappings().one_or_none()
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    payment = dict(payment)

    signals_row = await db.execute(
        text("SELECT * FROM payment_signals WHERE payment_id = :id"),
        {"id": payment_id},
    )
    raw_signals = signals_row.mappings().one_or_none()
    if raw_signals:
        s = dict(raw_signals)
        signals = {
            "matching": {
                "name_similarity_score":     s.get("name_similarity_score"),
                "policy_match_confidence":   s.get("policy_match_confidence"),
                "customer_match_confidence": s.get("customer_match_confidence"),
                "account_match":             s.get("account_match"),
                "amount_match":              s.get("amount_match"),
                "historical_match":          s.get("historical_match"),
                "jaro_winkler_score":        s.get("jaro_winkler_score"),
                "levenshtein_score":         s.get("levenshtein_score"),
                "soundex_match":             s.get("soundex_match"),
                "deterministic_score":       s.get("deterministic_score"),
                "used_llm":                  s.get("used_llm"),
                "llm_score":                 s.get("llm_score"),
            },
            "amount": {
                "amount_variance_pct":          s.get("amount_variance_pct"),
                "is_overpayment":               s.get("is_overpayment"),
                "is_underpayment":              s.get("is_underpayment"),
                "difference_amount":            s.get("difference_amount"),
                "is_multi_period":              s.get("is_multi_period"),
                "estimated_periods":            s.get("estimated_periods"),
                "historical_consistency_score": s.get("historical_consistency_score"),
                "is_multi_method":              s.get("is_multi_method"),
                "multi_method_fraction":        s.get("multi_method_fraction"),
                "is_third_party_payment":       s.get("is_third_party_payment"),
                "third_party_relationship":     s.get("third_party_relationship"),
            },
            "temporal": {
                "payment_timing_quality":  s.get("payment_timing_quality"),
                "days_from_due_date":      s.get("days_from_due_date"),
                "days_since_last_payment": s.get("days_since_last_payment"),
            },
            "risk": {
                "has_risk_flags":             s.get("has_risk_flags"),
                "risk_flag_types":            s.get("risk_flag_types") or [],
                "account_status":             s.get("account_status"),
                "payment_method_risk_level":  s.get("payment_method_risk_level"),
                "outstanding_balance_cents":  s.get("outstanding_balance_cents"),
                "outstanding_balance_status": s.get("outstanding_balance_status"),
            },
            "duplicate": {
                "is_duplicate_match":           s.get("is_duplicate_match"),
                "duplicate_payment_id":         s.get("duplicate_payment_id"),
                "hours_since_duplicate":        s.get("hours_since_duplicate"),
                "outstanding_balance_justifies": s.get("outstanding_balance_justifies"),
                "duplicate_amount_difference":  s.get("duplicate_amount_difference"),
            },
        }
    else:
        signals = None

    rec_row = await db.execute(
        text("SELECT * FROM payment_recommendations WHERE payment_id = :id"),
        {"id": payment_id},
    )
    rec = rec_row.mappings().one_or_none()
    recommendation = dict(rec) if rec else None

    audit_rows = await db.execute(
        text("SELECT * FROM audit_log WHERE payment_id = :id ORDER BY timestamp ASC"),
        {"id": payment_id},
    )
    audit_trail = [dict(r) for r in audit_rows.mappings()]
    for entry in audit_trail:
        if "details" in entry and entry["details"] is not None:
            entry["details"] = dict(entry["details"]) if not isinstance(entry["details"], dict) else entry["details"]

    annotation_rows = await db.execute(
        text("SELECT * FROM case_annotations WHERE payment_id = :id ORDER BY created_at ASC"),
        {"id": payment_id},
    )
    annotations = [dict(r) for r in annotation_rows.mappings()]

    doc_rows = await db.execute(
        text("""
            SELECT document_id, payment_id, uploaded_by, file_name, file_type,
                   file_size_bytes, document_type, description, uploaded_at
            FROM case_documents
            WHERE payment_id = :id AND is_deleted = false
            ORDER BY uploaded_at ASC
        """),
        {"id": payment_id},
    )
    documents = [dict(r) for r in doc_rows.mappings()]

    return {
        "payment": payment,
        "signals": signals,
        "recommendation": recommendation,
        "audit_logs": audit_trail,
        "annotations": annotations,
        "documents": documents,
    }
