# CES — Customer Exception System (Payment Resolution)

## What this project does
AI agent that processes unidentified/miscellaneous insurance payments and recommends one of three actions: APPLY, HOLD, or ESCALATE. Payments are routed through 5 scenarios based on match quality, amount variance, and duplicate detection.

## Stack
### Backend
- Python 3.12+
- FastAPI (async)
- PostgreSQL with SQLAlchemy (async) + asyncpg
- Protobuf (proto3)
- Claude API (`anthropic` SDK) for AI agent components
- jellyfish (Jaro-Winkler, Levenshtein, Soundex for name matching)

## Rules
Always before making any changes, search the web for the newest chanes and only implemen if it if you are 100% sure that it is the best way to do it.

### Frontend
- Next.js + React
- TypeScript
- Tailwind CSS + shadcn/ui

## Key paths
- `backend/` — FastAPI application
- `frontend/` — Next.js application
- `proto/` — protobuf definitions (source of truth for data models)
- `db/schema.sql` — PostgreSQL schema derived from protos
- `docs/` — design and specification documents
  - `docs/scenarios/` — detailed scenario specifications (1-5)
  - `docs/architecture/` — architecture docs split by pipeline stage (00-07)
  - `docs/Final_Scenario_Definitions.md` — authoritative decision logic with examples
  - `docs/Step3_Feature_Signals.md` — 19 signal computation methods across 5 categories
  - `docs/Executive_Summary_Scenarios.md` — overview with routing flow and decision matrix
  - `docs/Database_Design.md` — proto-to-DB mapping and design notes

## Conventions
- Monetary amounts are stored as integers in cents (never floats)
- IDs use prefixed format: `CUST-XXXX`, `POL-XXXXX`, `PMT-XXX`
- Proto files are the source of truth — schema and application models derive from them
- All DB operations use transactions
- Enums in Postgres are lowercase snake_case (`fraud_history`, not `FRAUD_HISTORY`)
- When updating decision logic, update in this order: protos → schema → scenario docs → architecture docs → reference docs

## Architecture (5-Stage Pipeline)
1. **Ingest** (code + Claude API) — validate fields, parse free-text references to extract policy numbers/intent/period count, persist payment as RECEIVED
2. **Compute Signals** (code + Claude Haiku for gray-zone names) — 19 signals in 3 dependency waves, snapshot to `payment_signals`
3. **AI Agent** (deterministic router + Claude API reasoning) — Scenario 5 runs first (duplicate check), then route to 1-4. Produces structured recommendation JSON
4. **Persist** (code) — single DB transaction: save recommendation + update status + fill matched IDs + auto-apply ledger + audit log. Retry wrapper: 3 attempts with backoff
5. **Human Approval Queue** (Next.js frontend) — analyst reviews HELD payments, approves (→ APPLIED, ledger updated) or rejects (→ ESCALATED)

## 5 Scenarios (Routing is deterministic if/else, reasoning uses Claude API)
1. **Strong Policy Match** — policy # provided, name ≥75%, variance ≤2%. Auto-apply requires: name >90%, no risk flags, active policy, low-risk payment method
2. **Customer Match, No Policy** — customer match ≥90% (or <90% with 2+ supporting signals), no policy ref. Always requires human approval
3. **High Amount Variance** — match found but variance >2%. Tiers: 2-15% HOLD, 15-50% check special cases (multi-period, multi-method, third-party → HOLD), >100% ESCALATE. Name must be ≥90%
4. **No Matching Customer** — all matching failed. Check for third-party payment first (employer, family, escrow → HOLD if amount ≤15%), otherwise ESCALATE
5. **Duplicate Payment** — runs FIRST on every payment. Match: 3 exact fields (sender, method, reference) + amount within $2 tolerance, within 72hrs. Balance >0 → HOLD, balance =0 → ESCALATE

## 19 Signals (5 categories, 3 computation waves)
### Category 1: Matching & Identification (4)
- Name Similarity Score (0-100%, hybrid: traditional algorithms + Claude Haiku for gray zone 70-92%)
- Policy Match Confidence (0-100%)
- Customer Match Confidence (0-100%)
- Supporting Signals (3 booleans: account_match, amount_match, historical_match)

### Category 2: Amount & Variance (7)
- Amount Variance %
- Overpayment/Underpayment (enum + cents)
- Multi-Period Indicator (boolean + period count)
- Multi-Method Indicator (boolean + fraction — detects split premium across banks)
- Third-Party Indicator (boolean + relationship type — employer, family, escrow, trust, POA)
- Historical Consistency (score from z-score outlier detection)

### Category 3: Temporal & Pattern (2)
- Payment Timing Quality (EXCELLENT/GOOD/ACCEPTABLE/POOR based on days from due)
- Days Since Last Payment

