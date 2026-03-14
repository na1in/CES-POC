# Stage 1: Ingest Layer (Event Monitoring)

**Purpose:** Receive raw payments, validate fields, parse free-text references using Claude API, and persist to DB with status `RECEIVED`.

---

## Overview

This is the front door of the system. Payments arrive via a REST endpoint and may contain incomplete or messy data — especially in the free-text reference fields where humans type whatever they want.

The Ingest layer does three things:
1. Validate required fields
2. Use Claude API to parse free-text references
3. Save the payment to the database

---

## Endpoint

`POST /api/payments/ingest`

---

## Input Example

```json
{
  "amount": 500000,
  "sender_name": "John A Smith",
  "sender_account": "ACC-9876",
  "beneficiary_name": "John Smith",
  "payment_method": "ACH",
  "payment_date": "2026-03-12T09:00:00Z",
  "reference_1": "For policy POL-12345 Jan premium",
  "reference_2": "Auto insurance payment"
}
```

- Amount is in **cents** (500000 = $5,000.00)
- Reference fields are free text — this is where the AI helps

---

## Step 1: Field Validation

Check that required fields are present and valid:

| Field | Required | Validation |
|-------|----------|-----------|
| amount | Yes | Must be positive integer (cents) |
| sender_name | Yes | Non-empty string |
| payment_method | Yes | Must be valid enum (ACH, CHECK, WIRE, EFT) |
| payment_date | Yes | Valid timestamp |
| sender_account | No | — |
| beneficiary_name | No | — |
| reference_1 | No | Free text |
| reference_2 | No | Free text |

If validation fails, return 400 with error details. The payment is not saved.

---

## Step 2: Claude API — Parse Free-Text References

Reference fields can contain anything:
- `"For policy POL-12345 Jan premium"`
- `"Payment for my car insurance jan to march"`
- `"Invoice #12345"`
- `"Premium payment - John Smith"`

Claude API extracts structured data from this free text:

**Input to Claude:**
```
Parse the following payment reference fields and extract:
- Policy number (if present)
- Payment intent (premium, deposit, catch-up, etc.)
- Period count (how many months/periods this covers)

Reference 1: "For policy POL-12345 Jan premium"
Reference 2: "Auto insurance payment"
```

**Claude returns:**
```json
{
  "extracted_policy_number": "POL-12345",
  "payment_intent": "premium_payment",
  "period_count": 1,
  "policy_type_hint": "auto"
}
```

This extracted data is **not stored in the Payment proto** — the raw reference text is preserved as-is for auditability. The extracted data feeds into the next stage (Compute Signals) where it's used for policy lookup and matching.

---

## Step 3: Persist to Database

The validated payment is saved to the `payments` table, filling the Payment proto:

```
payment_id:         "PMT-001"          (generated, prefixed format)
amount_cents:       500000             (from input)
sender_name:        "John A Smith"     (from input)
sender_account:     "ACC-9876"         (from input)
beneficiary_name:   "John Smith"       (from input)
payment_method:     ACH                (from input)
payment_date:       2026-03-12T09:00Z  (from input)
reference_1:        "For policy..."    (raw, preserved)
reference_2:        "Auto insurance.." (raw, preserved)
status:             RECEIVED           (initial status)
matched_customer_id: (empty)           (filled later by Compute Signals)
matched_policy_id:   (empty)           (filled later by Compute Signals)
ingested_at:        2026-03-12T09:01Z  (system timestamp)
```

An audit log entry is written: `RECEIVED` with `actor: "system"`.

---

## What Happens Next

The payment is now safely in the database. The processing pipeline (Stages 2-4) kicks off immediately. If processing fails, the payment is not lost — it remains in `RECEIVED` status and can be reprocessed.

See: [02_Compute_Signals.md](./02_Compute_Signals.md)

---

## Backend Modules

| File | Responsibility |
|------|---------------|
| `backend/app/routers/payments.py` | REST endpoint, request parsing |
| `backend/app/services/ingest.py` | Field validation, Claude API text parsing, DB persist |

---

*End of Document*
