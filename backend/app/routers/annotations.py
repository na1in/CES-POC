"""
Annotation endpoints — case notes, override reasons, contact records, investigation notes.

POST /api/payments/{id}/annotations  — add annotation; contact_record also transitions
                                        payment → pending_sender_response
GET  /api/payments/{id}/annotations  — list all annotations for a payment
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["annotations"])

_VALID_ANNOTATION_TYPES = {"case_note", "override_reason", "contact_record", "investigation_note"}
_CONTACT_REQUIRED_STATUSES = {"escalated"}


# ── Request body ──────────────────────────────────────────────────────────────

class AnnotationBody(BaseModel):
    annotation_type: str
    content: str
    contact_method: Optional[str] = None    # phone | email | letter
    contact_outcome: Optional[str] = None   # reached | no_answer | voicemail | bounced
    contacted_party: Optional[str] = None

    @field_validator("annotation_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in _VALID_ANNOTATION_TYPES:
            raise ValueError(f"annotation_type must be one of {sorted(_VALID_ANNOTATION_TYPES)}")
        return v

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty")
        return v


# ── Pure helpers (unit-testable) ──────────────────────────────────────────────

def requires_contact_fields(annotation_type: str) -> bool:
    return annotation_type == "contact_record"


def contact_record_triggers_pending(payment_status: str) -> bool:
    """True if adding a contact_record should move the payment to pending_sender_response."""
    return payment_status in _CONTACT_REQUIRED_STATUSES


# ── POST /annotations ─────────────────────────────────────────────────────────

@router.post("/{payment_id}/annotations", status_code=status.HTTP_201_CREATED)
async def add_annotation(
    payment_id: str,
    body: AnnotationBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Add a case annotation. contact_record triggers PENDING_SENDER_RESPONSE if currently ESCALATED."""
    if requires_contact_fields(body.annotation_type) and not body.contact_method:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="contact_method is required for contact_record annotations",
        )

    payment_row = await db.execute(
        text("SELECT status FROM payments WHERE payment_id = :id"),
        {"id": payment_id},
    )
    payment = payment_row.mappings().one_or_none()
    if payment is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")

    result = await db.execute(text("""
        INSERT INTO case_annotations (
            payment_id, author_user_id, annotation_type, content,
            contact_method, contact_outcome, contacted_party
        )
        VALUES (
            :payment_id, :author, CAST(:atype AS annotation_type), :content,
            :contact_method, :contact_outcome, :contacted_party
        )
        RETURNING annotation_id, created_at
    """), {
        "payment_id": payment_id,
        "author": current_user.user_id,
        "atype": body.annotation_type,
        "content": body.content,
        "contact_method": body.contact_method,
        "contact_outcome": body.contact_outcome,
        "contacted_party": body.contacted_party,
    })
    row = result.mappings().one()
    annotation_id = row["annotation_id"]
    created_at = row["created_at"]

    audit_action = "contact_logged" if body.annotation_type == "contact_record" else "annotated"
    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (:pid, CAST(:atype AS audit_action_type), :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "pid": payment_id,
        "atype": audit_action,
        "actor": current_user.name,
        "actor_uid": current_user.user_id,
        "details": f'{{"annotation_type": "{body.annotation_type}", "annotation_id": {annotation_id}}}',
    })

    status_changed = False
    if body.annotation_type == "contact_record" and contact_record_triggers_pending(payment["status"]):
        await db.execute(text("""
            UPDATE payments SET status = 'pending_sender_response' WHERE payment_id = :id
        """), {"id": payment_id})
        status_changed = True

    await db.commit()
    logger.info("%s added %s annotation on %s", current_user.user_id, body.annotation_type, payment_id)

    return {
        "annotation_id": annotation_id,
        "payment_id": payment_id,
        "annotation_type": body.annotation_type,
        "created_at": created_at.isoformat(),
        "status_changed_to": "pending_sender_response" if status_changed else None,
    }


# ── GET /annotations ──────────────────────────────────────────────────────────

@router.get("/{payment_id}/annotations")
async def list_annotations(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all annotations for a payment, oldest first."""
    exists = await db.execute(
        text("SELECT 1 FROM payments WHERE payment_id = :id"),
        {"id": payment_id},
    )
    if exists.one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")

    rows = await db.execute(text("""
        SELECT annotation_id, payment_id, author_user_id, annotation_type, content,
               contact_method, contact_outcome, contacted_party, created_at
        FROM case_annotations
        WHERE payment_id = :id
        ORDER BY created_at ASC
    """), {"id": payment_id})

    return {"annotations": [dict(r) for r in rows.mappings()]}