### Category 4: Risk & Fraud (4)
- Risk Flags (fraud_history, suspended_account, chronic_late_payments)
- Account Status (ACTIVE/INACTIVE/CLOSED/PENDING)
- Outstanding Balance (cents + CURRENT/PAST_DUE)
- Payment Method Risk Level (Low=ACH/Card, Medium=Check/Wire, High=Unknown)

### Category 5: Duplicate Detection (4) — only computed if duplicate detected
- Duplicate Match (binary: 3 exact + $2 tolerance)
- Time Between Payments (hours)
- Balance Justification (boolean)
- Duplicate Amount Difference (cents, 0=exact, up to 200=$2)

## Hybrid Name Matching
- Traditional: Jaro-Winkler + Levenshtein + Soundex → deterministic_score
- If score <70%: clear mismatch, no LLM call
- If score >92%: clear match, no LLM call
- If score 70-92% (gray zone): call Claude Haiku → final = max(deterministic, llm)
- Gray zone boundaries configurable in `configuration_thresholds`
- Estimated 15-20% of payments hit gray zone

## Configuration thresholds (stored in DB, never hardcoded)
| Parameter | Default | Used For |
|-----------|---------|----------|
| `name_match_auto_apply` | 90% | Scenario 1 auto-apply boundary |
| `name_match_hold` | 75% | Hold vs escalate boundary |
| `name_gray_zone_lower` | 70% | Below = skip LLM |
| `name_gray_zone_upper` | 92% | Above = skip LLM |
| `amount_tolerance_auto` | 2% | Auto-approve variance |
| `duplicate_window_hours` | 72 | Duplicate detection window |
| `duplicate_amount_tolerance_cents` | 200 | $2 max diff for duplicate match |
| `multi_period_tolerance` | 5% | Multi-period payment detection |

## Payment statuses
RECEIVED → PROCESSING → APPLIED / HELD / ESCALATED / PROCESSING_FAILED / PENDING_SENDER_RESPONSE / RETURNED
- PROCESSING_FAILED: pipeline failed after 3 retries, can be reprocessed via API
- HELD → APPLIED (analyst approves) or ESCALATED (analyst rejects)
- ESCALATED → PENDING_SENDER_RESPONSE (Damien awaiting sender reply, SLA timer starts) → APPLIED / RETURNED / ESCALATED
- PENDING_SENDER_RESPONSE → SLA breach triggers Lorraine's exception dashboard

## Retry strategy
- Ingest always succeeds (payment saved as RECEIVED)
- Processing pipeline retried up to 3 times with backoff (1s, 3s)
- Retryable: DB timeouts, deadlocks, Claude API timeouts/rate limits
- Not retryable: constraint violations, validation errors, unknown errors
- After 3 failures: status → PROCESSING_FAILED, audit logged, visible in UI

## Frontend pages

### Analyst (Priya) + Investigator (Damien)
1. **Queue Dashboard** (`/`) — open cases sorted by AI confidence score; columns: scenario, sender name, amount, **payment method**, AI recommendation, confidence band, age
2. **Investigation Queue** (`/investigations`) — Damien only; escalated cases pre-sorted by risk level; shows risk indicator + time since escalation
3. **Payment Detail** (`/payments/[id]`) — payment info (incl. payment method), signal bars with algorithm breakdown, AI reasoning panel, audit timeline, approve/reject/override/return buttons, annotation panel, document upload + list

### Director (Lorraine)
4. **Governance Dashboard** (`/governance`) — metric cards: Auto-Applied by AI, Applied after Human Review, Held Pending Review, Escalated by AI, Escalated by Human, Human Overrides; payment method breakdown chart; override rate trend; SLA adherence; confidence score histogram; date range filter
5. **Compliance Export** (`/governance/export`) — date range selector, export scope, download structured report
6. **Exception Dashboard** (`/governance/exceptions`) — SLA-breached cases, anomaly flags, config change requests pending approval

### Admin (Marcus)
7. **Admin Dashboard** (`/admin`) — per-scenario analytics: case volume trend, decision distribution, override rate by confidence band, confidence histogram
8. **Override Analysis** (`/admin/overrides`) — filterable by scenario, confidence band, date range, override reason category
9. **Configuration Management** (`/admin/config`) — current thresholds, change request form, version history, staging simulation, deploy/rollback controls

### Shared
10. **Settings** (`/settings`) — threshold viewer (read-only for non-admin; change request flow for admin)

## API endpoints

### Payments
- `POST /api/payments/ingest` — submit new payment
- `GET /api/payments` — list with filters + pagination (sortable by confidence_score, has_risk_flags, payment_method)
- `GET /api/payments/{id}` — full detail (payment + signals + recommendation + audit + annotations + documents)
- `POST /api/payments/{id}/approve` — analyst approves HELD → APPLIED + ledger update
- `POST /api/payments/{id}/reject` — analyst rejects HELD → ESCALATED
- `POST /api/payments/{id}/override` — override AI recommendation (mandatory reason field)
- `POST /api/payments/{id}/return` — Damien marks payment as returned to sender
- `POST /api/payments/{id}/reprocess` — re-run pipeline for PROCESSING_FAILED

