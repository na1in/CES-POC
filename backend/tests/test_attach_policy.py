"""
Manual policy attach (UX critique item 4).

Covers GET /api/policies/search and POST /api/payments/{id}/attach-policy —
the path that lets an analyst resolve a "No matched policy" case instead of
being forced to escalate or override-and-apply.

Auth: tokens minted directly via create_access_token, as in test_e2e_actions.
LLM: mocked by the autouse fixture in conftest.py.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.models.user import UserRole


def _analyst_headers() -> dict:
    return {"Authorization": f"Bearer {create_access_token('USR-0001', UserRole.analyst)}"}


def _director_headers() -> dict:
    return {"Authorization": f"Bearer {create_access_token('USR-0003', UserRole.director)}"}


async def _unmatched_held_payment(client: AsyncClient, db: AsyncSession) -> str:
    """Ingest a payment with no policy reference and park it in HELD."""
    resp = await client.post("/api/payments/ingest", json={
        "amount": 120000,
        "sender_name": "Nobody In Particular",
        "payment_method": "Wire",
        "payment_date": "2026-05-10T10:00:00Z",
    })
    assert resp.status_code == 201
    pid = resp.json()["payment_id"]
    await db.execute(text("""
        UPDATE payments
        SET status = 'held', matched_policy_id = NULL, matched_customer_id = NULL
        WHERE payment_id = :id
    """), {"id": pid})
    await db.commit()
    return pid


# ── Search ────────────────────────────────────────────────────────────────────

class TestPolicySearch:
    async def test_finds_policy_by_number(self, client: AsyncClient):
        r = await client.get("/api/policies/search?q=POL-00001", headers=_analyst_headers())
        assert r.status_code == 200
        assert "POL-00001" in [p["policy_number"] for p in r.json()["policies"]]

    async def test_finds_policy_by_customer_name(self, client: AsyncClient):
        r = await client.get("/api/policies/search?q=Robert", headers=_analyst_headers())
        assert r.status_code == 200
        policies = r.json()["policies"]
        assert policies, "expected at least one policy for a seeded customer name"
        assert all("Robert" in p["customer_name"] for p in policies)

    async def test_search_is_case_insensitive(self, client: AsyncClient):
        lower = await client.get("/api/policies/search?q=robert", headers=_analyst_headers())
        upper = await client.get("/api/policies/search?q=ROBERT", headers=_analyst_headers())
        assert lower.json()["count"] == upper.json()["count"] > 0

    async def test_active_policies_sort_first(self, client: AsyncClient):
        r = await client.get("/api/policies/search?q=POL", headers=_analyst_headers())
        statuses = [p["status"] for p in r.json()["policies"]]
        actives = [i for i, s in enumerate(statuses) if s == "active"]
        inactives = [i for i, s in enumerate(statuses) if s != "active"]
        if actives and inactives:
            assert max(actives) < min(inactives)

    async def test_no_match_returns_empty_not_error(self, client: AsyncClient):
        r = await client.get("/api/policies/search?q=zzzznope", headers=_analyst_headers())
        assert r.status_code == 200
        assert r.json()["count"] == 0

    async def test_short_query_rejected(self, client: AsyncClient):
        r = await client.get("/api/policies/search?q=a", headers=_analyst_headers())
        assert r.status_code == 422

    async def test_requires_auth(self, client: AsyncClient):
        r = await client.get("/api/policies/search?q=POL")
        assert r.status_code == 401

    async def test_director_is_not_permitted(self, client: AsyncClient):
        r = await client.get("/api/policies/search?q=POL", headers=_director_headers())
        assert r.status_code == 403


# ── Attach ────────────────────────────────────────────────────────────────────

class TestAttachPolicy:
    async def test_attaches_policy_and_customer(self, client: AsyncClient, db: AsyncSession):
        pid = await _unmatched_held_payment(client, db)
        r = await client.post(f"/api/payments/{pid}/attach-policy",
                              json={"policy_number": "POL-00001"},
                              headers=_analyst_headers())
        assert r.status_code == 200
        assert r.json()["matched_policy_id"] == "POL-00001"

        row = (await db.execute(text(
            "SELECT matched_policy_id, matched_customer_id FROM payments WHERE payment_id = :id"
        ), {"id": pid})).mappings().one()
        assert row["matched_policy_id"] == "POL-00001"
        assert row["matched_customer_id"] is not None

    async def test_writes_audit_row_with_actor(self, client: AsyncClient, db: AsyncSession):
        pid = await _unmatched_held_payment(client, db)
        await client.post(f"/api/payments/{pid}/attach-policy",
                          json={"policy_number": "POL-00001", "reason": "Confirmed by phone"},
                          headers=_analyst_headers())
        row = (await db.execute(text("""
            SELECT actor, actor_user_id, details FROM audit_log
            WHERE payment_id = :id AND action_type = 'policy_attached'
        """), {"id": pid})).mappings().one()
        assert row["actor_user_id"] == "USR-0001"
        assert row["details"]["policy_number"] == "POL-00001"
        assert row["details"]["reason"] == "Confirmed by phone"

    async def test_unknown_policy_404(self, client: AsyncClient, db: AsyncSession):
        pid = await _unmatched_held_payment(client, db)
        r = await client.post(f"/api/payments/{pid}/attach-policy",
                              json={"policy_number": "POL-99999"},
                              headers=_analyst_headers())
        assert r.status_code == 404

    async def test_unknown_payment_404(self, client: AsyncClient):
        r = await client.post("/api/payments/PMT-NOPE/attach-policy",
                              json={"policy_number": "POL-00001"},
                              headers=_analyst_headers())
        assert r.status_code == 404

    async def test_closed_payment_409(self, client: AsyncClient, db: AsyncSession):
        pid = await _unmatched_held_payment(client, db)
        await db.execute(text("UPDATE payments SET status='applied' WHERE payment_id=:id"), {"id": pid})
        await db.commit()
        r = await client.post(f"/api/payments/{pid}/attach-policy",
                              json={"policy_number": "POL-00001"},
                              headers=_analyst_headers())
        assert r.status_code == 409

    async def test_reattach_records_previous_policy(self, client: AsyncClient, db: AsyncSession):
        pid = await _unmatched_held_payment(client, db)
        await client.post(f"/api/payments/{pid}/attach-policy",
                          json={"policy_number": "POL-00001"}, headers=_analyst_headers())
        await client.post(f"/api/payments/{pid}/attach-policy",
                          json={"policy_number": "POL-00002"}, headers=_analyst_headers())
        rows = (await db.execute(text("""
            SELECT details FROM audit_log
            WHERE payment_id = :id AND action_type = 'policy_attached'
            ORDER BY log_id
        """), {"id": pid})).mappings().all()
        assert len(rows) == 2
        assert rows[1]["details"]["previous_policy_number"] == "POL-00001"

    async def test_director_is_not_permitted(self, client: AsyncClient, db: AsyncSession):
        pid = await _unmatched_held_payment(client, db)
        r = await client.post(f"/api/payments/{pid}/attach-policy",
                              json={"policy_number": "POL-00001"},
                              headers=_director_headers())
        assert r.status_code == 403
