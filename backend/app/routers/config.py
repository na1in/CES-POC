"""
Configuration management endpoints — threshold management + change-request workflow.

GET  /api/settings/thresholds                           — current active thresholds
GET  /api/settings/thresholds/history                   — full version history
POST /api/settings/change-requests                      — Marcus proposes a change
GET  /api/settings/change-requests                      — list (filterable by status)
POST /api/settings/change-requests/{id}/approve         — Lorraine approves
POST /api/settings/change-requests/{id}/reject          — Lorraine rejects (mandatory comment)
POST /api/settings/change-requests/{id}/deploy          — Marcus deploys approved change
POST /api/settings/change-requests/{id}/rollback        — Emergency rollback (director or admin)
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user, require_admin, require_director
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["config"])

_DEPLOYABLE_STATE = "approved"
_ROLLBACKABLE_STATE = "deployed"


# ── Request bodies ────────────────────────────────────────────────────────────

class ChangeRequestBody(BaseModel):
    parameter_name: str
    proposed_value: str
    rationale: str
    projected_impact: Optional[str] = None

    @field_validator("rationale")
    @classmethod
    def rationale_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("rationale must not be empty")
        return v


class RejectBody(BaseModel):
    comment: str

    @field_validator("comment")
    @classmethod
    def comment_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("comment is required when rejecting a change request")
        return v


# ── Pure helpers ──────────────────────────────────────────────────────────────

def can_deploy(change: dict) -> bool:
    return change.get("status") == _DEPLOYABLE_STATE


def can_rollback(change: dict) -> bool:
    return change.get("status") == _ROLLBACKABLE_STATE


# ── GET /thresholds ───────────────────────────────────────────────────────────

@router.get("/thresholds")
async def get_thresholds(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return all active configuration thresholds."""
    rows = await db.execute(text("""
        SELECT parameter_name, parameter_value, description, effective_date
        FROM configuration_thresholds
        ORDER BY parameter_name
    """))
    return {"thresholds": [dict(r) for r in rows.mappings()]}


# ── GET /thresholds/history ───────────────────────────────────────────────────

@router.get("/thresholds/history")
async def get_threshold_history(
    parameter_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Full version history. Optionally filter by parameter name."""
    params: dict = {}
    where = ""
    if parameter_name:
        where = "WHERE parameter_name = :param"
        params["param"] = parameter_name

    rows = await db.execute(text(f"""
        SELECT version_id, parameter_name, parameter_value, changed_by, approved_by,
               rationale, change_request_id, effective_from, effective_to
        FROM configuration_threshold_history
        {where}
        ORDER BY effective_from DESC
    """), params)
    return {"history": [dict(r) for r in rows.mappings()]}


# ── POST /change-requests ─────────────────────────────────────────────────────

@router.post("/change-requests", status_code=status.HTTP_201_CREATED)
async def propose_change(
    body: ChangeRequestBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Marcus proposes a threshold change. Enters 'pending' state for Lorraine to review."""
    current_row = await db.execute(text("""
        SELECT parameter_value FROM configuration_thresholds
        WHERE parameter_name = :param
    """), {"param": body.parameter_name})
    current = current_row.scalar_one_or_none()
    if current is None:
        raise HTTPException(
            status_code=404,
            detail=f"Parameter '{body.parameter_name}' not found",
        )

    result = await db.execute(text("""
        INSERT INTO configuration_change_requests
            (parameter_name, current_value, proposed_value, rationale,
             projected_impact, proposed_by, status)
        VALUES (:param, :current, :proposed, :rationale, :impact, :proposed_by, 'pending')
        RETURNING change_id, proposed_at
    """), {
        "param": body.parameter_name,
        "current": current,
        "proposed": body.proposed_value,
        "rationale": body.rationale,
        "impact": body.projected_impact,
        "proposed_by": current_user.user_id,
    })
    row = result.mappings().one()

    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (NULL, 'config_change_proposed', :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "actor": current_user.name,
        "actor_uid": current_user.user_id,
        "details": json.dumps({
            "change_id": row["change_id"],
            "parameter_name": body.parameter_name,
            "current_value": current,
            "proposed_value": body.proposed_value,
        }),
    })

    await db.commit()
    return {
        "change_id": row["change_id"],
        "parameter_name": body.parameter_name,
        "current_value": current,
        "proposed_value": body.proposed_value,
        "status": "pending",
        "proposed_at": row["proposed_at"].isoformat(),
    }


