# Data Flow & Pipeline Orchestration

**Purpose:** Shows the complete end-to-end journey of a payment through the system, the pipeline orchestrator, and payment lifecycle states.

---

## End-to-End Sequence

```
Payment arrives (POST /api/payments/ingest)
    │
    │  ── STAGE 1: INGEST ──
    │
    ├── 1.  Validate required fields (amount, sender, method, date)
    ├── 2.  Claude API: parse free-text references → extract policy #, intent, period count
    ├── 3.  Generate payment ID (PMT-XXX)
    ├── 4.  INSERT into payments (status = RECEIVED)
    ├── 5.  Audit log: RECEIVED
    │
    │  ── STAGE 2: COMPUTE SIGNALS ──
    │
    ├── 6.  Wave 1 (parallel): name similarity, amount variance, timing, duplicate check
    ├── 7.  Wave 2: policy confidence, customer confidence, over/underpay, historical consistency
    ├── 8.  Wave 3: risk flags, balance, supporting signals, multi-period, time between payments
    ├── 9.  INSERT into payment_signals (snapshot)
    ├── 10. Audit log: SIGNALS_COMPUTED
    │
    │  ── STAGE 3: AI AGENT ──
    │
    ├── 11. Scenario 5 check (duplicate detection — runs first on every payment)
    ├── 12. Route to Scenario 1, 2, 3, or 4 (deterministic decision tree)
    ├── 13. Claude API: reason within selected scenario → structured recommendation
    │
    │  ── STAGE 4: PERSIST ──
    │
    ├── 14. INSERT into payment_recommendations
    ├── 15. UPDATE payments (status, matched_customer_id, matched_policy_id)
    ├── 16. Audit log: RECOMMENDATION_MADE
    │
    │  ── STAGE 5: RESOLUTION ──
    │
    ├── 17a. If requires_human_approval = false:
    │         ├── INSERT into payment_history (ledger updated)
    │         ├── UPDATE policy outstanding_balance
    │         └── Audit log: APPLIED (actor: system)
    │
    ├── 17b. If requires_human_approval = true:
    │         └── Payment appears in approval queue
    │              │
    │              ├── Analyst APPROVES:
    │              │     ├── Status: HELD → APPLIED
    │              │     ├── INSERT into payment_history
    │              │     ├── UPDATE policy outstanding_balance
    │              │     └── Audit log: APPROVED + APPLIED (actor: analyst ID)
    │              │
    │              └── Analyst REJECTS:
    │                    ├── Status: HELD → ESCALATED
    │                    └── Audit log: ESCALATED (actor: analyst ID, notes)
    │
    └── 17c. If processing fails after 3 retries:
              ├── Status: RECEIVED → PROCESSING_FAILED
              ├── Audit log: PROCESSING_FAILED (error details)
              └── Analyst can trigger reprocess via POST /api/payments/{id}/reprocess
```

---

## Payment Lifecycle (State Diagram)

```
                    ┌──────────┐
    Ingest ────────>│ RECEIVED │
                    └────┬─────┘
                         │
                    Processing pipeline
                    (signals → route → reason → persist)
                         │
              ┌──────────┼──────────────┬─────────────────┐
              │          │              │                 │
              ▼          ▼              ▼                 ▼
        ┌──────────┐ ┌──────┐  ┌───────────┐  ┌──────────────────┐
        │ APPLIED  │ │ HELD │  │ ESCALATED │  │PROCESSING_FAILED │
        │ (final)  │ │      │  │  (final)  │  │                  │
        └──────────┘ └──┬───┘  └───────────┘  └────────┬─────────┘
                        │                               │
                   Human action                    Reprocess
                        │                               │
              ┌─────────┴────────┐                      │
              │                  │                      │
              ▼                  ▼                      ▼
        ┌──────────┐     ┌───────────┐          Back to RECEIVED
        │ APPLIED  │     │ ESCALATED │          (re-enters pipeline)
        │ (final)  │     │  (final)  │
        └──────────┘     └───────────┘
```

### Status Definitions

| Status | Meaning | How It Gets Here |
|--------|---------|-----------------|
| RECEIVED | Payment ingested, awaiting processing | Initial state after ingest |
| APPLIED | Payment allocated to a policy | Auto-apply or analyst approval |
| HELD | Waiting for analyst review | AI recommends with requires_human_approval = true |
| ESCALATED | Sent to investigation queue | AI escalates or analyst rejects |
| PROCESSING_FAILED | Pipeline failed after retries | Transient error during processing |

---

## Pipeline Orchestrator

The `pipeline.py` module ties all stages together:

```
pipeline.process_payment(payment_id):
    │
    ├── signals = signal_engine.compute_all(payment_id)
    │     ├── Wave 1 (parallel)
    │     ├── Wave 2
    │     └── Wave 3
    │
    ├── scenario = agent.router.route(payment_id, signals)
    │
    ├── recommendation = agent.reasoning.reason(payment_id, scenario, signals)
    │
    └── persist.save(payment_id, signals, recommendation)
```

The pipeline is called from the ingest endpoint after the payment is saved. It runs with the retry wrapper described in [04_Persist_Layer.md](./04_Persist_Layer.md).

---

## Audit Trail

Every payment accumulates an ordered audit trail. Example for a payment that goes through human approval:

| # | Timestamp | Action | Actor | Details |
|---|-----------|--------|-------|---------|
| 1 | 09:01:23 | RECEIVED | system | Payment ingested |
| 2 | 09:01:24 | SIGNALS_COMPUTED | system | 15 signals computed and snapshotted |
| 3 | 09:01:25 | RECOMMENDATION_MADE | system | APPLY, 85% confidence, Scenario 2 |
| 4 | 10:15:00 | APPROVED | analyst-jane-doe | "Confirmed with customer records" |
| 5 | 10:15:00 | APPLIED | analyst-jane-doe | Ledger updated, balance adjusted |

The audit trail is append-only. Entries are never modified or deleted.

---

## Database Tables Touched Per Stage

| Stage | Reads From | Writes To |
|-------|-----------|----------|
| 1. Ingest | — | payments, audit_log |
| 2. Signals | customers, policies, payment_history, risk_flags, payments, configuration_thresholds | payment_signals, audit_log |
| 3. AI Agent | payment_signals, configuration_thresholds | — (output held in memory) |
| 4. Persist | — | payment_recommendations, payments, audit_log |
| 5. Approval | payments, payment_recommendations | payments, payment_history, policies, audit_log |

---

*End of Document*
