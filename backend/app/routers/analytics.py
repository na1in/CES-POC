"""
Analytics endpoints — decision attribution + override analysis.

GET /api/analytics/decisions  — summary counts, per-scenario breakdown,
                                 payment method breakdown, confidence histogram
GET /api/analytics/overrides  — filterable override detail list
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_BUCKETS = [f"{i * 10}-{(i + 1) * 10}" for i in range(10)]


# ── Pure helpers ──────────────────────────────────────────────────────────────

def _confidence_bucket(score: float) -> str:
    """Map a 0–100 confidence score to a histogram bucket label."""
    return f"{min(int(score // 10), 9) * 10}-{min(int(score // 10), 9) * 10 + 10}"


def _compute_histogram(scores: list) -> dict:
    """Count confidence scores into 10 equal-width buckets."""
    histogram = {b: 0 for b in _BUCKETS}
    for s in scores:
        if s is not None:
            histogram[_confidence_bucket(float(s))] += 1
    return histogram


# ── GET /api/analytics/decisions ─────────────────────────────────────────────

@router.get("/decisions")
async def get_decisions(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Decision attribution breakdown. Optional date range and payment method filter.
    Powers Lorraine's Governance Dashboard and Marcus's Admin Dashboard.
    """
    from datetime import date as _date
    conditions = []
    params: dict = {}

    if from_date:
        conditions.append("p.payment_date >= :from_date")
        params["from_date"] = _date.fromisoformat(from_date)
    if to_date:
        from datetime import timedelta
        conditions.append("p.payment_date < :to_date")
        params["to_date"] = _date.fromisoformat(to_date) + timedelta(days=1)
    if payment_method:
        conditions.append("p.payment_method = :payment_method")
        params["payment_method"] = payment_method

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # ── Summary counts ────────────────────────────────────────────────────────
    summary_row = await db.execute(text(f"""
        SELECT
            COUNT(*) FILTER (WHERE p.status = 'applied'
                AND pr.decision_attribution = 'ai_autonomous')        AS auto_applied,
            COUNT(*) FILTER (WHERE p.status = 'applied'
                AND pr.decision_attribution = 'human_confirmed')       AS applied_human_review,
            COUNT(*) FILTER (WHERE p.status = 'applied'
                AND pr.decision_attribution = 'human_override')        AS applied_human_override,
            COUNT(*) FILTER (WHERE p.status = 'held')                  AS held_pending_review,
            COUNT(*) FILTER (WHERE p.status = 'escalated'
                AND pr.decision_attribution = 'ai_autonomous')         AS escalated_by_ai,
            COUNT(*) FILTER (WHERE p.status = 'escalated'
                AND pr.decision_attribution IN ('human_confirmed','human_override')) AS escalated_by_human,
            COUNT(*) FILTER (WHERE pr.decision_attribution = 'human_override') AS human_overrides,
            COUNT(*) FILTER (WHERE p.status = 'returned')              AS returned,
            COUNT(*) FILTER (WHERE p.status NOT IN
                ('received','processing','processing_failed'))          AS total_processed
        FROM payments p
        LEFT JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
        {where}
    """), params)
    summary = dict(summary_row.mappings().one())

    total = summary["total_processed"] or 1
    summary["override_rate_pct"] = round(
        (summary["human_overrides"] / total) * 100, 2
    )

    # ── Per-scenario breakdown ────────────────────────────────────────────────
    scenario_rows = await db.execute(text(f"""
        SELECT
            pr.scenario_route,
            COUNT(*)                                                     AS volume,
            AVG(pr.confidence_score)                                     AS avg_confidence,
            COUNT(*) FILTER (WHERE pr.decision_attribution = 'ai_autonomous')     AS ai_autonomous,
            COUNT(*) FILTER (WHERE pr.decision_attribution = 'human_confirmed')   AS human_confirmed,
            COUNT(*) FILTER (WHERE pr.decision_attribution = 'human_override')    AS human_override,
            COUNT(*) FILTER (WHERE pr.decision_attribution = 'human_override')    AS override_count,
            COUNT(*) FILTER (WHERE pr.recommendation = 'apply')          AS apply_count,
            COUNT(*) FILTER (WHERE pr.recommendation = 'hold')           AS hold_count,
            COUNT(*) FILTER (WHERE pr.recommendation = 'escalate')       AS escalate_count
        FROM payments p
        JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
        {where}
        GROUP BY pr.scenario_route
        ORDER BY pr.scenario_route
    """), params)
    scenarios = []
    for r in scenario_rows.mappings():
        row = dict(r)
        row["avg_confidence"] = round(float(row["avg_confidence"] or 0), 1)
        scenarios.append(row)

    # ── Payment method breakdown ──────────────────────────────────────────────
    method_rows = await db.execute(text(f"""
        SELECT
            p.payment_method,
            COUNT(*)                                                     AS volume,
            COUNT(*) FILTER (WHERE pr.decision_attribution = 'ai_autonomous')    AS ai_autonomous,
            COUNT(*) FILTER (WHERE pr.decision_attribution = 'human_confirmed')  AS human_confirmed,
            COUNT(*) FILTER (WHERE pr.decision_attribution = 'human_override')   AS human_override
        FROM payments p
        LEFT JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
        {where}
        GROUP BY p.payment_method
        ORDER BY p.payment_method
    """), params)
    methods = [dict(r) for r in method_rows.mappings()]

    # ── Confidence histogram ──────────────────────────────────────────────────
    score_rows = await db.execute(text(f"""
        SELECT pr.confidence_score
        FROM payments p
        JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
        {where}
    """), params)
    scores = [r[0] for r in score_rows]
    histogram = _compute_histogram(scores)

    return {
        "summary": summary,
        "by_scenario": scenarios,
        "by_payment_method": methods,
        "confidence_histogram": histogram,
    }


