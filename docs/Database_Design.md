# Database Design - AI Agent Payment Resolution

## Context

The AI Agent Payment Resolution system processes incoming payments and routes them through 5 scenarios to determine whether to **APPLY**, **HOLD**, or **ESCALATE**. The database stores payment inputs, customer/policy reference data, computed signals, recommendations, audit trails, user records, case annotations, case documents, configuration change history, analytics, and governance data.

This is a **design document only**, database-agnostic. All message and enum definitions live in Protocol Buffer files under `proto/`.

---

## Proto Files

| File | Messages / Enums | Description |
|------|-----------------|-------------|
| `proto/customer.proto` | `Customer`, `RiskFlag`, `RiskFlagType`, `CustomerStatus` | Customer accounts and risk flags (fraud_history, suspended_account, chronic_late_payments) |
| `proto/policy.proto` | `Policy`, `PaymentHistory`, `PolicyStatus`, `PremiumFrequency`, `PaymentHistoryStatus` | Insurance policies and historical payment records for pattern analysis |
| `proto/payment.proto` | `Payment`, `PaymentStatus` | Incoming payments; status lifecycle includes PENDING_SENDER_RESPONSE and RETURNED; SLA fields (investigation_due_date, sla_breached) |
| `proto/signals.proto` | `PaymentSignals`, `MatchingSignals`, `AmountSignals`, `TemporalSignals`, `RiskSignals`, `DuplicateSignals`, `PaymentTimingQuality`, `AccountStatus`, `PaymentMethodRiskLevel` | All 19 computed feature signals (1-to-1 with Payment); MatchingSignals includes full algorithm breakdown |
| `proto/recommendation.proto` | `PaymentRecommendation`, `Recommendation`, `ScenarioRoute` | Final AI agent decision output (1-to-1 with Payment); decision_attribution set at case closure |
| `proto/audit.proto` | `AuditLogEntry`, `ConfigurationThreshold`, `AuditActionType` | Append-only audit trail (20 action types); current active threshold values |
| `proto/user.proto` | `User`, `UserRole` | System users; role (ANALYST/INVESTIGATOR/DIRECTOR/ADMIN) controls home screen, data scope, and decision authority |
| `proto/document.proto` | `CaseDocument`, `DocumentType` | Document metadata for case attachments; files in object storage; soft-delete only |
| `proto/annotation.proto` | `CaseAnnotation`, `AnnotationType` | Immutable case notes and contact records; append-only for audit compliance |
| `proto/config_change.proto` | `ConfigurationChangeRequest`, `ConfigurationThresholdVersion`, `ConfigChangeStatus` | Marcus→Lorraine approval workflow for threshold changes; full version history |
| `proto/analytics.proto` | `DecisionAttribution`, `AnalyticsDecisionsResponse`, `ScenarioBreakdown`, `PaymentMethodBreakdown`, `AnomalyFlag` | Governance and admin dashboard data; decision attribution (AI_AUTONOMOUS / HUMAN_CONFIRMED / HUMAN_OVERRIDE) |

---

## Relationships

```
Customer (1) ──→ (many) Policy
Customer (1) ──→ (many) RiskFlag
Policy   (1) ──→ (many) PaymentHistory

Payment  (1) ──→ (1)    PaymentSignals
Payment  (1) ──→ (1)    PaymentRecommendation
Payment  (many) → (1)   Customer  (optional — may not be matched)
Payment  (many) → (1)   Policy    (optional — may not be matched)

Payment  (1) ──→ (many) AuditLogEntry
Payment  (1) ──→ (many) CaseAnnotation
Payment  (1) ──→ (many) CaseDocument

User     (1) ──→ (many) AuditLogEntry               (actor_user_id FK)
User     (1) ──→ (many) CaseAnnotation              (author_user_id FK)
User     (1) ──→ (many) CaseDocument                (uploaded_by FK)
User     (1) ──→ (many) ConfigurationChangeRequest  (proposed_by / approved_by FK)
User     (1) ──→ (many) AnomalyFlag                 (flagged_by / assigned_to FK)

ConfigurationChangeRequest (1) ──→ (many) ConfigurationThresholdVersion
```

---

## Key Indexes

When backed by a datastore that supports indexing:

**Payment lookups:**
- `Payment(payment_date)` — 72-hour duplicate window searches
- `Payment(sender_name)` — name similarity lookups
- `Payment(amount)` — amount correlation searches
- `Payment(status)` — queue filtering (HELD, ESCALATED, PROCESSING_FAILED)
- `Payment(sla_breached, investigation_due_date)` — Lorraine's exception dashboard

**Signal and history queries:**
- `PaymentHistory(policy_id, payment_date)` — historical pattern queries
- `Policy(policy_number, status)` — policy lookups
- `RiskFlag(customer_id, is_active)` — active risk flag checks
- `AuditLogEntry(payment_id, timestamp)` — audit trail reconstruction

**Case management:**
- `CaseAnnotation(payment_id, created_at)` — annotation timeline
- `CaseDocument(payment_id, is_deleted)` — active document list

**Configuration:**
- `ConfigurationChangeRequest(status)` — pending approvals for Lorraine

**Analytics:**
- `AnomalyFlag(status, assigned_to)` — open anomaly investigation queue

---

## Data Flow

1. Payment ingested → `payments` (status: RECEIVED) + `audit_log` (RECEIVED)
2. Signals computed → `payment_signals` + `audit_log` (SIGNALS_COMPUTED)
3. Scenario routing + AI decision → `payment_recommendations` + `payments` (status updated) + `audit_log` (RECOMMENDATION_MADE)
   - ESCALATED: also sets `investigation_due_date` on payment
