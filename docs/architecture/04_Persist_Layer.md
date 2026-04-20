# Stage 4: Persist Layer (Action Execution)

**Purpose:** Save the AI recommendation, update payment status, handle ledger updates, and write audit trail — all in a single database transaction.

---

## Overview

This is the simplest stage but one of the most important. After the AI produces a recommendation, we need to commit everything to the database atomically. Either all writes succeed, or none do.

---

## What Gets Saved (Single Transaction)

```python
async with db.begin():  # single transaction — all or nothing
    1. save_recommendation(...)
    2. update_payment_status(...)
    3. fill_matched_ids(...)
    4. if auto_apply: update_ledger(...)
    5. write_audit_log(...)
# all committed together, or all rolled back on failure
```

### Step 1: Save Recommendation

The AI output is written to the `payment_recommendations` table:

```
payment_id:              "PMT-001"
recommendation:          APPLY
confidence_score:        95
scenario_route:          STRONG_POLICY_MATCH
decision_path:           "scenario_1_auto_apply"
requires_human_approval: false
approval_reason:         (empty — no approval needed)
reasoning:               ["Policy POL-12345 confirmed active...", ...]
suggested_action:        "Apply to POL-12345"
processing_time_ms:      1243
created_at:              2026-03-12T09:01:25Z
```

### Step 2: Update Payment Status

The `payments` table status is updated:

```
RECEIVED  ──→  APPLIED      (auto-apply, no human needed)
          ──→  HELD         (waiting for analyst approval)
          ──→  ESCALATED    (sent to investigation queue)
```

For ESCALATED payments, `investigation_due_date` is also set at this point — this is the SLA deadline for Damien to resolve the case. The `sla_breached` field is updated by `sla.py` on a background schedule if the deadline passes without resolution.

### Step 3: Fill Matched IDs

The `matched_customer_id` and `matched_policy_id` fields on the payment record — which were left empty during Ingest — are now filled:

```
matched_customer_id:  "CUST-0001"   (was empty)
matched_policy_id:    "POL-12345"   (was empty)
```

For Scenario 4 (no match), these remain empty.

### Step 4: Ledger Update (Auto-Apply Only)