### Annotations
- `POST /api/payments/{id}/annotations` — add case note, override reason, or investigation note
- `GET /api/payments/{id}/annotations` — list all annotations for a case

### Documents
- `POST /api/payments/{id}/documents` — upload supporting document (multipart)
- `GET /api/payments/{id}/documents` — list document metadata for a case
- `GET /api/payments/{id}/documents/{doc_id}` — download/stream document
- `DELETE /api/payments/{id}/documents/{doc_id}` — soft delete only

### Settings / Configuration
- `GET /api/settings/thresholds` — read current active thresholds
- `POST /api/settings/change-requests` — Marcus submits a change proposal
- `GET /api/settings/change-requests` — list change requests (filterable by status)
- `POST /api/settings/change-requests/{id}/approve` — Lorraine approves
- `POST /api/settings/change-requests/{id}/reject` — Lorraine rejects (mandatory comment)
- `POST /api/settings/change-requests/{id}/deploy` — Marcus deploys approved change
- `POST /api/settings/change-requests/{id}/rollback` — emergency rollback (requires Lorraine approval)
- `GET /api/settings/thresholds/history` — full version history for all parameters

### Analytics
- `GET /api/analytics/decisions` — decision attribution breakdown (AI vs human, by payment method, by scenario)
- `GET /api/analytics/overrides` — override analysis (filterable by scenario, confidence band, date, reason)

### Governance
- `POST /api/governance/reviews` — Lorraine records a period review
- `GET /api/governance/reviews` — list governance reviews
- `POST /api/governance/anomalies` — Lorraine flags a metric anomaly for Marcus
- `GET /api/governance/anomalies` — list anomaly flags (filterable by status)
- `PATCH /api/governance/anomalies/{id}` — Marcus updates investigation status + resolution notes
- `GET /api/governance/export` — export audit-ready report (date range + scope)

## Backend module structure
| Module | Responsibility |
|--------|---------------|
| `backend/app/services/signal_engine.py` | Orchestrates 3 signal waves |
| `backend/app/services/signals/matching.py` | Hybrid name matching with full algorithm breakdown (jaro_winkler, levenshtein, soundex, llm_score) |
| `backend/app/services/signals/amount.py` | Variance, multi-period, multi-method, third-party, historical |
| `backend/app/services/signals/temporal.py` | Timing quality, days since last |
| `backend/app/services/signals/risk.py` | Risk flags, account status, balance snapshot, payment method risk |
| `backend/app/services/signals/duplicate.py` | 72hr duplicate detection with $2 tolerance |
| `backend/app/services/agent/router.py` | Deterministic scenario routing |
| `backend/app/services/agent/reasoning.py` | Claude API structured prompts |
| `backend/app/services/agent/scenarios/sc1-5` | Per-scenario prompt, criteria, output parsing |
| `backend/app/services/persist.py` | Single-transaction save; sets decision_attribution at closure |
| `backend/app/services/pipeline.py` | End-to-end orchestrator with retry |
| `backend/app/services/storage.py` | Document storage abstraction (local FS for PoC, S3-compatible) |
| `backend/app/services/sla.py` | SLA deadline computation and breach detection |
| `backend/app/routers/approvals.py` | Approve/reject/override/return endpoints |
| `backend/app/routers/annotations.py` | Case annotation endpoints |
| `backend/app/routers/documents.py` | Document upload/download/list endpoints |
| `backend/app/routers/analytics.py` | Decision attribution + override analysis endpoints |
| `backend/app/routers/governance.py` | Review log, anomaly flags, audit export endpoints |
| `backend/app/routers/config.py` | Change request workflow + threshold history endpoints |

## Key proto files
| File | Contents |
|------|----------|
| `proto/payment.proto` | Payment, PaymentStatus (incl. pending_sender_response, returned) |
| `proto/signals.proto` | PaymentSignals with full name matching breakdown |
| `proto/recommendation.proto` | PaymentRecommendation with DecisionAttribution |
| `proto/audit.proto` | AuditLogEntry (all 20 action types), ConfigurationThreshold |
| `proto/user.proto` | User, UserRole |
| `proto/document.proto` | CaseDocument, DocumentType |
| `proto/annotation.proto` | CaseAnnotation, AnnotationType |
| `proto/config_change.proto` | ConfigurationChangeRequest, ConfigurationThresholdVersion |
| `proto/analytics.proto` | DecisionAttribution, AnalyticsDecisionsResponse, AnomalyFlag |
| `proto/customer.proto` | Customer, RiskFlag, RiskFlagType |
| `proto/policy.proto` | Policy, PaymentHistory |

## Implementation plan
See `docs/Implementation_Plan.md` for the full phased plan with ticket breakdowns, parallel tracks, estimates, and risk mitigation. Team: 2 engineers + 1 designer, ~7 weeks.

## GitHub
- Repository: https://github.com/na1in/CES-POC
- Main branch: `main`
