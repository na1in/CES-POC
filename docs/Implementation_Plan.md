# CES Payment Resolution — Implementation Plan

**Date:** March 14, 2026
**Team:** 2 Engineers (A & B) + 1 Designer
**Estimated Duration:** 7 weeks

---

## Phase 0: Foundation (Week 1) — All Hands

Everyone unblocked before splitting into parallel tracks.

| Ticket | Owner | Description | Deliverable |
|--------|-------|-------------|-------------|
| DB setup & seed data | Engineer A | Postgres setup, run `schema.sql`, seed `configuration_thresholds` with defaults, seed test customers/policies/payment history | Working DB with test data |
| Proto compilation | Engineer A | Set up protobuf compilation pipeline, generate Python classes from `proto/` | Generated Python proto classes |
| FastAPI project structure | Engineer B | Auth middleware, DB session management (async SQLAlchemy + asyncpg), error handling, health check, config loader | Running FastAPI app skeleton |
| UI/UX design | Designer | Design all 4 pages: Dashboard, Payment List, Payment Detail (signals/reasoning/approve-reject), Settings. Use wireframes in `docs/architecture/05_Human_Approval_Queue.md` as starting point | Figma designs for all pages |

**Exit criteria:** DB running with test data, FastAPI app starts, proto classes generated, designs reviewed.

---

## Phase 1: Core Pipeline + Frontend Shell (Weeks 2–4) — Parallel Tracks

### Track A: Backend Pipeline (Engineer A)

Stages are sequential — each feeds the next.

