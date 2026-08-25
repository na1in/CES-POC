"""
Policy lookup endpoints.

GET /api/policies/search — find a policy by number or customer name, so an
analyst staring at "No matched policy" can resolve the match by hand instead
of being forced to escalate or override-and-apply.
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, require_analyst_or_investigator
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/policies", tags=["policies"])

_MAX_RESULTS = 20


@router.get("/search")
async def search_policies(
    q: str = Query(..., min_length=2, description="Policy number or customer name fragment"),
    limit: int = Query(10, ge=1, le=_MAX_RESULTS),
    current_user: CurrentUser = Depends(require_analyst_or_investigator),
    db: AsyncSession = Depends(get_db),
):
    """
    Case-insensitive substring search over policy number and customer name.

    Active policies sort first — an analyst attaching a policy almost always
    wants a live one, and attaching a non-active policy is rejected downstream.
    """
    rows = await db.execute(text("""
        SELECT
            p.policy_number,
            p.customer_id,
            c.name              AS customer_name,
            p.policy_type,
            p.premium_amount,
            p.premium_frequency::text AS premium_frequency,
            p.status::text      AS status,
            p.outstanding_balance,
            p.next_due_date
        FROM policies p
        JOIN customers c ON c.customer_id = p.customer_id
        WHERE p.policy_number ILIKE :pattern
           OR c.name ILIKE :pattern
        ORDER BY (p.status = 'active') DESC, p.policy_number
        LIMIT :limit
    """), {"pattern": f"%{q.strip()}%", "limit": limit})

    policies = [dict(r) for r in rows.mappings()]
    return {"policies": policies, "count": len(policies), "query": q}
