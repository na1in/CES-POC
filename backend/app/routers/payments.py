import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, StrictInt, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.ingest import parse_reference_fields

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
    result = await db.execute(text("SELECT MAX(payment_id) FROM payments"))
    current_max = result.scalar_one_or_none()
    if current_max is None:
        next_num = 1
    else:
        next_num = int(current_max.split("-")[1]) + 1
    return f"PMT-{next_num:03d}"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/ingest", status_code=status.HTTP_201_CREATED, response_model=IngestResponse)
async def ingest_payment(body: IngestRequest, db: AsyncSession = Depends(get_db)):
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

    return IngestResponse(payment_id=payment_id, status="received", created_timestamp=now)
