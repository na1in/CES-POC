"""
CES-25 / CES-26: Analyst & Investigator Action Endpoints

POST /api/payments/{id}/approve    — Priya: HELD → APPLIED + ledger
POST /api/payments/{id}/reject     — Priya: HELD → ESCALATED + SLA deadline
POST /api/payments/{id}/override   — Priya/Damien: explicit recommendation override
POST /api/payments/{id}/return     — Damien: ESCALATED/PENDING → RETURNED
POST /api/payments/{id}/reprocess  — Any: PROCESSING_FAILED → re-run pipeline
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, require_analyst, require_analyst_or_investigator, require_investigator
from app.database import get_db
from app.services.pipeline import run_pipeline
from app.services.persist import _SLA_HOURS, _target_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["approvals"])

_OVERRIDE_ACTIONS = {"APPLY", "HOLD", "ESCALATE"}
_APPROVABLE_STATUSES = {"held"}
_REJECTABLE_STATUSES = {"held"}
_RETURNABLE_STATUSES = {"escalated", "pending_sender_response"}
_REPROCESSABLE_STATUSES = {"processing_failed"}
_OVERRIDABLE_STATUSES = {"held", "escalated", "processing", "received"}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _load_payment(payment_id: str, db: AsyncSession) -> dict:
    row = await db.execute(
        text("SELECT * FROM payments WHERE payment_id = :id"),
        {"id": payment_id},
    )
    result = row.mappings().one_or_none()
    if result is None:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    return dict(result)


def _assert_status(payment: dict, allowed: set[str], action: str) -> None:
    if payment["status"] not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot {action} a payment with status '{payment['status']}'"
        )


async def _apply_ledger(payment: dict, policy_id: str | None, db: AsyncSession) -> None:
    """Insert payment_history and reduce policy outstanding_balance."""
    if not policy_id:
        return
    now = datetime.now(timezone.utc)
    await db.execute(text("""
        INSERT INTO payment_history (policy_id, payment_date, amount, payment_method, sender_account, status)
        VALUES (:policy_id, :payment_date, :amount, :payment_method, :sender_account, 'applied')
    """), {
        "policy_id": policy_id,
        "payment_date": payment.get("payment_date") or now,
        "amount": payment["amount"],
        "payment_method": payment["payment_method"],
        "sender_account": payment.get("sender_account"),
    })
    await db.execute(text("""
        UPDATE policies
        SET outstanding_balance = GREATEST(0, outstanding_balance - :amount),
            modified_date = now()
        WHERE policy_number = :policy_number
    """), {"policy_number": policy_id, "amount": payment["amount"]})


async def _write_annotation(
    payment_id: str,
    author_user_id: str,
    annotation_type: str,
    content: str,
    db: AsyncSession,
) -> None:
    await db.execute(text("""
        INSERT INTO case_annotations (payment_id, author_user_id, annotation_type, content)
        VALUES (:payment_id, :author, CAST(:atype AS annotation_type), :content)
    """), {
        "payment_id": payment_id,
        "author": author_user_id,
        "atype": annotation_type,
        "content": content,
    })


async def _write_audit(
    payment_id: str,
    action_type: str,
    actor: str,
    actor_user_id: str,
    details: dict,
    db: AsyncSession,
) -> None:
    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (:pid, CAST(:atype AS audit_action_type), :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "pid": payment_id,
        "atype": action_type,
        "actor": actor,
        "actor_uid": actor_user_id,
        "details": json.dumps(details),
    })


# ── Request bodies ────────────────────────────────────────────────────────────

class NotesBody(BaseModel):
    notes: str | None = None


class OverrideBody(BaseModel):
    override_action: str   # "APPLY" | "HOLD" | "ESCALATE"
    reason: str


# ── POST /approve ─────────────────────────────────────────────────────────────

@router.post("/{payment_id}/approve")
async def approve_payment(
    payment_id: str,
    body: NotesBody = NotesBody(),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """Priya approves a HELD payment → APPLIED. Triggers ledger update."""
    payment = await _load_payment(payment_id, db)
    _assert_status(payment, _APPROVABLE_STATUSES, "approve")

    policy_id = payment.get("matched_policy_id")

    await _apply_ledger(payment, policy_id, db)

    await db.execute(text("""
        UPDATE payments SET status = 'applied' WHERE payment_id = :id
    """), {"id": payment_id})

    await db.execute(text("""
        UPDATE payment_recommendations
        SET decision_attribution = 'human_confirmed'
        WHERE payment_id = :id
    """), {"id": payment_id})

    if body.notes:
        await _write_annotation(payment_id, current_user.user_id, "case_note", body.notes, db)

    await _write_audit(payment_id, "approved", current_user.name, current_user.user_id,
                       {"policy_id": policy_id}, db)
    await _write_audit(payment_id, "applied", current_user.name, current_user.user_id,
                       {"via": "human_approval"}, db)

    await db.commit()
    logger.info("%s approved %s → applied", current_user.user_id, payment_id)
    return {"payment_id": payment_id, "status": "applied", "decision_attribution": "human_confirmed"}


# ── POST /reject ──────────────────────────────────────────────────────────────

@router.post("/{payment_id}/reject")
async def reject_payment(
    payment_id: str,
    body: NotesBody = NotesBody(),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
):
    """Priya rejects a HELD payment → ESCALATED. Sets SLA deadline for Damien."""
    payment = await _load_payment(payment_id, db)
    _assert_status(payment, _REJECTABLE_STATUSES, "reject")

    due_date = datetime.now(timezone.utc) + timedelta(hours=_SLA_HOURS)

    await db.execute(text("""
        UPDATE payments
        SET status = 'escalated', investigation_due_date = :due_date
        WHERE payment_id = :id
    """), {"id": payment_id, "due_date": due_date})

    await db.execute(text("""
        UPDATE payment_recommendations
        SET decision_attribution = 'human_confirmed'
        WHERE payment_id = :id
    """), {"id": payment_id})

    if body.notes:
        await _write_annotation(payment_id, current_user.user_id, "case_note", body.notes, db)

    await _write_audit(payment_id, "escalated", current_user.name, current_user.user_id,
                       {"via": "analyst_rejection", "sla_due": due_date.isoformat()}, db)

    await db.commit()
    logger.info("%s rejected %s → escalated", current_user.user_id, payment_id)
    return {
        "payment_id": payment_id,
        "status": "escalated",
        "investigation_due_date": due_date.isoformat(),
    }


# ── POST /override ────────────────────────────────────────────────────────────

@router.post("/{payment_id}/override")
async def override_payment(
    payment_id: str,
    body: OverrideBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst_or_investigator),
):
    """Priya or Damien explicitly overrides the AI recommendation. Reason is mandatory."""
    if body.override_action not in _OVERRIDE_ACTIONS:
        raise HTTPException(status_code=400, detail=f"override_action must be one of {_OVERRIDE_ACTIONS}")

    payment = await _load_payment(payment_id, db)
    _assert_status(payment, _OVERRIDABLE_STATUSES, "override")

    new_status = _target_status(body.override_action, requires_human_approval=False)
    policy_id = payment.get("matched_policy_id")
    due_date = None

    if new_status == "applied":
        await _apply_ledger(payment, policy_id, db)
    elif new_status == "escalated":
        due_date = datetime.now(timezone.utc) + timedelta(hours=_SLA_HOURS)

    await db.execute(text("""
        UPDATE payments
        SET status = CAST(:status AS payment_status),
            investigation_due_date = :due_date
        WHERE payment_id = :id
    """), {"id": payment_id, "status": new_status, "due_date": due_date})

    await db.execute(text("""
        UPDATE payment_recommendations
        SET decision_attribution = 'human_override'
        WHERE payment_id = :id
    """), {"id": payment_id})

    await _write_annotation(payment_id, current_user.user_id, "override_reason", body.reason, db)

    await _write_audit(payment_id, "overridden", current_user.name, current_user.user_id, {
        "override_action": body.override_action,
        "new_status": new_status,
        "reason_preview": body.reason[:120],
    }, db)
    if new_status == "applied":
        await _write_audit(payment_id, "applied", current_user.name, current_user.user_id,
                           {"via": "human_override"}, db)
    elif new_status == "escalated":
        await _write_audit(payment_id, "escalated", current_user.name, current_user.user_id,
                           {"via": "human_override"}, db)

    await db.commit()
    logger.info("%s overrode %s → %s", current_user.user_id, payment_id, new_status)
    return {"payment_id": payment_id, "status": new_status, "decision_attribution": "human_override"}


# ── POST /return ──────────────────────────────────────────────────────────────

@router.post("/{payment_id}/return")
async def return_payment(
    payment_id: str,
    body: NotesBody = NotesBody(),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_investigator),
):
    """Damien marks a payment as returned to sender after investigation."""
    payment = await _load_payment(payment_id, db)
    _assert_status(payment, _RETURNABLE_STATUSES, "return")

    await db.execute(text("""
        UPDATE payments SET status = 'returned' WHERE payment_id = :id
    """), {"id": payment_id})

    if body.notes:
        await _write_annotation(payment_id, current_user.user_id, "investigation_note", body.notes, db)

    await _write_audit(payment_id, "returned", current_user.name, current_user.user_id,
                       {"notes_provided": bool(body.notes)}, db)

    await db.commit()
    logger.info("%s marked %s as returned", current_user.user_id, payment_id)
    return {"payment_id": payment_id, "status": "returned"}


# ── POST /reprocess ───────────────────────────────────────────────────────────

@router.post("/{payment_id}/reprocess")
async def reprocess_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Re-run the full pipeline for a PROCESSING_FAILED payment. Clears partial state first."""
    payment = await _load_payment(payment_id, db)
    _assert_status(payment, _REPROCESSABLE_STATUSES, "reprocess")

    # Clear any partial state from the failed run before re-running
    await db.execute(text("DELETE FROM payment_signals WHERE payment_id = :id"), {"id": payment_id})
    await db.execute(text("DELETE FROM payment_recommendations WHERE payment_id = :id"), {"id": payment_id})
    await db.execute(text("UPDATE payments SET status = 'received' WHERE payment_id = :id"), {"id": payment_id})
    await db.commit()

    recommendation = await run_pipeline(payment_id, db)
    return {
        "payment_id": payment_id,
        "status": _target_status(
            recommendation["recommendation"],
            recommendation.get("requires_human_approval", True),
        ),
        "recommendation": recommendation,
    }