# ── GET /api/analytics/overrides ─────────────────────────────────────────────

@router.get("/overrides")
async def get_overrides(
    scenario: Optional[str] = Query(None),
    confidence_band: Optional[str] = Query(None, description="e.g. '0-25', '25-50', '50-75', '75-100'"),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Override detail list. Filterable by scenario, confidence band, and date range."""
    from datetime import date as _date
    conditions = ["pr.decision_attribution = 'human_override'"]
    params: dict = {}

    if scenario:
        conditions.append("pr.scenario_route = CAST(:scenario AS scenario_route)")
        params["scenario"] = scenario
    if from_date:
        conditions.append("p.payment_date >= :from_date")
        params["from_date"] = _date.fromisoformat(from_date)
    if to_date:
        from datetime import timedelta
        conditions.append("p.payment_date < :to_date")
        params["to_date"] = _date.fromisoformat(to_date) + timedelta(days=1)
    if confidence_band:
        parts = confidence_band.split("-")
        if len(parts) == 2:
            conditions.append("pr.confidence_score >= :conf_low AND pr.confidence_score < :conf_high")
            params["conf_low"] = float(parts[0])
            params["conf_high"] = float(parts[1])

    where = "WHERE " + " AND ".join(conditions)
    params["page_size"] = page_size
    params["offset"] = (page - 1) * page_size

    count_row = await db.execute(text(f"""
        SELECT COUNT(*)
        FROM payments p
        JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
        {where}
    """), params)
    total = count_row.scalar_one()

    rows = await db.execute(text(f"""
        SELECT
            p.payment_id, p.sender_name, p.amount, p.payment_method,
            p.payment_date, p.status,
            pr.scenario_route, pr.recommendation AS original_recommendation,
            pr.confidence_score, pr.decision_attribution,
            a.content AS override_reason,
            a.author_user_id AS overridden_by,
            a.created_at AS overridden_at
        FROM payments p
        JOIN payment_recommendations pr ON pr.payment_id = p.payment_id
        LEFT JOIN LATERAL (
            SELECT content, author_user_id, created_at
            FROM case_annotations
            WHERE payment_id = p.payment_id
              AND annotation_type = 'override_reason'
            ORDER BY created_at DESC
            LIMIT 1
        ) a ON true
        {where}
        ORDER BY p.payment_date DESC
        LIMIT :page_size OFFSET :offset
    """), params)

    overrides = [dict(r) for r in rows.mappings()]
    return {"overrides": overrides, "total": total, "page": page, "page_size": page_size}
