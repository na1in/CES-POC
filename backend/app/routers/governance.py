"""
Governance endpoints — review log, anomaly flags, audit export.

POST /api/governance/reviews                — Lorraine records a period review
GET  /api/governance/reviews                — list reviews
POST /api/governance/anomalies              — Lorraine flags a metric anomaly
GET  /api/governance/anomalies              — list anomaly flags
PATCH /api/governance/anomalies/{id}        — Marcus updates investigation / resolution
GET  /api/governance/export                 — structured audit-ready report
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

router = APIRouter(prefix="/api/governance", tags=["governance"])

_VALID_ANOMALY_STATUSES = {"open", "investigating", "resolved"}
_EXPORT_SCOPES = {"decisions", "overrides", "config_changes", "all"}


# ── Request bodies ────────────────────────────────────────────────────────────

class ReviewBody(BaseModel):
    period_start: str   # ISO date: YYYY-MM-DD
    period_end: str
    notes: Optional[str] = None
    export_generated: bool = False


class AnomalyBody(BaseModel):
    metric_name: str
    description: str
    scenario_type: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    assigned_to: Optional[str] = None

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be empty")
        return v


class AnomalyUpdateBody(BaseModel):
    status: str
    resolution_notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_ANOMALY_STATUSES:
            raise ValueError(f"status must be one of {sorted(_VALID_ANOMALY_STATUSES)}")
        return v


# ── Pure helpers ──────────────────────────────────────────────────────────────

def is_valid_export_scope(scope: str) -> bool:
    return scope in _EXPORT_SCOPES


# ── POST /reviews ─────────────────────────────────────────────────────────────

@router.post("/reviews", status_code=status.HTTP_201_CREATED)
async def create_review(
    body: ReviewBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_director),
):
    """Lorraine records that she has reviewed a reporting period."""
    result = await db.execute(text("""
        INSERT INTO governance_reviews
            (reviewed_by, period_start, period_end, export_generated, notes)
        VALUES (:reviewer, :start, :end, :exported, :notes)
        RETURNING review_id, review_timestamp
    """), {
        "reviewer": current_user.user_id,
        "start": body.period_start,
        "end": body.period_end,
        "exported": body.export_generated,
        "notes": body.notes,
    })
    row = result.mappings().one()

    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (NULL, 'governance_review_recorded', :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "actor": current_user.name,
        "actor_uid": current_user.user_id,
        "details": json.dumps({
            "review_id": row["review_id"],
            "period_start": body.period_start,
            "period_end": body.period_end,
        }),
    })

    await db.commit()
    return {
        "review_id": row["review_id"],
        "reviewed_by": current_user.user_id,
        "period_start": body.period_start,
        "period_end": body.period_end,
        "review_timestamp": row["review_timestamp"].isoformat(),
    }


# ── GET /reviews ──────────────────────────────────────────────────────────────

@router.get("/reviews")
async def list_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    rows = await db.execute(text("""
        SELECT review_id, reviewed_by, period_start, period_end,
               review_timestamp, export_generated, notes
        FROM governance_reviews
        ORDER BY review_timestamp DESC
    """))
    return {"reviews": [dict(r) for r in rows.mappings()]}


# ── POST /anomalies ───────────────────────────────────────────────────────────

@router.post("/anomalies", status_code=status.HTTP_201_CREATED)
async def flag_anomaly(
    body: AnomalyBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_director),
):
    """Lorraine flags a metric anomaly for Marcus to investigate."""
    result = await db.execute(text("""
        INSERT INTO anomaly_flags
            (metric_name, scenario_type, description, period_start, period_end,
             flagged_by, assigned_to, status)
        VALUES (:metric, :scenario, :desc, :pstart, :pend, :flagged_by, :assigned_to, 'open')
        RETURNING flag_id, flagged_at
    """), {
        "metric": body.metric_name,
        "scenario": body.scenario_type,
        "desc": body.description,
        "pstart": body.period_start,
        "pend": body.period_end,
        "flagged_by": current_user.user_id,
        "assigned_to": body.assigned_to,
    })
    row = result.mappings().one()

    await db.execute(text("""
        INSERT INTO audit_log (payment_id, action_type, actor, actor_user_id, details, timestamp)
        VALUES (NULL, 'anomaly_flagged', :actor, :actor_uid,
                CAST(:details AS jsonb), now())
    """), {
        "actor": current_user.name,
        "actor_uid": current_user.user_id,
        "details": json.dumps({
            "flag_id": row["flag_id"],
            "metric_name": body.metric_name,
        }),
    })

    await db.commit()
    return {
        "flag_id": row["flag_id"],
        "metric_name": body.metric_name,
        "status": "open",
        "flagged_at": row["flagged_at"].isoformat(),
    }


# ── GET /anomalies ────────────────────────────────────────────────────────────

@router.get("/anomalies")
async def list_anomalies(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    params: dict = {}
    where = ""
    if status_filter:
        where = "WHERE status = CAST(:status AS anomaly_flag_status)"
        params["status"] = status_filter

    rows = await db.execute(text(f"""
        SELECT flag_id, metric_name, scenario_type, description, period_start, period_end,
               flagged_by, assigned_to, status, resolution_notes, flagged_at, resolved_at
        FROM anomaly_flags
        {where}
        ORDER BY flagged_at DESC
    """), params)
    return {"anomalies": [dict(r) for r in rows.mappings()]}


# ── PATCH /anomalies/{id} ─────────────────────────────────────────────────────

@router.patch("/anomalies/{flag_id}")
async def update_anomaly(
    flag_id: int,
    body: AnomalyUpdateBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Marcus updates investigation status and optionally adds resolution notes."""
    resolved_at_expr = "resolved_at = now()," if body.status == "resolved" else ""

    result = await db.execute(text(f"""
        UPDATE anomaly_flags
        SET status = CAST(:status AS anomaly_flag_status),
            {resolved_at_expr}
            resolution_notes = COALESCE(:notes, resolution_notes)
        WHERE flag_id = :flag_id
        RETURNING flag_id, status
    """), {
        "flag_id": flag_id,
        "status": body.status,
        "notes": body.resolution_notes,
    })
    updated = result.mappings().one_or_none()
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Anomaly flag {flag_id} not found")

    await db.commit()
    return {"flag_id": flag_id, "status": body.status}


