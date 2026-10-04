"""The audit report must escape HTML exactly once: the signal-check rules read "< 75" / ">100%" in the browser,
not the literal text "&lt; 75" (which is what a double escape renders)."""
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline import run_pipeline


async def test_signal_rule_text_is_escaped_once(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/payments/ingest", json={
        "amount": 120000, "sender_name": "Maria Rodriguez", "sender_account": "ACC-10002",
        "payment_method": "Credit Card", "payment_date": "2026-05-10T10:00:00Z",
    })
    assert resp.status_code == 201
    pid = resp.json()["payment_id"]
    await run_pipeline(pid, db)

    report = await client.get(f"/api/payments/{pid}/audit-report")
    assert report.status_code == 200
    html = report.text
    assert "&amp;lt;" not in html and "&amp;gt;" not in html      # no double escape
    assert "&lt; 75 escalate" in html                               # escaped exactly once -> shows "< 75" in the browser
    assert "&gt;100% escalate" in html
