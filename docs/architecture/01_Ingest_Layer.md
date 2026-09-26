# Stage 1: Ingest Layer (Event Monitoring)

**Purpose:** Receive raw payments, validate fields, parse free-text references (deterministic regex, no LLM), and persist to DB with status `RECEIVED`.

---

## Overview

This is the front door of the system. Payments arrive via a REST endpoint and may contain incomplete or messy data — especially in the free-text reference fields where humans type whatever they want.

The Ingest layer does three things:
1. Validate required fields
2. Extract the policy number from the free-text references (regex)
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

## Step 2: Parse Free-Text References (deterministic)

Reference fields can contain anything:
- `"For policy POL-12345 Jan premium"`
- `"ins. policy no. 10169"`
- `"pol 90003 - ins."`
- `"Invoice #12345"`

A regex (`parse_reference_fields` in `backend/app/services/ingest.py`) extracts the policy number. It is not an LLM call: the evaluation harness
measured a regex matching or beating the LLM parser on policy-number extraction, with none of its failure modes (un-normalised output such as
`POL90001`, missed plain references, timeouts, run-to-run variation), at no cost and without sending reference text to a third party.

- **Formats accepted:** `POL-12345`, `POL12345`, `pol 12345`, `Pol.12345`, `Policy #12345`, `policy no. 12345`, `policy number: 12345`, `P0L-12345`.
  The number must be exactly 5 digits and the keyword may not run into letters (`policyholder 12345` does not match).
- **Output is always normalised** to `POL-XXXXX`.
- **Ambiguity is left to a person:** if the text names two different policy numbers the payment is left unmatched (no policy number) so the analyst chooses.
- **Fields:** both reference fields are read together. `payment_intent` and `period_count` keep their defaults (`unknown`, `1`): nothing
  downstream reads them (multi-period detection is computed from amounts in `signals/amount.py`).
- **Parsed once:** the ingest endpoint passes its parse to the pipeline, so the same text is never parsed twice. Parsing is a pure function, so the
  reprocess path re-parses to the same result.
- **Spotting gaps:** when the text contains a 5-digit number but no pattern matched, an info line is logged (the text itself is not logged).

This extracted data is **not stored in the Payment proto** — the raw reference text is preserved as-is for auditability. The extracted policy number is
recorded in the `received` audit entry and feeds the next stage (Compute Signals) where it is used for policy lookup and matching.

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
| `backend/app/services/ingest.py` | Deterministic (regex) policy-number extraction from the reference fields |

---

*End of Document*
