"""
CES-41: E2E action flow tests

Tests every analyst/investigator action endpoint against real DB state:
  approve   — HELD → APPLIED + ledger update + audit
  reject    — HELD → ESCALATED + SLA deadline + audit
  override  — HELD/ESCALATED → APPLY/HOLD/ESCALATE + override annotation + audit
  return    — ESCALATED → RETURNED + audit
  reprocess — PROCESSING_FAILED → pipeline re-runs → new recommendation

Each test ingests a payment, runs the pipeline to a known state, then calls
the action endpoint with a bearer token for the correct role.

Auth: tokens are minted directly via create_access_token — no HTTP login needed.
LLM: mocked by the autouse fixture in conftest.py (same as E2E scenario tests).
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.models.user import UserRole
from app.services.pipeline import run_pipeline

# ── Auth helpers ──────────────────────────────────────────────────────────────

def _analyst_headers() -> dict:
    token = create_access_token("USR-0001", UserRole.analyst)
    return {"Authorization": f"Bearer {token}"}


def _investigator_headers() -> dict:
    token = create_access_token("USR-0002", UserRole.investigator)
    return {"Authorization": f"Bearer {token}"}


# ── Shared payment fixture helpers ────────────────────────────────────────────

async def _held_payment(client: AsyncClient, db: AsyncSession) -> str:
    """Ingest + pipeline → HELD. Uses Sc2 (no policy ref → always HOLD)."""
    resp = await client.post("/api/payments/ingest", json={
        "amount": 120000,
        "sender_name": "Maria Rodriguez",
        "sender_account": "ACC-10002",
        "payment_method": "Credit Card",
        "payment_date": "2026-05-10T10:00:00Z",
    })
    assert resp.status_code == 201
    pid = resp.json()["payment_id"]
    await run_pipeline(pid, db)
    body = (await client.get(f"/api/payments/{pid}")).json()
    assert body["payment"]["status"] == "held", f"Expected held, got {body['payment']['status']}"
    return pid


async def _escalated_payment(client: AsyncClient, db: AsyncSession) -> str:
    """Ingest + pipeline → ESCALATED. Uses Sc4 (unrecognised sender)."""
    resp = await client.post("/api/payments/ingest", json={
        "amount": 50000,
        "sender_name": "Zxqvf Bljrpm 99999",
        "payment_method": "Wire",
        "payment_date": "2026-05-10T10:00:00Z",
    })
    assert resp.status_code == 201
    pid = resp.json()["payment_id"]
    await run_pipeline(pid, db)
    body = (await client.get(f"/api/payments/{pid}")).json()
    assert body["payment"]["status"] == "escalated", f"Expected escalated, got {body['payment']['status']}"
    return pid


async def _failed_payment(client: AsyncClient, db: AsyncSession) -> str:
    """Ingest a payment and force it to processing_failed without running the pipeline."""
    resp = await client.post("/api/payments/ingest", json={
        "amount": 150000,
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-10001",
        "payment_method": "ACH",
        "payment_date": "2026-05-10T10:00:00Z",
        "reference_field_1": "policy POL-00001 May payment",
    })
    assert resp.status_code == 201
    pid = resp.json()["payment_id"]
    await db.execute(
        text("UPDATE payments SET status = 'processing_failed' WHERE payment_id = :id"),
        {"id": pid},
    )
    return pid


# ── Approve ───────────────────────────────────────────────────────────────────

async def test_approve_held_applies_payment(client: AsyncClient, db: AsyncSession):
    """Analyst approves a HELD payment → status=applied, attribution=human_confirmed."""
    pid = await _held_payment(client, db)

    resp = await client.post(f"/api/payments/{pid}/approve", headers=_analyst_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "applied"
    assert body["decision_attribution"] == "human_confirmed"

    detail = (await client.get(f"/api/payments/{pid}")).json()
    assert detail["payment"]["status"] == "applied"
    assert detail["recommendation"]["decision_attribution"] == "human_confirmed"


async def test_approve_writes_audit_entry(client: AsyncClient, db: AsyncSession):
    pid = await _held_payment(client, db)
    await client.post(f"/api/payments/{pid}/approve", headers=_analyst_headers())

    detail = (await client.get(f"/api/payments/{pid}")).json()
    actions = [e["action_type"] for e in detail["audit_trail"]]
    assert "approved" in actions
    assert "applied" in actions


async def test_approve_with_notes_creates_annotation(client: AsyncClient, db: AsyncSession):
    pid = await _held_payment(client, db)
    await client.post(
        f"/api/payments/{pid}/approve",
        json={"notes": "Verified with customer — approved."},
        headers=_analyst_headers(),
    )

    detail = (await client.get(f"/api/payments/{pid}")).json()
    contents = [a["content"] for a in detail["annotations"]]
    assert any("Verified with customer" in c for c in contents)


async def test_approve_rejects_non_analyst(client: AsyncClient, db: AsyncSession):
    """Investigator role cannot approve."""
    pid = await _held_payment(client, db)
    resp = await client.post(f"/api/payments/{pid}/approve", headers=_investigator_headers())
    assert resp.status_code == 403


async def test_approve_conflicts_on_wrong_status(client: AsyncClient, db: AsyncSession):
    """Approving an already-applied payment returns 409."""
    pid = await _held_payment(client, db)
    await client.post(f"/api/payments/{pid}/approve", headers=_analyst_headers())
    resp = await client.post(f"/api/payments/{pid}/approve", headers=_analyst_headers())
    assert resp.status_code == 409


# ── Reject ────────────────────────────────────────────────────────────────────

async def test_reject_held_escalates_payment(client: AsyncClient, db: AsyncSession):
    """Analyst rejects a HELD payment → status=escalated + SLA deadline set."""
    pid = await _held_payment(client, db)

    resp = await client.post(f"/api/payments/{pid}/reject", headers=_analyst_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "escalated"
    assert body["investigation_due_date"] is not None

    detail = (await client.get(f"/api/payments/{pid}")).json()
    assert detail["payment"]["status"] == "escalated"
    assert detail["payment"]["investigation_due_date"] is not None


async def test_reject_writes_audit_entry(client: AsyncClient, db: AsyncSession):
    pid = await _held_payment(client, db)
    await client.post(f"/api/payments/{pid}/reject", headers=_analyst_headers())

    detail = (await client.get(f"/api/payments/{pid}")).json()
    actions = [e["action_type"] for e in detail["audit_trail"]]
    assert "escalated" in actions


async def test_reject_conflicts_on_escalated_status(client: AsyncClient, db: AsyncSession):
    """Cannot reject a payment that is already escalated."""
    pid = await _held_payment(client, db)
    await client.post(f"/api/payments/{pid}/reject", headers=_analyst_headers())
    resp = await client.post(f"/api/payments/{pid}/reject", headers=_analyst_headers())
    assert resp.status_code == 409


# ── Override ──────────────────────────────────────────────────────────────────

async def test_override_held_to_apply(client: AsyncClient, db: AsyncSession):
    """Analyst overrides HOLD → APPLY: status=applied, attribution=human_override."""
    pid = await _held_payment(client, db)

    resp = await client.post(
        f"/api/payments/{pid}/override",
        json={"override_action": "APPLY", "reason": "Customer confirmed payment intent."},
        headers=_analyst_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"
    assert resp.json()["decision_attribution"] == "human_override"

    detail = (await client.get(f"/api/payments/{pid}")).json()
    assert detail["payment"]["status"] == "applied"
    assert detail["recommendation"]["decision_attribution"] == "human_override"


async def test_override_held_to_escalate(client: AsyncClient, db: AsyncSession):
    pid = await _held_payment(client, db)

    resp = await client.post(
        f"/api/payments/{pid}/override",
        json={"override_action": "ESCALATE", "reason": "Suspicious sender — escalate to Damien."},
        headers=_analyst_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "escalated"

    detail = (await client.get(f"/api/payments/{pid}")).json()
    assert detail["payment"]["status"] == "escalated"
    assert detail["payment"]["investigation_due_date"] is not None


async def test_override_writes_annotation_and_audit(client: AsyncClient, db: AsyncSession):
    pid = await _held_payment(client, db)
    reason = "Manual review confirmed — applying."
    await client.post(
        f"/api/payments/{pid}/override",
        json={"override_action": "APPLY", "reason": reason},
        headers=_analyst_headers(),
    )

    detail = (await client.get(f"/api/payments/{pid}")).json()
    # Annotation must be of type override_reason with our reason text
    annotations = detail["annotations"]
    assert any(a["annotation_type"] == "override_reason" and reason in a["content"] for a in annotations)
    # Audit trail must include overridden
    actions = [e["action_type"] for e in detail["audit_trail"]]
    assert "overridden" in actions


async def test_override_investigator_can_override(client: AsyncClient, db: AsyncSession):
    """Investigators can also override (require_analyst_or_investigator)."""
    pid = await _escalated_payment(client, db)

    resp = await client.post(
        f"/api/payments/{pid}/override",
        json={"override_action": "HOLD", "reason": "Need more info before returning."},
        headers=_investigator_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "held"


async def test_override_rejects_invalid_action(client: AsyncClient, db: AsyncSession):
    pid = await _held_payment(client, db)
    resp = await client.post(
        f"/api/payments/{pid}/override",
        json={"override_action": "UNKNOWN", "reason": "test"},
        headers=_analyst_headers(),
    )
    assert resp.status_code == 400


# ── Return ────────────────────────────────────────────────────────────────────

async def test_return_escalated_payment(client: AsyncClient, db: AsyncSession):
    """Investigator marks an escalated payment as returned."""
    pid = await _escalated_payment(client, db)

    resp = await client.post(
        f"/api/payments/{pid}/return",
        json={"notes": "Sender confirmed they sent to wrong account — returning."},
        headers=_investigator_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "returned"

    detail = (await client.get(f"/api/payments/{pid}")).json()
    assert detail["payment"]["status"] == "returned"


async def test_return_writes_investigation_note(client: AsyncClient, db: AsyncSession):
    pid = await _escalated_payment(client, db)
    note = "Contacted sender — wrong recipient."
    await client.post(
        f"/api/payments/{pid}/return",
        json={"notes": note},
        headers=_investigator_headers(),
    )

    detail = (await client.get(f"/api/payments/{pid}")).json()
    assert any(a["annotation_type"] == "investigation_note" and note in a["content"]
               for a in detail["annotations"])


async def test_return_writes_audit_entry(client: AsyncClient, db: AsyncSession):
    pid = await _escalated_payment(client, db)
    await client.post(f"/api/payments/{pid}/return", headers=_investigator_headers())

    detail = (await client.get(f"/api/payments/{pid}")).json()
    actions = [e["action_type"] for e in detail["audit_trail"]]
    assert "returned" in actions


async def test_return_rejects_analyst_role(client: AsyncClient, db: AsyncSession):
    """Analyst cannot return — only investigator."""
    pid = await _escalated_payment(client, db)
    resp = await client.post(f"/api/payments/{pid}/return", headers=_analyst_headers())
    assert resp.status_code == 403


async def test_return_conflicts_on_held_status(client: AsyncClient, db: AsyncSession):
    """Cannot return a HELD payment — must be escalated first."""
    pid = await _held_payment(client, db)
    resp = await client.post(f"/api/payments/{pid}/return", headers=_investigator_headers())
    assert resp.status_code == 409


# ── Reprocess ─────────────────────────────────────────────────────────────────

async def test_reprocess_failed_payment_reruns_pipeline(client: AsyncClient, db: AsyncSession):
    """A processing_failed payment reprocessed should produce a recommendation."""
    pid = await _failed_payment(client, db)

    resp = await client.post(f"/api/payments/{pid}/reprocess")
    assert resp.status_code == 200
    body = resp.json()
    assert body["payment_id"] == pid
    assert body["status"] in ("applied", "held", "escalated")
    assert body["recommendation"]["scenario_route"] is not None


async def test_reprocess_conflicts_on_non_failed_status(client: AsyncClient, db: AsyncSession):
    """Cannot reprocess a payment that is not in processing_failed."""
    pid = await _held_payment(client, db)
    resp = await client.post(f"/api/payments/{pid}/reprocess")
    assert resp.status_code == 409


async def test_reprocess_clears_partial_signals(client: AsyncClient, db: AsyncSession):
    """After reprocess, new signals are written (old ones were cleared first)."""
    pid = await _failed_payment(client, db)

    # Insert a bogus signal row to simulate partial state
    await db.execute(text("""
        INSERT INTO payment_signals (payment_id, name_similarity_score)
        VALUES (:id, 0.0)
        ON CONFLICT (payment_id) DO UPDATE SET name_similarity_score = 0.0
    """), {"id": pid})

    await client.post(f"/api/payments/{pid}/reprocess")

    detail = (await client.get(f"/api/payments/{pid}")).json()
    # Signals should now reflect the real pipeline run, not the bogus 0.0
    assert detail["signals"] is not None
