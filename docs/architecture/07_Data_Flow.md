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
    ├── 6.  UPDATE payments (status = PROCESSING)
    ├── 7.  Wave 1 (parallel): name similarity, amount variance, timing, duplicate check
    ├── 8.  Wave 2: policy confidence, customer confidence, over/underpay, historical consistency
    ├── 9.  Wave 3: risk flags, balance, supporting signals, multi-period, time between payments
    ├── 10. INSERT into payment_signals (snapshot)
    ├── 11. Audit log: SIGNALS_COMPUTED
    │
    │  ── STAGE 3: AI AGENT ──
    │
    ├── 12. Scenario 5 check (duplicate detection — runs first on every payment)
    ├── 13. Route to Scenario 1, 2, 3, or 4 (deterministic decision tree)
    ├── 14. Claude API: reason within selected scenario → structured recommendation
    │
    │  ── STAGE 4: PERSIST ──
    │
    ├── 15. INSERT into payment_recommendations (decision_attribution = UNSPECIFIED)
    ├── 16. UPDATE payments (status, matched_customer_id, matched_policy_id)
    │         If status = ESCALATED: SET investigation_due_date (SLA deadline for Damien)
    ├── 17. Audit log: RECOMMENDATION_MADE
    │
    │  ── STAGE 5: RESOLUTION ──
    │
    ├── 18a. If requires_human_approval = false AND recommendation = APPLY:
    │         ├── INSERT into payment_history (ledger updated)
    │         ├── UPDATE policy outstanding_balance
    │         ├── SET decision_attribution = AI_AUTONOMOUS
    │         └── Audit log: APPLIED (actor: system)
    │
    ├── 18b. If requires_human_approval = false AND recommendation = ESCALATE:
    │         ├── SET decision_attribution = AI_AUTONOMOUS
    │         ├── Audit log: ESCALATED (actor: system)
    │         └── → Payment routes to Damien's investigation queue (see 18d)
    │
    ├── 18c. If requires_human_approval = true → Payment appears in Priya's approval queue
    │         │
    │         ├── Analyst APPROVES:
    │         │     ├── Status: HELD → APPLIED
    │         │     ├── INSERT into payment_history (ledger updated)
    │         │     ├── UPDATE policy outstanding_balance
    │         │     ├── SET decision_attribution = HUMAN_CONFIRMED
    │         │     └── Audit log: APPROVED + APPLIED (actor: analyst ID)
    │         │
    │         ├── Analyst REJECTS:
    │         │     ├── Status: HELD → ESCALATED
    │         │     ├── SET investigation_due_date (SLA deadline for Damien)
    │         │     ├── Audit log: ESCALATED (actor: analyst ID, notes)
    │         │     └── → Payment routes to Damien's investigation queue (see 18d)
    │         │
    │         └── Analyst OVERRIDES:
    │               ├── Status: HELD → APPLIED or ESCALATED (analyst choice)
    │               ├── SET decision_attribution = HUMAN_OVERRIDE
    │               ├── INSERT case_annotation (OVERRIDE_REASON, mandatory)
    │               └── Audit log: OVERRIDDEN (original rec, override action, reason)
    │
    ├── 18d. Damien's investigation queue (reached from 18b or 18c-reject):
    │         │
    │         ├── Damien logs outreach:
    │         │     ├── Status: ESCALATED → PENDING_SENDER_RESPONSE
    │         │     ├── INSERT case_annotation (CONTACT_RECORD)
    │         │     ├── Audit log: CONTACT_LOGGED
    │         │     └── SLA timer running; breach → sla_breached = true (Lorraine notified)
    │         │
    │         ├── Damien APPLIES (after sender confirmation):
    │         │     ├── Status: PENDING_SENDER_RESPONSE → APPLIED
    │         │     ├── INSERT into payment_history
    │         │     ├── SET decision_attribution = HUMAN_CONFIRMED
    │         │     └── Audit log: APPLIED (actor: Damien's ID)
    │         │
    │         └── Damien RETURNS (payment sent back to sender):
    │               ├── Status: ESCALATED/PENDING_SENDER_RESPONSE → RETURNED
    │               └── Audit log: RETURNED (actor: Damien's ID)
    │
    └── 18e. If processing fails after 3 retries:
              ├── Status: PROCESSING → PROCESSING_FAILED
              ├── Audit log: PROCESSING_FAILED (error details)
              └── Reprocess via POST /api/payments/{id}/reprocess → back to RECEIVED
```

---

## Payment Lifecycle (State Diagram)

```
                    ┌──────────┐
    Ingest ────────>│ RECEIVED │
                    └────┬─────┘
                         │ pipeline starts
                    ┌────▼─────┐
                    │PROCESSING│
                    └────┬─────┘
                         │
              ┌──────────┼──────────┬──────────────────────┐
              │          │          │                      │
              ▼          ▼          ▼                      ▼
        ┌──────────┐ ┌──────┐ ┌───────────┐  ┌──────────────────────┐
        │ APPLIED  │ │ HELD │ │ ESCALATED │  │  PROCESSING_FAILED   │
        │(AI auto) │ │      │ │ (AI direct│  │                      │
        └──────────┘ └──┬───┘ └─────┬─────┘  └──────────┬───────────┘
                        │           │                    │
                   Priya action      │               Reprocess
                        │           │                    ▼
             ┌──────────┼──────┐    │             ┌──────────┐
             │          │      │    │             │ RECEIVED │
             ▼          ▼      ▼    │             └──────────┘
        ┌────────┐ ┌────────┐ ┌──────────┐
        │APPLIED │ │ESCALAT.│ │ APPLIED  │   ← override paths
        │(approv)│ │(reject)│ │(override)│
        └────────┘ └───┬────┘ └──────────┘
                       │
              ─────────┴──────── (both AI-direct and Priya-reject)
                       │
                  Damien action
                       │
         ┌─────────────┼──────────────┐
         │             │              │
         ▼             ▼              ▼
   ┌──────────┐  ┌─────────────────┐  ┌──────────┐
   │ APPLIED  │  │   PENDING_      │  │ RETURNED │
   │ (final)  │  │ SENDER_RESPONSE │  │ (final)  │
   └──────────┘  └───────┬─────────┘  └──────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌──────────┐ ┌────────┐ ┌───────────┐
        │ APPLIED  │ │RETURNED│ │ ESCALATED │
        │ (final)  │ │(final) │ │(SLA breach│
        └──────────┘ └────────┘ └───────────┘
```

### Status Definitions

| Status | Meaning | How It Gets Here | Terminal? |
|--------|---------|-----------------|-----------|
| RECEIVED | Payment ingested, awaiting pipeline | Initial state after ingest; also after reprocess | No |
| PROCESSING | Pipeline actively running | Set at start of signal computation | No |
| APPLIED | Payment allocated to a policy ledger | AI auto-apply, Priya approval/override, Damien approval | Yes |
| HELD | Waiting for Priya's review | AI recommends with requires_human_approval = true | No |
| ESCALATED | Routed to Damien's investigation queue | AI direct-escalate, Priya rejection, or SLA breach | No |
| PROCESSING_FAILED | Pipeline failed after 3 retries | Transient error — reprocessable via API | No |
| PENDING_SENDER_RESPONSE | Damien initiated outreach; SLA timer running | Damien logs a contact attempt | No |
| RETURNED | Payment sent back to sender | Damien's final determination after investigation | Yes |

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
| 1 | 09:01:23 | RECEIVED | system | Payment ingested, status = RECEIVED |
| 2 | 09:01:23 | — | system | status = PROCESSING (pipeline starts) |
| 3 | 09:01:24 | SIGNALS_COMPUTED | system | 19 signals computed and snapshotted |
| 4 | 09:01:25 | RECOMMENDATION_MADE | system | APPLY, 85% confidence, Scenario 2, status = HELD |
| 5 | 10:15:00 | ANNOTATED | Priya (USR-0001) | Case note: "Confirmed with customer records" |
| 6 | 10:15:00 | APPROVED | Priya (USR-0001) | decision_attribution = HUMAN_CONFIRMED |
| 7 | 10:15:00 | APPLIED | Priya (USR-0001) | Ledger updated, balance adjusted |

The audit trail is append-only. Entries are never modified or deleted.

---

## Database Tables Touched Per Stage

| Stage | Reads From | Writes To |
|-------|-----------|----------|
| 1. Ingest | — | payments, audit_log |
| 2. Signals | customers, policies, payment_history, risk_flags, payments, configuration_thresholds | payment_signals, audit_log |
| 3. AI Agent | payment_signals, configuration_thresholds | — (output held in memory) |
| 4. Persist | — | payment_recommendations, payments, audit_log |
| 5. Human Actions | payments, payment_recommendations | payments, payment_history, policies, case_annotations, case_documents, audit_log |
| Config Workflow | configuration_thresholds | configuration_change_requests, configuration_threshold_history, audit_log |
| Governance | — | governance_reviews, anomaly_flags, audit_log |

---

*End of Document*