4. Human actions on HELD payments (Priya — Analyst):
   - Approve → `payments` (APPLIED) + `payment_history` + `policies.outstanding_balance` + `audit_log` (APPROVED, APPLIED)
   - Reject → `payments` (ESCALATED) + `investigation_due_date` set + `audit_log` (ESCALATED)
   - Override → `payments` (new status) + `case_annotations` (OVERRIDE_REASON) + `audit_log` (OVERRIDDEN)
5. Human actions on ESCALATED payments (Damien — Investigator):
   - Log contact → `case_annotations` (CONTACT_RECORD) + `payments` (PENDING_SENDER_RESPONSE) + `audit_log` (CONTACT_LOGGED)
   - Apply → `payments` (APPLIED) + `payment_history` + `audit_log` (APPLIED)
   - Return → `payments` (RETURNED) + `audit_log` (RETURNED)
6. SLA breach (system) → `payments.sla_breached = true` + `audit_log` (SLA_BREACHED)
7. Case notes / documents → `case_annotations` + `case_documents` + `audit_log` (ANNOTATED / DOCUMENT_UPLOADED)
8. Config change workflow → `configuration_change_requests` → `configuration_threshold_history` + `audit_log` (CONFIG_CHANGE_*)
9. Governance actions (Lorraine) → `governance_reviews` / `anomaly_flags` + `audit_log`

---

## Design Notes

### Monetary Amounts
All monetary values (`amount`, `premium_amount`, `outstanding_balance`, `difference_amount`, `duplicate_amount_difference`) are stored as `int64` in **cents** to avoid floating-point precision issues. Never use floats for money.

### Scores and Percentages
Confidence scores and similarity scores (0-100) use `double`. Exact precision is not required for ML confidence values.

### Enums in PostgreSQL
Postgres enums are lowercase snake_case to match proto naming after conversion (e.g., `fraud_history`, not `FRAUD_HISTORY`; `ai_autonomous`, not `AI_AUTONOMOUS`).

### Nullable / Unset Fields
Proto3 uses default values (0, false, empty string) for unset fields. Where the distinction matters (e.g., `matched_customer_id` unset vs. empty match), document the sentinel clearly.

### Append-Only Tables
`AuditLogEntry` and `CaseAnnotation` are **append-only** — entries are never updated or deleted. Hard requirement for regulatory audit compliance.

### Soft Delete
`CaseDocument` uses `is_deleted` (bool) for soft delete only. Hard deletes are prohibited for audit compliance. Queries should filter `WHERE is_deleted = false` by default.

### Signal Snapshot
`PaymentSignals` is snapshotted at decision time. Even if customer data changes later (new risk flag, policy cancelled), the record of what the system saw at decision time is permanent and immutable.

### MatchingSignals Algorithm Breakdown
`MatchingSignals` stores the full name-matching algorithm provenance:
- `jaro_winkler_score` — raw Jaro-Winkler similarity (0-100)
- `levenshtein_score` — raw Levenshtein-based similarity (0-100)
- `soundex_match` — whether Soundex codes matched
- `deterministic_score` — combined traditional score before any LLM call
- `used_llm` — whether the gray-zone Claude Haiku call was made
- `llm_score` — Claude Haiku score if called (0 if not used)

Gives Damien (Investigator) full algorithmic provenance when reviewing escalated cases.

### Decision Attribution
`PaymentRecommendation.decision_attribution` is set at **case closure**, not at AI decision time. At pipeline time it is `UNSPECIFIED`. When a human takes a final action it is set to:
- `AI_AUTONOMOUS` — auto-applied or escalated with no human touch
- `HUMAN_CONFIRMED` — human agreed with AI recommendation
- `HUMAN_OVERRIDE` — human changed the outcome

This field drives Lorraine's governance dashboard and Marcus's analytics.

### SLA Fields
`Payment.investigation_due_date` is set when a case is ESCALATED. `Payment.sla_breached` is updated by `sla.py` on a background schedule. SLA-breached cases surface in Lorraine's Exception Dashboard.

### Configuration Change Workflow
Direct threshold edits are not allowed. Every production change requires a `ConfigurationChangeRequest`:
1. Marcus proposes (`status: PENDING`)
2. Lorraine approves or rejects
3. Marcus deploys (`status: DEPLOYED`) → new `ConfigurationThresholdVersion` entry created
4. `ConfigurationThreshold` (current active value) is updated atomically with the version entry

Emergency rollback reverts to the previous `ConfigurationThresholdVersion`.

### PaymentSignals Sub-messages
`PaymentSignals` uses nested sub-messages rather than a flat structure:
- `MatchingSignals` — name similarity + policy/customer confidence + supporting signals + algorithm breakdown
- `AmountSignals` — variance, multi-period, multi-method (split premium), third-party, historical consistency
- `TemporalSignals` — timing quality, days from due date, days since last payment
- `RiskSignals` — risk flags, account status, payment method risk level, outstanding balance snapshot
- `DuplicateSignals` — duplicate match, hours since duplicate, balance justification, amount difference

### Object Storage (Documents)
`CaseDocument` stores metadata only. The actual file bytes live in object storage (local filesystem for PoC, S3-compatible for production). `storage_path` is the key or local path used to retrieve the file.

### JSON Fields
`AuditLogEntry.details` maps to `google.protobuf.Struct` for structured but schema-flexible audit details. `PaymentRecommendation.reasoning` maps to `repeated string` for ordered reasoning points.