# ── GET /export ───────────────────────────────────────────────────────────────

@router.get("/export")
async def export_report(
    from_date: str = Query(...),
    to_date: str = Query(...),
    scope: str = Query("all"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_director),
):
    """
    Generate an audit-ready structured report for the given date range.
    scope: 'decisions' | 'overrides' | 'config_changes' | 'all'
    """
    if not is_valid_export_scope(scope):
        raise HTTPException(
            status_code=400,
            detail=f"scope must be one of {sorted(_EXPORT_SCOPES)}",
        )

    report: dict = {
        "generated_at": None,
        "period": {"from": from_date, "to": to_date},
        "scope": scope,
        "generated_by": current_user.user_id,
    }

    params = {"from_date": from_date, "to_date": to_date}

    if scope in ("decisions", "all"):
        rows = await db.execute(text("""
            SELECT
                p.payment_id, p.sender_name, p.amount, p.payment_method,
                p.payment_date, p.status,
                pr.recommendation, pr.confidence_score, pr.scenario_route,
                pr.decision_attribution, pr.requires_human_approval
            FROM payments p
            LEFT JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
            WHERE p.payment_date BETWEEN :from_date AND :to_date
            ORDER BY p.payment_date DESC
        """), params)
        report["decisions"] = [dict(r) for r in rows.mappings()]

    if scope in ("overrides", "all"):
        rows = await db.execute(text("""
            SELECT
                p.payment_id, p.sender_name, p.amount, p.payment_method, p.payment_date,
                pr.scenario_route, pr.recommendation AS original_recommendation,
                pr.confidence_score,
                a.content AS override_reason, a.author_user_id AS overridden_by, a.created_at AS overridden_at
            FROM payments p
            JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
            LEFT JOIN LATERAL (
                SELECT content, author_user_id, created_at
                FROM case_annotations
                WHERE payment_id = p.payment_id AND annotation_type = 'override_reason'
                ORDER BY created_at DESC LIMIT 1
            ) a ON true
            WHERE p.payment_date BETWEEN :from_date AND :to_date
              AND pr.decision_attribution = 'human_override'
            ORDER BY p.payment_date DESC
        """), params)
        report["overrides"] = [dict(r) for r in rows.mappings()]

    if scope in ("config_changes", "all"):
        rows = await db.execute(text("""
            SELECT change_id, parameter_name, current_value, proposed_value,
                   rationale, proposed_by, approved_by, status,
                   proposed_at, reviewed_at, deployed_at
            FROM configuration_change_requests
            WHERE proposed_at BETWEEN :from_date AND :to_date
            ORDER BY proposed_at DESC
        """), params)
        report["config_changes"] = [dict(r) for r in rows.mappings()]

    from datetime import datetime, timezone
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    return report
