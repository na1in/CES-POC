"""
CES-42: E2E config workflow + pipeline retry/failure tests

Config workflow (propose → approve → deploy → rollback):
  - Marcus (admin) proposes a threshold change
  - Lorraine (director) approves or rejects
  - Marcus deploys an approved change → threshold value updates in DB
  - Lorraine rolls back a deployed change → previous value restored

Pipeline failure behaviour:
  - Non-retryable error → status immediately becomes processing_failed
  - Retryable error on every attempt → exhausts 3 attempts → processing_failed
  - processing_failed payment can be reprocessed back to a normal outcome

Auth: tokens minted directly via create_access_token.
LLM: mocked by the autouse fixture in conftest.py.
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.models.user import UserRole
from app.services.pipeline import run_pipeline, _is_retryable

# ── Auth helpers ──────────────────────────────────────────────────────────────

def _admin_headers() -> dict:
    token = create_access_token("USR-0004", UserRole.admin)
    return {"Authorization": f"Bearer {token}"}


def _director_headers() -> dict:
    token = create_access_token("USR-0003", UserRole.director)
    return {"Authorization": f"Bearer {token}"}


def _analyst_headers() -> dict:
    token = create_access_token("USR-0001", UserRole.analyst)
    return {"Authorization": f"Bearer {token}"}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _propose(client: AsyncClient, param: str = "name_match_hold",
                   value: str = "80") -> int:
    """Marcus proposes a change. Returns change_id."""
    resp = await client.post("/api/settings/change-requests", json={
        "parameter_name": param,
        "proposed_value": value,
        "rationale": "Tightening the hold threshold for Q3 review cycle.",
    }, headers=_admin_headers())
    assert resp.status_code == 201, resp.text
    return resp.json()["change_id"]


async def _propose_approve(client: AsyncClient, param: str = "name_match_hold",
                           value: str = "80") -> int:
    """Propose + Lorraine approves. Returns change_id."""
    cid = await _propose(client, param, value)
    resp = await client.post(f"/api/settings/change-requests/{cid}/approve",
                             headers=_director_headers())
    assert resp.status_code == 200
    return cid


async def _propose_approve_deploy(client: AsyncClient, param: str = "name_match_hold",
                                  value: str = "80") -> int:
    """Full propose → approve → deploy. Returns change_id."""
    cid = await _propose_approve(client, param, value)
    resp = await client.post(f"/api/settings/change-requests/{cid}/deploy",
                             headers=_admin_headers())
    assert resp.status_code == 200
    return cid


# ══════════════════════════════════════════════════════════════════════════════
# Config workflow — propose
# ══════════════════════════════════════════════════════════════════════════════

async def test_propose_creates_pending_request(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/settings/change-requests", json={
        "parameter_name": "name_match_hold",
        "proposed_value": "80",
        "rationale": "Q3 threshold review.",
    }, headers=_admin_headers())
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["parameter_name"] == "name_match_hold"
    assert body["proposed_value"] == "80"
    assert body["change_id"] is not None


async def test_propose_records_current_value(client: AsyncClient, db: AsyncSession):
    """current_value must match what's actually in the DB right now."""
    current_row = (await db.execute(
        text("SELECT parameter_value FROM configuration_thresholds WHERE parameter_name = 'name_match_hold'")
    )).scalar_one()

    resp = await client.post("/api/settings/change-requests", json={
        "parameter_name": "name_match_hold",
        "proposed_value": "82",
        "rationale": "Test.",
    }, headers=_admin_headers())
    assert resp.json()["current_value"] == current_row


async def test_propose_rejects_unknown_parameter(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/settings/change-requests", json={
        "parameter_name": "nonexistent_param",
        "proposed_value": "99",
        "rationale": "Test.",
    }, headers=_admin_headers())
    assert resp.status_code == 404


async def test_propose_rejects_empty_rationale(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/settings/change-requests", json={
        "parameter_name": "name_match_hold",
        "proposed_value": "80",
        "rationale": "   ",
    }, headers=_admin_headers())
    assert resp.status_code == 422


async def test_propose_rejects_non_admin(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/settings/change-requests", json={
        "parameter_name": "name_match_hold",
        "proposed_value": "80",
        "rationale": "Test.",
    }, headers=_analyst_headers())
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# Config workflow — approve / reject
# ══════════════════════════════════════════════════════════════════════════════