If the recommendation is APPLY with `requires_human_approval = false`:
- INSERT into `payment_history` (the policy's payment ledger)
- UPDATE the policy's `outstanding_balance` (subtract the payment amount)

If the recommendation is HOLD or ESCALATE:
- **Ledger is NOT updated.** Deferred until a human approves (see below).

### Step 5: Set Decision Attribution

The `decision_attribution` field on `payment_recommendations` is set at case **closure**, not at recommendation time:
- `AI_AUTONOMOUS` — payment auto-applied or escalated with no human touching it
- `HUMAN_CONFIRMED` — human agreed with AI recommendation
- `HUMAN_OVERRIDE` — human changed the outcome

At pipeline time, the field is left as `UNSPECIFIED`. It is populated when the case is closed by a human action (approve, reject, override, return).

### Step 6: Audit Log

Write an audit log entry: `RECOMMENDATION_MADE` with full details.

```
log_id:      (auto-generated)
payment_id:  "PMT-001"
action_type: RECOMMENDATION_MADE
actor:       "system"
details:     { recommendation: "APPLY", confidence: 95, scenario: 1, ... }
timestamp:   2026-03-12T09:01:25Z
```

---

## Post-Approval Ledger Update (Human Action)

For payments that were HELD, the ledger update happens later when an analyst takes action:

### Analyst Approves (`POST /api/payments/{id}/approve`)

```
1. UPDATE payments.status:  HELD → APPLIED
2. INSERT into payment_history (ledger now updated)
3. UPDATE policy outstanding_balance (subtract payment amount)
4. Audit log: APPROVED  (actor = "analyst-jane-doe")
5. Audit log: APPLIED
```

### Analyst Rejects (`POST /api/payments/{id}/reject`)

```
1. UPDATE payments.status:  HELD → ESCALATED
2. SET investigation_due_date (SLA deadline for Damien)
3. Ledger remains untouched
4. Audit log: ESCALATED  (actor = analyst user ID, notes included)
```

### Override (`POST /api/payments/{id}/override`)

Either Priya or Damien can override the AI recommendation. A reason is mandatory and stored as an `OVERRIDE_REASON` annotation.

```
1. UPDATE payments.status to new outcome (APPLIED or ESCALATED)
2. If APPLIED: INSERT into payment_history, UPDATE policy outstanding_balance
3. SET decision_attribution = HUMAN_OVERRIDE on payment_recommendations
4. Audit log: OVERRIDDEN (original_recommendation, override_action, reason)
5. Audit log: APPLIED or ESCALATED
```

### Investigator Returns Payment (`POST /api/payments/{id}/return`)

Damien determines a payment must be returned to the sender.

```
1. UPDATE payments.status:  ESCALATED → RETURNED
2. Ledger remains untouched (payment was never applied)
3. Audit log: RETURNED (actor = Damien's user ID, notes)
```

### Investigation SLA — PENDING_SENDER_RESPONSE

Damien can mark a case as awaiting sender response (e.g., after logging outreach):

```
1. UPDATE payments.status:  ESCALATED → PENDING_SENDER_RESPONSE
2. SLA timer starts (tracked via investigation_due_date)
3. Audit log: CONTACT_LOGGED (contact_method, outcome, contacted_party)
```

From PENDING_SENDER_RESPONSE, the case resolves as:
- Sender responds positively → APPLIED (Damien approves)
- Sender confirms duplicate → RETURNED
- SLA breached → `sla_breached = true`, surfaces in Lorraine's Exception Dashboard → ESCALATED

### Actor Tracking

The audit trail always records **who** made the final call:

| Action | Actor | decision_attribution |
|--------|-------|----------------------|
| Auto-apply (no approval needed) | `"system"` | AI_AUTONOMOUS |
| Human approves HELD | analyst user ID | HUMAN_CONFIRMED |
| Human rejects HELD | analyst user ID | HUMAN_CONFIRMED (AI said HOLD, human confirms ESCALATE) |
| Human overrides | analyst/investigator user ID | HUMAN_OVERRIDE |
| Damien returns payment | investigator user ID | HUMAN_CONFIRMED |

---

## Retry & Failure Strategy

Ingest and processing are **separated** so a processing failure never loses the payment.

### Pipeline Structure

```
POST /api/payments/ingest
    │
    ├── Step A: Ingest (validate + save as RECEIVED)
    │     Always runs once. Payment is now safely in the DB.
    │
    └── Step B: process_payment() with retry wrapper
          ├── Compute signals
          ├── Route scenario
          ├── AI reasoning (Claude API)
          └── Persist (single DB transaction)
```

### Retry Behavior for Step B

```
Attempt 1: Run full processing pipeline
    │
    FAILED (transaction rolled back — nothing half-saved)
    │
    Attempt 2 (after 1 second)
    │
    FAILED
    │
    Attempt 3 (after 3 seconds)
    │
    FAILED
    │
    All retries exhausted:
    ├── Mark payment status → PROCESSING_FAILED
    ├── Write audit log: PROCESSING_FAILED (with error details)
    └── Payment appears in "Failed Processing" view in UI
```

### What Gets Retried vs. What Does Not

| Failure Type | Retry? | Reason |
|---|---|---|
| DB connection timeout | Yes | Transient — network blip |
| DB deadlock | Yes | Transient — concurrent writes |
| Claude API timeout | Yes | Transient — API hiccup |
| Claude API rate limit | Yes (with backoff) | Temporary throttle |
| DB constraint violation (e.g. duplicate key) | No | Bug — retrying won't help |
| Data validation error | No | Bad data — needs investigation |
| Unknown/unclassified error | No | Needs manual review |

### Recovery for Failed Payments

Failed payments remain in the DB with status `PROCESSING_FAILED`. They can be reprocessed:

`POST /api/payments/{id}/reprocess`

This re-runs the full processing pipeline (signals → route → reason → persist) from scratch. Since signals are always computed fresh and the original payment data is intact, reprocessing is safe and idempotent.

---

## Backend Modules

| File | Responsibility |
|------|---------------|
| `backend/app/services/persist.py` | Save recommendation, update status, ledger, audit (single transaction) |
| `backend/app/services/pipeline.py` | End-to-end orchestrator with retry logic |
| `backend/app/routers/approvals.py` | Approve/reject/override/return endpoints |
| `backend/app/routers/annotations.py` | Case annotation endpoints |
| `backend/app/routers/documents.py` | Document upload/download/list endpoints |
| `backend/app/services/sla.py` | SLA deadline computation and breach detection |
| `backend/app/services/storage.py` | Document storage abstraction (local FS for PoC, S3-compatible) |

---

## What Happens Next

For auto-applied payments, the process is complete. For HOLD/ESCALATE payments, they appear in the Human Approval Queue (Stage 5) where an analyst reviews and takes action.

See: [05_Human_Approval_Queue.md](./05_Human_Approval_Queue.md)

---

*End of Document*