# ── GET /change-requests ──────────────────────────────────────────────────────

@router.get("/change-requests")
async def list_change_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    params: dict = {}
    where = ""
    if status_filter:
        where = "WHERE status = CAST(:status AS config_change_status)"
        params["status"] = status_filter

    rows = await db.execute(text(f"""
        SELECT change_id, parameter_name, current_value, proposed_value, rationale,
               projected_impact, proposed_by, approved_by, review_comment,
               status, proposed_at, reviewed_at, deployed_at
        FROM configuration_change_requests
        {where}
        ORDER BY proposed_at DESC
    """), params)
    return {"change_requests": [dict(r) for r in rows.mappings()]}


# ── Shared helper: load change request ───────────────────────────────────────

async def _load_change_request(change_id: int, db: AsyncSession) -> dict:
    row = await db.execute(text("""
        SELECT * FROM configuration_change_requests WHERE change_id = :id
    """), {"id": change_id})
    result = row.mappings().one_or_none()
    if result is None:
        raise HTTPException(status_code=404, detail=f"Change request {change_id} not found")
    return dict(result)


# ── POST /change-requests/{id}/approve ───────────────────────────────────────

@router.post("/change-requests/{change_id}/approve")
async def approve_change_request(
    change_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_director),
):
    """Lorraine approves a pending change request."""
    change = await _load_change_request(change_id, db)
    if change["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve a change request with status '{change['status']}'",
        )

    await db.execute(text("""
        UPDATE configuration_change_requests
        SET status = 'approved', approved_by = :approver, reviewed_at = now()
        WHERE change_id = :id
    """), {"id": change_id, "approver": current_user.user_id})

    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (NULL, 'config_change_approved', :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "actor": current_user.name,
        "actor_uid": current_user.user_id,
        "details": json.dumps({"change_id": change_id, "parameter_name": change["parameter_name"]}),
    })

    await db.commit()
    return {"change_id": change_id, "status": "approved"}


# ── POST /change-requests/{id}/reject ────────────────────────────────────────

@router.post("/change-requests/{change_id}/reject")
async def reject_change_request(
    change_id: int,
    body: RejectBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_director),
):
    """Lorraine rejects a pending change request. Comment is mandatory."""
    change = await _load_change_request(change_id, db)
    if change["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject a change request with status '{change['status']}'",
        )

    await db.execute(text("""
        UPDATE configuration_change_requests
        SET status = 'rejected', approved_by = :reviewer,
            review_comment = :comment, reviewed_at = now()
        WHERE change_id = :id
    """), {"id": change_id, "reviewer": current_user.user_id, "comment": body.comment})

    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (NULL, 'config_change_rejected', :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "actor": current_user.name,
        "actor_uid": current_user.user_id,
        "details": json.dumps({
            "change_id": change_id,
            "parameter_name": change["parameter_name"],
            "comment": body.comment,
        }),
    })

    await db.commit()
    return {"change_id": change_id, "status": "rejected"}


# ── POST /change-requests/{id}/deploy ────────────────────────────────────────