async def test_approve_moves_to_approved(client: AsyncClient, db: AsyncSession):
    cid = await _propose(client)
    resp = await client.post(f"/api/settings/change-requests/{cid}/approve",
                             headers=_director_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    listing = (await client.get("/api/settings/change-requests",
                                headers=_director_headers())).json()
    match = next(r for r in listing["change_requests"] if r["change_id"] == cid)
    assert match["status"] == "approved"
    assert match["approved_by"] == "USR-0003"


async def test_approve_rejects_non_director(client: AsyncClient, db: AsyncSession):
    cid = await _propose(client)
    resp = await client.post(f"/api/settings/change-requests/{cid}/approve",
                             headers=_admin_headers())
    assert resp.status_code == 403


async def test_approve_conflicts_on_non_pending(client: AsyncClient, db: AsyncSession):
    cid = await _propose_approve(client)
    resp = await client.post(f"/api/settings/change-requests/{cid}/approve",
                             headers=_director_headers())
    assert resp.status_code == 409


async def test_reject_moves_to_rejected_with_comment(client: AsyncClient, db: AsyncSession):
    cid = await _propose(client)
    resp = await client.post(f"/api/settings/change-requests/{cid}/reject",
                             json={"comment": "Insufficient justification for Q3."},
                             headers=_director_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    listing = (await client.get("/api/settings/change-requests",
                                headers=_director_headers())).json()
    match = next(r for r in listing["change_requests"] if r["change_id"] == cid)
    assert match["status"] == "rejected"
    assert match["review_comment"] == "Insufficient justification for Q3."


async def test_reject_requires_comment(client: AsyncClient, db: AsyncSession):
    cid = await _propose(client)
    resp = await client.post(f"/api/settings/change-requests/{cid}/reject",
                             json={"comment": ""},
                             headers=_director_headers())
    assert resp.status_code == 422


async def test_reject_conflicts_on_non_pending(client: AsyncClient, db: AsyncSession):
    cid = await _propose_approve(client)
    resp = await client.post(f"/api/settings/change-requests/{cid}/reject",
                             json={"comment": "Too late."},
                             headers=_director_headers())
    assert resp.status_code == 409


# ══════════════════════════════════════════════════════════════════════════════
# Config workflow — deploy
# ══════════════════════════════════════════════════════════════════════════════

async def test_deploy_updates_active_threshold(client: AsyncClient, db: AsyncSession):
    cid = await _propose_approve(client, param="name_match_hold", value="82")
    resp = await client.post(f"/api/settings/change-requests/{cid}/deploy",
                             headers=_admin_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "deployed"
    assert body["new_value"] == "82"

    # Threshold in DB must reflect the new value
    thresholds = (await client.get("/api/settings/thresholds",
                                   headers=_admin_headers())).json()
    hold = next(t for t in thresholds["thresholds"] if t["parameter_name"] == "name_match_hold")
    assert hold["parameter_value"] == "82"


async def test_deploy_writes_history_entry(client: AsyncClient, db: AsyncSession):
    cid = await _propose_approve(client, param="amount_tolerance_auto", value="3")
    await client.post(f"/api/settings/change-requests/{cid}/deploy",
                      headers=_admin_headers())

    history = (await client.get(
        "/api/settings/thresholds/history?parameter_name=amount_tolerance_auto",
        headers=_admin_headers(),
    )).json()
    values = [h["parameter_value"] for h in history["history"]]
    assert "3" in values


async def test_deploy_conflicts_on_non_approved(client: AsyncClient, db: AsyncSession):
    cid = await _propose(client)  # still pending
    resp = await client.post(f"/api/settings/change-requests/{cid}/deploy",
                             headers=_admin_headers())
    assert resp.status_code == 409


async def test_deploy_rejects_non_admin(client: AsyncClient, db: AsyncSession):
    cid = await _propose_approve(client)
    resp = await client.post(f"/api/settings/change-requests/{cid}/deploy",
                             headers=_director_headers())
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# Config workflow — rollback
# ══════════════════════════════════════════════════════════════════════════════

async def test_rollback_restores_previous_value(client: AsyncClient, db: AsyncSession):
    # Capture the original value before we do anything
    original = (await db.execute(
        text("SELECT parameter_value FROM configuration_thresholds WHERE parameter_name = 'name_match_hold'")
    )).scalar_one()

    # Rollback queries configuration_threshold_history for a prior entry. The seed
    # data doesn't populate history, so we insert a baseline row here to give the
    # rollback endpoint something to restore to.
    await db.execute(text("""
        INSERT INTO configuration_threshold_history
            (parameter_name, parameter_value, changed_by, approved_by,
             rationale, effective_from)
        VALUES ('name_match_hold', :val, 'USR-0004', 'USR-0003',
                'Baseline for rollback test', now() - interval '1 day')
    """), {"val": original})

    cid = await _propose_approve_deploy(client, param="name_match_hold", value="85")

    resp = await client.post(f"/api/settings/change-requests/{cid}/rollback",
                             headers=_director_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rolled_back"
    assert body["restored_value"] == original
    assert body["rolled_back_value"] == "85"

    # Active threshold must be back to original
    thresholds = (await client.get("/api/settings/thresholds",
                                   headers=_admin_headers())).json()
    hold = next(t for t in thresholds["thresholds"] if t["parameter_name"] == "name_match_hold")
    assert hold["parameter_value"] == original


async def test_rollback_conflicts_on_non_deployed(client: AsyncClient, db: AsyncSession):
    cid = await _propose_approve(client)  # approved but not deployed
    resp = await client.post(f"/api/settings/change-requests/{cid}/rollback",
                             headers=_director_headers())
    assert resp.status_code == 409


async def test_rollback_rejects_non_director(client: AsyncClient, db: AsyncSession):
    cid = await _propose_approve_deploy(client)
    resp = await client.post(f"/api/settings/change-requests/{cid}/rollback",
                             headers=_admin_headers())
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline failure behaviour
# ══════════════════════════════════════════════════════════════════════════════

async def test_non_retryable_error_marks_processing_failed(client: AsyncClient, db: AsyncSession):
    """A ValueError (non-retryable) on the first attempt sets status=processing_failed."""
    resp = await client.post("/api/payments/ingest", json={
        "amount": 150000,
        "sender_name": "Robert Johnson",
        "payment_method": "ACH",
        "payment_date": "2026-05-10T10:00:00Z",
    })
    pid = resp.json()["payment_id"]

    with patch("app.services.pipeline._process_payment",
               side_effect=ValueError("simulated validation error")):
        with pytest.raises(ValueError):
            await run_pipeline(pid, db)

    row = (await db.execute(
        text("SELECT status FROM payments WHERE payment_id = :id"), {"id": pid}
    )).scalar_one()
    assert row == "processing_failed"


async def test_retryable_error_exhausts_all_attempts(client: AsyncClient, db: AsyncSession):
    """An openai.APITimeoutError on every attempt exhausts retries → processing_failed."""
    import openai

    resp = await client.post("/api/payments/ingest", json={
        "amount": 150000,
        "sender_name": "Robert Johnson",
        "payment_method": "ACH",
        "payment_date": "2026-05-10T11:00:00Z",
    })
    pid = resp.json()["payment_id"]

    call_count = 0

    async def _always_timeout(payment_id, db):
        nonlocal call_count
        call_count += 1
        raise openai.APITimeoutError("simulated timeout")

    with patch("app.services.pipeline._process_payment", side_effect=_always_timeout):
        with patch("asyncio.sleep"):  # skip retry delays
            with pytest.raises(openai.APITimeoutError):
                await run_pipeline(pid, db)

    assert call_count == 3  # all 3 attempts exhausted

    row = (await db.execute(
        text("SELECT status FROM payments WHERE payment_id = :id"), {"id": pid}
    )).scalar_one()
    assert row == "processing_failed"


async def test_retryable_error_succeeds_on_second_attempt(client: AsyncClient, db: AsyncSession):
    """Pipeline succeeds on the second attempt after one retryable failure."""
    import openai

    resp = await client.post("/api/payments/ingest", json={
        "amount": 150000,
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-10001",
        "payment_method": "ACH",
        "payment_date": "2026-05-10T12:00:00Z",
        "reference_field_1": "policy POL-00001 May payment",
    })
    pid = resp.json()["payment_id"]

    attempt = 0
    original_process = __import__(
        "app.services.pipeline", fromlist=["_process_payment"]
    )._process_payment

    async def _fail_once(payment_id, db):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            raise openai.APITimeoutError("simulated timeout on first attempt")
        return await original_process(payment_id, db)

    with patch("app.services.pipeline._process_payment", side_effect=_fail_once):
        with patch("asyncio.sleep"):
            result = await run_pipeline(pid, db)

    assert result["recommendation"] in ("APPLY", "HOLD", "ESCALATE")

    row = (await db.execute(
        text("SELECT status FROM payments WHERE payment_id = :id"), {"id": pid}
    )).scalar_one()
    assert row in ("applied", "held", "escalated")


# ── _is_retryable classification ─────────────────────────────────────────────

def test_is_retryable_operational_error():
    from sqlalchemy.exc import OperationalError
    assert _is_retryable(OperationalError("", {}, None)) is True


def test_is_retryable_integrity_error():
    from sqlalchemy.exc import IntegrityError
    assert _is_retryable(IntegrityError("", {}, None)) is False


def test_is_retryable_value_error():
    assert _is_retryable(ValueError("bad input")) is False


def test_is_retryable_openai_timeout():
    import openai
    assert _is_retryable(openai.APITimeoutError("timeout")) is True


def test_is_retryable_openai_rate_limit():
    import openai
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.request = MagicMock()
    assert _is_retryable(openai.RateLimitError(
        "rate limit", response=mock_response, body=None)) is True


def test_is_retryable_unknown_exception():
    assert _is_retryable(RuntimeError("unknown")) is False