| Ticket | Description | Depends On | Est. |
|--------|-------------|------------|------|
| **Ingest endpoint** | `POST /api/payments/ingest` — validate required fields (amount, sender, method, date), call Claude API to parse free-text references (extract policy #, intent, period count), generate PMT-XXX ID, INSERT into `payments` (status=RECEIVED), write RECEIVED audit log | Phase 0 | 3d |
| **Signal Engine — Wave 1** | Run in parallel: name similarity (hybrid w/ Haiku for gray zone 70-92%), amount variance, timing quality, duplicate check (3 exact + $2 tolerance). Modules: `matching.py`, `amount.py`, `temporal.py`, `duplicate.py` | Ingest | 4d |
| **Signal Engine — Wave 2** | Policy match confidence, customer match confidence, over/underpayment, historical consistency. Depends on Wave 1 outputs (name score, variance, parsed policy #) | Wave 1 | 3d |
| **Signal Engine — Wave 3** | Risk flags, account status, outstanding balance, payment method risk level, supporting signals, multi-period indicator, multi-method indicator, third-party indicator, time between payments, duplicate amount difference | Wave 2 | 3d |
| **Signal snapshot** | Persist all 19 signals to `payment_signals` table, write SIGNALS_COMPUTED audit log | Waves done | 1d |

### Track B: Frontend Shell (Engineer B + Designer)

Fully parallel with Track A — uses mock data matching the API contract.

| Ticket | Owner | Description | Depends On | Est. |
|--------|-------|-------------|------------|------|
| **API types & mock data** | Engineer B | TypeScript types from proto definitions, mock API responses for all endpoints (list, detail, signals, recommendation, audit trail) | Phase 0 | 2d |
| **Dashboard page** | Engineer B + Designer | `/` — status count cards (Received/Applied/Held/Escalated), scenario breakdown bar chart, PROCESSING_FAILED alert | Types | 2d |
| **Payment List page** | Engineer B + Designer | `/payments` — filterable/sortable table with columns (ID, Sender, Amount, Scenario, Status, Date). Filters: status, scenario, date range, search | Types | 3d |
| **Payment Detail page** | Engineer B + Designer | `/payments/[id]` — payment info card, computed signals panel (visual bars + pass/fail), AI reasoning panel (ordered list + confidence), audit timeline, approve/reject buttons with notes input | Types | 4d |
| **Settings page** | Engineer B + Designer | `/settings` — threshold editor form (name match %, amount tolerance %, duplicate window, gray zone bounds), save button, note about existing payments unaffected | Types | 1d |

**Exit criteria:** Full pipeline from ingest through signal snapshot working. All 4 frontend pages built and functional with mock data.

---

## Phase 2: AI Agent + Real APIs (Weeks 5–6) — Parallel Tracks

### Track A: AI Agent + Persist (Engineer A)

| Ticket | Description | Depends On | Est. |
|--------|-------------|------------|------|
| **Scenario Router** | Deterministic if/else routing in `router.py`. Scenario 5 runs first (duplicate check). Then route to 1-4 based on: policy reference present? Name ≥75%? Variance ≤2%? Customer match ≥90% or <90% w/ 2+ supporting signals? Pure Python, fully unit-testable | Signals done | 2d |
| **Scenario 1 — Strong Policy Match** | Claude API prompt + output parsing. Paths: auto-apply (name >90%, no risk flags, active policy, low-risk method), hold (name 75-90% OR risk flags OR high-risk method), reroute (name <75%) | Router | 1.5d |
| **Scenario 2 — Customer Match, No Policy** | Disambiguation: single policy → APPLY w/ approval, amount matches 1 of N → APPLY w/ approval, ambiguous → HOLD. Always requires approval. Reroute to Sc3 if variance >15% | Router | 1.5d |
| **Scenario 3 — High Amount Variance** | 5 variance tiers. Special case checks before escalating (15-50%): multi-period, multi-method, third-party → HOLD instead of ESCALATE. Name must be ≥90%, else reroute to Sc4 | Router | 2d |
| **Scenario 4 — No Matching Customer** | Third-party check first (valid policy + third-party pattern + amount ≤15% → HOLD). Otherwise ESCALATE. Provide best fuzzy match + amount correlation | Router | 1d |
| **Scenario 5 — Duplicate Payment** | 3 exact fields + $2 amount tolerance within 72hrs. Balance >0 → HOLD, balance =0 → ESCALATE. Capture duplicate_amount_difference | Router | 1d |
| **Persist layer** | `persist.py` — single DB transaction: INSERT recommendation, UPDATE payment status + matched IDs, auto-apply ledger update (INSERT payment_history + UPDATE policy balance), audit log RECOMMENDATION_MADE | Scenarios | 1.5d |
| **Pipeline orchestrator** | `pipeline.py` — ties stages together. Retry wrapper: 3 attempts (1s, 3s backoff). Retryable: DB timeouts, deadlocks, Claude API timeouts/rate limits. Non-retryable: constraint violations, validation errors. Exhausted → PROCESSING_FAILED | Persist | 1d |

### Track B: Real API Endpoints (Engineer B)

| Ticket | Description | Depends On | Est. |
|--------|-------------|------------|------|
| **GET `/api/payments`** | List with filters (status, scenario, date range, sender search) + pagination. Sort by date desc | Phase 1 frontend | 1.5d |
| **GET `/api/payments/{id}`** | Full detail: payment + signals + recommendation + audit trail. Join across 4 tables | Phase 1 frontend | 1d |
| **POST `/api/payments/{id}/approve`** | Validate status=HELD. Single transaction: status → APPLIED, INSERT payment_history, UPDATE policy balance, audit log APPROVED + APPLIED (actor = analyst ID) | Phase 1 frontend | 1.5d |
| **POST `/api/payments/{id}/reject`** | Validate status=HELD. Status → ESCALATED, audit log ESCALATED (actor + rejection notes) | Phase 1 frontend | 0.5d |
| **GET/PUT `/api/settings/thresholds`** | Read all thresholds, update individual thresholds. Changes effective for new payments only | Phase 1 frontend | 1d |
| **POST `/api/payments/{id}/reprocess`** | Validate status=PROCESSING_FAILED. Reset to RECEIVED, re-run full pipeline | Pipeline done | 0.5d |
| **Wire frontend to real APIs** | Replace all mock data with real API calls, add loading states, error handling | APIs done | 2d |

**Exit criteria:** End-to-end flow works: submit payment → signals computed → routed → recommendation → approve/reject. All APIs live, frontend connected.

---

## Phase 3: Integration & Polish (Week 7) — All Hands

| Ticket | Owner | Description |
|--------|-------|-------------|
| **E2E test: Scenario 1** | Engineer A | Strong match auto-apply + hold (ambiguous name) + hold (risk flags) + hold (high-risk method) |
| **E2E test: Scenario 2** | Engineer A | Single policy, amount disambiguates, ambiguous multi-policy |
| **E2E test: Scenario 3** | Engineer A | Each variance tier + multi-period + multi-method + third-party special cases |
| **E2E test: Scenario 4** | Engineer A | No match escalate + third-party hold |
| **E2E test: Scenario 5** | Engineer A | Exact duplicate, $2 tolerance, balance justifies, outside window |
| **E2E test: Retry & failure** | Engineer A | Simulate transient failures, verify 3 retries, PROCESSING_FAILED status, reprocess |
| **Frontend integration testing** | Engineer B | Real API calls across all pages, error states, empty states, loading spinners |
| **Threshold config validation** | Engineer B | Change thresholds → verify new payments use new values, old recommendations unaffected |
| **UI polish** | Designer + Engineer B | Responsive layout, empty states, error toasts, edge case screens, accessibility |

**Exit criteria:** All 5 scenarios tested end-to-end. Frontend polished and responsive. Retry/failure paths verified.

---

## Parallelization Summary

```
Week 1:     [========= Phase 0: Foundation (all hands) =========]

               Engineer A                    Engineer B + Designer
            ─────────────────           ──────────────────────────
Week 2:     Ingest endpoint              API types + mock data
Week 3:     Signal Engine (Waves 1-2)    Dashboard + Payment List
Week 4:     Signal Engine (Wave 3)       Payment Detail + Settings
            + Snapshot

Week 5:     Scenario Router              GET /payments, GET /payments/{id}
            + Scenarios 1-3              + approve/reject endpoints
Week 6:     Scenarios 4-5               Settings API + reprocess
            + Persist + Pipeline         + Wire frontend to real APIs

Week 7:     [========= Phase 3: Integration & Polish (all hands) =========]
```

---

## Risk & Dependencies

| Risk | Mitigation |
|------|-----------|
| Claude API latency in pipeline | Retry wrapper handles transient issues; async calls prevent blocking |
| Gray-zone name matching accuracy | Haiku calls are logged with both scores for tuning; gray zone bounds are configurable |
| Frontend blocked on API contract | Mock data defined upfront from proto types; frontend never waits for backend |
| Complex scenario edge cases | Scenario docs have worked examples and edge cases; deterministic router is unit-testable in isolation |
| Threshold tuning | All thresholds DB-driven and editable via Settings page; no code deploy needed |

---

## Key Reference Documents

| Document | Purpose |
|----------|---------|
| `docs/architecture/00_Summary.md` | Architecture overview |
| `docs/architecture/01-07_*.md` | Detailed docs per pipeline stage |
| `docs/scenarios/Scenario_1-5_*.md` | Decision logic, examples, edge cases per scenario |
| `docs/Final_Scenario_Definitions.md` | Authoritative decision logic with full examples |
| `docs/Step3_Feature_Signals.md` | All 19 signals with computation methods |
| `proto/*.proto` | Source of truth for all data models |
| `db/schema.sql` | PostgreSQL schema |

---

*End of Document*