@router.post("/change-requests/{change_id}/deploy")
async def deploy_change_request(
    change_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Marcus deploys an approved change. Atomically:
      1. Close out old history entry (effective_to = now)
      2. Update configuration_thresholds to new value
      3. Insert new history entry
      4. Mark change request as deployed
    """
    change = await _load_change_request(change_id, db)
    if not can_deploy(change):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot deploy a change request with status '{change['status']}' (must be 'approved')",
        )

    param = change["parameter_name"]

    # Close active history entry
    await db.execute(text("""
        UPDATE configuration_threshold_history
        SET effective_to = now()
        WHERE parameter_name = :param AND effective_to IS NULL
    """), {"param": param})

    # Update active threshold
    await db.execute(text("""
        UPDATE configuration_thresholds
        SET parameter_value = :value, effective_date = now()
        WHERE parameter_name = :param
    """), {"param": param, "value": change["proposed_value"]})

    # Insert new history entry
    await db.execute(text("""
        INSERT INTO configuration_threshold_history
            (parameter_name, parameter_value, changed_by, approved_by,
             rationale, change_request_id, effective_from)
        VALUES (:param, :value, :changed_by, :approved_by,
                :rationale, :change_id, now())
    """), {
        "param": param,
        "value": change["proposed_value"],
        "changed_by": current_user.user_id,
        "approved_by": change["approved_by"],
        "rationale": change["rationale"],
        "change_id": change_id,
    })

    # Mark request as deployed
    await db.execute(text("""
        UPDATE configuration_change_requests
        SET status = 'deployed', deployed_at = now()
        WHERE change_id = :id
    """), {"id": change_id})

    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (NULL, 'config_change_deployed', :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "actor": current_user.name,
        "actor_uid": current_user.user_id,
        "details": json.dumps({
            "change_id": change_id,
            "parameter_name": param,
            "old_value": change["current_value"],
            "new_value": change["proposed_value"],
        }),
    })

    await db.commit()
    logger.info("%s deployed config change %d: %s = %s",
                current_user.user_id, change_id, param, change["proposed_value"])
    return {
        "change_id": change_id,
        "parameter_name": param,
        "old_value": change["current_value"],
        "new_value": change["proposed_value"],
        "status": "deployed",
    }


# ── POST /change-requests/{id}/rollback ──────────────────────────────────────

@router.post("/change-requests/{change_id}/rollback")
async def rollback_change_request(
    change_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_director),
):
    """
    Emergency rollback of a deployed change. Restores the previous value from
    configuration_threshold_history. Director-initiated (Lorraine).
    """
    change = await _load_change_request(change_id, db)
    if not can_rollback(change):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot rollback a change request with status '{change['status']}' (must be 'deployed')",
        )

    param = change["parameter_name"]

    # Find the previous value (the history entry that was closed when this was deployed)
    prev_row = await db.execute(text("""
        SELECT parameter_value, version_id
        FROM configuration_threshold_history
        WHERE parameter_name = :param
          AND change_request_id != :change_id
        ORDER BY effective_from DESC
        LIMIT 1
    """), {"param": param, "change_id": change_id})
    prev = prev_row.mappings().one_or_none()

    if prev is None:
        raise HTTPException(
            status_code=409,
            detail="No previous value found to rollback to",
        )

    prev_value = prev["parameter_value"]

    # Close current active history entry
    await db.execute(text("""
        UPDATE configuration_threshold_history
        SET effective_to = now()
        WHERE parameter_name = :param AND effective_to IS NULL
    """), {"param": param})

    # Restore previous value
    await db.execute(text("""
        UPDATE configuration_thresholds
        SET parameter_value = :value, effective_date = now()
        WHERE parameter_name = :param
    """), {"param": param, "value": prev_value})

    # Insert rollback history entry
    await db.execute(text("""
        INSERT INTO configuration_threshold_history
            (parameter_name, parameter_value, changed_by, approved_by,
             rationale, change_request_id, effective_from)
        VALUES (:param, :value, :changed_by, :approved_by,
                :rationale, :change_id, now())
    """), {
        "param": param,
        "value": prev_value,
        "changed_by": current_user.user_id,
        "approved_by": current_user.user_id,
        "rationale": f"Emergency rollback of change_id={change_id}",
        "change_id": change_id,
    })

    # Mark request as rolled back
    await db.execute(text("""
        UPDATE configuration_change_requests
        SET status = 'rolled_back'
        WHERE change_id = :id
    """), {"id": change_id})

    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (NULL, 'config_change_rolled_back', :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "actor": current_user.name,
        "actor_uid": current_user.user_id,
        "details": json.dumps({
            "change_id": change_id,
            "parameter_name": param,
            "rolled_back_value": change["proposed_value"],
            "restored_value": prev_value,
        }),
    })

    await db.commit()
    logger.info("%s rolled back config change %d: %s restored to %s",
                current_user.user_id, change_id, param, prev_value)
    return {
        "change_id": change_id,
        "parameter_name": param,
        "rolled_back_value": change["proposed_value"],
        "restored_value": prev_value,
        "status": "rolled_back",
    }
