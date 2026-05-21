"""
CES-40: E2E scenario tests

Each test:
  1. Ingests a crafted payment via POST /api/payments/ingest
  2. Runs run_pipeline() directly against the test DB transaction
  3. Asserts GET /api/payments/{id} returns the expected scenario_route,
     recommendation, status, and key signals

By default both LLM callsites are mocked (fast, no API cost). Pass --live-llm
to run with real OpenRouter calls and catch response-format regressions.

Seed data used (from scripts/seed.py):
  CUST-0001  Robert Johnson   ACC-10001  active      no risk flags
  CUST-0002  Maria Rodriguez  ACC-10002  active      no risk flags
  CUST-0003  James Wilson     ACC-10003  active      fraud_history flag
  CUST-0004  Sarah Lee        ACC-10004  inactive    no risk flags
  CUST-0005  David Chen       ACC-10005  active      chronic_late_payments

  POL-00001  CUST-0001  Auto    $1,500/mo   active   balance=0
  POL-00002  CUST-0001  Home     $950/mo   active   balance=0
  POL-00003  CUST-0002  Home   $1,200/mo   active   balance=0
  POL-00004  CUST-0003  Life   $2,000/mo   active   balance=0
  POL-00005  CUST-0004  Health   $800/mo   inactive balance=0
  POL-00006  CUST-0005  Auto   $4,500/qtr  active   balance=45000
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline import run_pipeline


# ── Scenario 1: Strong Policy Match — auto-apply path ────────────────────────

async def test_sc1_auto_apply(client: AsyncClient, db: AsyncSession):
    """
    Robert Johnson, exact name, ACH, POL-00001 reference, correct amount.
    Expect: scenario 1, APPLY, status=applied, requires_human_approval=False.
    """
    payload = {
        "amount": 150000,
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-10001",
        "payment_method": "ACH",
        "payment_date": "2026-05-10T10:00:00Z",
        "reference_field_1": "policy POL-00001 May payment",
    }
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 201
    payment_id = resp.json()["payment_id"]

    await run_pipeline(payment_id, db)

    detail = await client.get(f"/api/payments/{payment_id}")
    assert detail.status_code == 200
    body = detail.json()

    pmt = body["payment"]
    rec = body["recommendation"]

    assert pmt["status"] == "applied"
    assert rec["recommendation"] == "apply"
    assert rec["scenario_route"] == "scenario_1"
    assert rec["requires_human_approval"] is False
    assert rec["decision_path"] == "scenario_1_auto_apply"
    assert pmt["matched_policy_id"] == "POL-00001"
    assert pmt["matched_customer_id"] == "CUST-0001"


# ── Scenario 1: Strong Policy Match — hold path (risk flags) ─────────────────

async def test_sc1_hold_risk_flags(client: AsyncClient, db: AsyncSession):
    """
    James Wilson has fraud_history risk flag. Even with a perfect name match
    and correct amount, Scenario 1 should route to HOLD.
    """
    payload = {
        "amount": 200000,
        "sender_name": "James Wilson",
        "sender_account": "ACC-10003",
        "payment_method": "Check",
        "payment_date": "2026-05-10T10:00:00Z",
        "reference_field_1": "policy POL-00004 May payment",
    }
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 201
    payment_id = resp.json()["payment_id"]

    await run_pipeline(payment_id, db)

    detail = await client.get(f"/api/payments/{payment_id}")
    body = detail.json()

    pmt = body["payment"]
    rec = body["recommendation"]

    assert pmt["status"] == "held"
    assert rec["recommendation"] == "hold"
    assert rec["scenario_route"] == "scenario_1"
    assert rec["requires_human_approval"] is True
    assert "risk" in rec["decision_path"]


# ── Scenario 2: Customer Match, No Policy Reference ───────────────────────────

async def test_sc2_hold_ambiguous_policies(client: AsyncClient, db: AsyncSession):
    """
    Robert Johnson has two active policies (POL-00001 Auto, POL-00002 Home).
    No policy reference → Scenario 2. Amount of $150k matches POL-00001 but
    the router must land on Sc2 because no reference was parsed. With two
    active policies and ambiguous amount, expect HOLD.
    """
    payload = {
        "amount": 150000,
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-10001",
        "payment_method": "ACH",
        "payment_date": "2026-05-10T11:00:00Z",
        # No reference_field_1 → no extracted_policy_number
    }
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 201
    payment_id = resp.json()["payment_id"]

    await run_pipeline(payment_id, db)

    detail = await client.get(f"/api/payments/{payment_id}")
    body = detail.json()

    pmt = body["payment"]
    rec = body["recommendation"]

    assert pmt["status"] == "held"
    assert rec["scenario_route"] == "scenario_2"
    assert rec["requires_human_approval"] is True
    assert pmt["matched_customer_id"] == "CUST-0001"


async def test_sc2_apply_single_policy_strong_match(client: AsyncClient, db: AsyncSession):
    """
    Maria Rodriguez has exactly one active policy (POL-00003, $1,200/mo).
    Strong name match (≥90%) + no policy reference → Scenario 2 → APPLY
    (requires approval, since Sc2 always needs human sign-off).
    """
    payload = {
        "amount": 120000,
        "sender_name": "Maria Rodriguez",
        "sender_account": "ACC-10002",
        "payment_method": "Credit Card",
        "payment_date": "2026-05-10T12:00:00Z",
    }
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 201
    payment_id = resp.json()["payment_id"]

    await run_pipeline(payment_id, db)

    detail = await client.get(f"/api/payments/{payment_id}")
    body = detail.json()

    rec = body["recommendation"]
    pmt = body["payment"]

    assert rec["scenario_route"] == "scenario_2"
    assert rec["recommendation"] == "apply"
    assert rec["requires_human_approval"] is True
    assert pmt["matched_customer_id"] == "CUST-0002"
    # Status stays held because requires_human_approval=True at persist time
    assert pmt["status"] == "held"


# ── Scenario 3: High Amount Variance ─────────────────────────────────────────

async def test_sc3_hold_moderate_variance(client: AsyncClient, db: AsyncSession):
    """
    Robert Johnson, POL-00001 ($1,500/mo), pays $1,800 — 20% variance.
    Variance 15–50% → HOLD (standard Sc3 hold path).
    """
    payload = {
        "amount": 180000,  # $1,800 vs $1,500 = 20% variance
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-10001",
        "payment_method": "ACH",
        "payment_date": "2026-05-10T13:00:00Z",
        "reference_field_1": "policy POL-00001 May payment",
    }
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 201
    payment_id = resp.json()["payment_id"]

    await run_pipeline(payment_id, db)

    detail = await client.get(f"/api/payments/{payment_id}")
    body = detail.json()

    pmt = body["payment"]
    rec = body["recommendation"]

    assert pmt["status"] == "held"
    assert rec["scenario_route"] == "scenario_3"
    assert rec["recommendation"] == "hold"
    assert rec["requires_human_approval"] is True


async def test_sc3_escalate_extreme_variance(client: AsyncClient, db: AsyncSession):
    """
    Robert Johnson, POL-00001 ($1,500/mo), pays $4,500 — 200% variance.
    Variance >100% → ESCALATE.
    """
    payload = {
        "amount": 450000,  # $4,500 vs $1,500 = 200% variance
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-10001",
        "payment_method": "ACH",
        "payment_date": "2026-05-10T14:00:00Z",
        "reference_field_1": "policy POL-00001",
    }
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 201
    payment_id = resp.json()["payment_id"]

    await run_pipeline(payment_id, db)

    detail = await client.get(f"/api/payments/{payment_id}")
    body = detail.json()

    rec = body["recommendation"]
    pmt = body["payment"]

    assert rec["scenario_route"] == "scenario_3"
    assert rec["recommendation"] == "escalate"
    assert pmt["status"] == "escalated"


# ── Scenario 4: No Matching Customer ─────────────────────────────────────────

async def test_sc4_escalate_no_match(client: AsyncClient, db: AsyncSession):
    """
    Completely unknown sender — below the 75% name similarity floor for all
    seed customers. No policy reference. Should route to Scenario 4 → ESCALATE.
    """
    payload = {
        "amount": 99999,
        "sender_name": "Zxqvf Bljrpm 99999",  # nonsense name, no fuzzy match
        "payment_method": "Wire",
        "payment_date": "2026-05-10T15:00:00Z",
    }
    resp = await client.post("/api/payments/ingest", json=payload)
    assert resp.status_code == 201
    payment_id = resp.json()["payment_id"]

    await run_pipeline(payment_id, db)

    detail = await client.get(f"/api/payments/{payment_id}")
    body = detail.json()

    rec = body["recommendation"]
    pmt = body["payment"]

    assert rec["scenario_route"] == "scenario_4"
    assert rec["recommendation"] == "escalate"
    assert pmt["status"] == "escalated"
    assert rec["decision_path"] == "scenario_4_escalate_no_match"


# ── Scenario 5: Duplicate Payment Detection ───────────────────────────────────

async def test_sc5_escalate_true_duplicate(client: AsyncClient, db: AsyncSession):
    """
    Submit the same payment twice within the 72h window with zero outstanding balance.
    POL-00001 has balance=0 → duplicate should ESCALATE.

    Both ingests share the same DB transaction so the first payment is visible
    to the duplicate detector when the second one runs.
    """
    base_payload = {
        "amount": 150000,
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-10001",
        "payment_method": "ACH",
        "payment_date": "2026-05-10T10:00:00Z",
        "reference_field_1": "policy POL-00001 May payment",
    }

    # First payment — process it fully
    resp1 = await client.post("/api/payments/ingest", json=base_payload)
    assert resp1.status_code == 201
    first_id = resp1.json()["payment_id"]

    await run_pipeline(first_id, db)

    # Second payment — same fields, slightly different timestamp (still within 72h)
    dup_payload = {**base_payload, "payment_date": "2026-05-10T11:00:00Z"}
    resp2 = await client.post("/api/payments/ingest", json=dup_payload)
    assert resp2.status_code == 201
    dup_id = resp2.json()["payment_id"]

    await run_pipeline(dup_id, db)

    detail = await client.get(f"/api/payments/{dup_id}")
    body = detail.json()

    rec = body["recommendation"]
    pmt = body["payment"]

    assert rec["scenario_route"] == "scenario_5"
    assert rec["recommendation"] == "escalate"
    assert pmt["status"] == "escalated"
    assert rec["decision_path"] == "scenario_5_escalate_true_duplicate"


async def test_sc5_hold_balance_justifies(client: AsyncClient, db: AsyncSession):
    """
    David Chen has POL-00006 with $450 outstanding balance.
    Submit the same payment twice — the balance justifies the second payment
    so Scenario 5 should route to HOLD rather than ESCALATE.
    """
    base_payload = {
        "amount": 450000,
        "sender_name": "David Chen",
        "sender_account": "ACC-10005",
        "payment_method": "ACH",
        "payment_date": "2026-05-15T09:00:00Z",
        "reference_field_1": "policy POL-00006 Q2 payment",
    }

    resp1 = await client.post("/api/payments/ingest", json=base_payload)
    assert resp1.status_code == 201
    first_id = resp1.json()["payment_id"]

    await run_pipeline(first_id, db)

    dup_payload = {**base_payload, "payment_date": "2026-05-15T10:30:00Z"}
    resp2 = await client.post("/api/payments/ingest", json=dup_payload)
    assert resp2.status_code == 201
    dup_id = resp2.json()["payment_id"]

    await run_pipeline(dup_id, db)

    detail = await client.get(f"/api/payments/{dup_id}")
    body = detail.json()

    rec = body["recommendation"]
    pmt = body["payment"]

    assert rec["scenario_route"] == "scenario_5"
    assert rec["recommendation"] == "hold"
    assert pmt["status"] == "held"
    assert rec["decision_path"] == "scenario_5_hold_balance_justifies"
