"""Escalation audit wording ("confirmed" vs "rejected") and the Override Analysis listing."""
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.models.user import UserRole
from app.services.pipeline import run_pipeline


def _headers(user_id: str, role: UserRole) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


async def _held(client: AsyncClient, db: AsyncSession, body: dict) -> str:
    resp = await client.post("/api/payments/ingest", json={"payment_date": "2026-05-10T10:00:00Z", **body})
    assert resp.status_code == 201
    pid = resp.json()["payment_id"]
    await run_pipeline(pid, db)
    return pid


async def test_escalating_an_escalate_recommendation_says_confirmed(client: AsyncClient, db: AsyncSession):
    pid = await _held(client, db, {"amount": 50000, "sender_name": "Zxqvf Bljrpm 99999", "payment_method": "Wire"})
    assert (await client.get(f"/api/payments/{pid}")).json()["recommendation"]["recommendation"] == "escalate"
    assert (await client.post(f"/api/payments/{pid}/reject", headers=_headers("USR-0001", UserRole.analyst))).status_code == 200

    html = (await client.get(f"/api/payments/{pid}/audit-report")).text
    assert "Escalated to investigator — analyst confirmed the system recommendation." in html
    assert "analyst rejected the system recommendation" not in html


async def test_escalating_a_hold_recommendation_says_rejected(client: AsyncClient, db: AsyncSession):
    pid = await _held(client, db, {"amount": 120000, "sender_name": "Maria Rodriguez", "sender_account": "ACC-10002",
                                   "payment_method": "Credit Card"})
    assert (await client.get(f"/api/payments/{pid}")).json()["recommendation"]["recommendation"] != "escalate"
    assert (await client.post(f"/api/payments/{pid}/reject", headers=_headers("USR-0001", UserRole.analyst))).status_code == 200

    html = (await client.get(f"/api/payments/{pid}/audit-report")).text
    assert "Escalated — analyst rejected the system recommendation." in html
    assert "analyst confirmed" not in html


async def test_override_analysis_lists_only_real_overrides(client: AsyncClient, db: AsyncSession):
    pid = await _held(client, db, {"amount": 50000, "sender_name": "Zxqvf Bljrpm 99999", "payment_method": "Wire"})
    resp = await client.post(f"/api/payments/{pid}/override", headers=_headers("USR-0001", UserRole.analyst),
                             json={"override_action": "APPLY", "reason": "Verified by phone with the sender."})
    assert resp.status_code == 200

    data = (await client.get("/api/analytics/overrides", headers=_headers("USR-0004", UserRole.admin))).json()
    assert data["total"] == len(data["overrides"]) >= 1
    for row in data["overrides"]:                      # every listed case has a reason, a date and an analyst
        assert row["override_reason"] and row["overridden_at"] and row["overridden_by"] and row["overridden_by_name"]
    assert pid in {row["payment_id"] for row in data["overrides"]}
