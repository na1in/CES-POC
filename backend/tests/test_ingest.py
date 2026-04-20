import pytest
from httpx import AsyncClient

VALID_PAYLOAD = {
    "amount": 150000,
    "sender_name": "Robert Johnson",
    "sender_account": "ACC-10001",
    "payment_method": "ACH",
    "payment_date": "2026-04-18T10:00:00Z",
    "reference_field_1": "for policy POL-00001 April payment",
}


# ── Happy path ────────────────────────────────────────────────────────────────

async def test_ingest_success(client: AsyncClient):
    resp = await client.post("/api/payments/ingest", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "received"
    assert body["payment_id"].startswith("PMT-")
    assert "created_timestamp" in body


async def test_ingest_payment_id_format(client: AsyncClient):
    resp = await client.post("/api/payments/ingest", json=VALID_PAYLOAD)
    payment_id = resp.json()["payment_id"]
    prefix, num = payment_id.split("-")
    assert prefix == "PMT"
    assert num.isdigit()
    assert len(num) >= 3


async def test_ingest_optional_fields_omitted(client: AsyncClient):
    payload = {
        "amount": 50000,
        "sender_name": "Jane Smith",
        "payment_method": "Check",
        "payment_date": "2026-04-18T10:00:00Z",
    }
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 201


async def test_ingest_all_valid_payment_methods(client: AsyncClient):
    for method in ["ACH", "Check", "Credit Card", "Wire"]:
        payload = {**VALID_PAYLOAD, "payment_method": method}
        resp = await client.post("/api/payments/ingest", json=payload)
        assert resp.status_code == 201, f"Expected 201 for method={method}, got {resp.status_code}"


# ── Amount validation ─────────────────────────────────────────────────────────

async def test_ingest_rejects_float_amount(client: AsyncClient):
    resp = await client.post("/api/payments/ingest", json={**VALID_PAYLOAD, "amount": 150.53})
    assert resp.status_code == 422


async def test_ingest_rejects_whole_number_float(client: AsyncClient):
    """150.00 looks like an integer but signals the caller is using the wrong format."""
    resp = await client.post("/api/payments/ingest", json={**VALID_PAYLOAD, "amount": 150.00})
    assert resp.status_code == 422


async def test_ingest_rejects_zero_amount(client: AsyncClient):
    resp = await client.post("/api/payments/ingest", json={**VALID_PAYLOAD, "amount": 0})
    assert resp.status_code == 422


async def test_ingest_rejects_negative_amount(client: AsyncClient):
    resp = await client.post("/api/payments/ingest", json={**VALID_PAYLOAD, "amount": -5000})
    assert resp.status_code == 422


# ── Payment method validation ─────────────────────────────────────────────────

async def test_ingest_rejects_invalid_payment_method(client: AsyncClient):
    resp = await client.post("/api/payments/ingest", json={**VALID_PAYLOAD, "payment_method": "Cash"})
    assert resp.status_code == 422


async def test_ingest_rejects_lowercase_payment_method(client: AsyncClient):
    resp = await client.post("/api/payments/ingest", json={**VALID_PAYLOAD, "payment_method": "ach"})
    assert resp.status_code == 422


# ── Missing required fields ───────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["amount", "sender_name", "payment_method", "payment_date"])
async def test_ingest_rejects_missing_required_field(client: AsyncClient, field: str):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != field}
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 422


# ── Claude parse failure is non-fatal ────────────────────────────────────────

async def test_ingest_succeeds_without_api_key(client: AsyncClient):
    """Claude parse failing (no API key) must not fail the ingest."""
    resp = await client.post("/api/payments/ingest", json=VALID_PAYLOAD)
    assert resp.status_code == 201


async def test_ingest_succeeds_with_no_reference_fields(client: AsyncClient):
    payload = {**VALID_PAYLOAD, "reference_field_1": None, "reference_field_2": None}
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 201
