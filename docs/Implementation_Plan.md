# CES Payment Resolution — Implementation Plan

**Date:** April 9, 2026
**Team:** 2 Engineers (A & B) + 1 Designer
**Estimated Duration:** 10 weeks

---

## Scope Overview

The system serves four personas across 10 frontend pages and ~35 API endpoints. Implementation is split into four phases:

| Phase | Weeks | Focus |
|-------|-------|-------|
| 0 | 1 | Foundation — DB, protos, FastAPI skeleton, all 10 page designs |
| 1 | 2–4 | Core pipeline (ingest → signals) + Analyst/Investigator frontend shell |
| 2 | 5–7 | AI Agent + all Analyst/Investigator APIs + Annotations/Documents |
| 3 | 8–9 | Director/Admin pages + Governance/Analytics/Config APIs |
| 4 | 10 | Integration & Polish — all roles, all flows |

---

## Phase 0: Foundation (Week 1) — All Hands

Everyone unblocked before splitting into parallel tracks.

| Ticket | Owner | Description | Deliverable |
|--------|-------|-------------|-------------|
| DB setup & seed data | Engineer A | Postgres setup, run `schema.sql`, seed `configuration_thresholds` with defaults, seed test customers/policies/payment history/users (one per role) | Working DB with test data |
| Proto compilation | Engineer A | Set up protobuf compilation pipeline, generate Python classes from all 11 `proto/` files | Generated Python proto classes |
| FastAPI project structure | Engineer B | Role-based auth middleware (user_id + role from token), DB session management (async SQLAlchemy + asyncpg), error handling, health check, config loader | Running FastAPI app skeleton |
| UI/UX design — Analyst & Investigator | Designer | Design 4 pages: Queue Dashboard, Investigation Queue, Payment Detail (signals w/ algorithm breakdown, reasoning, annotation panel, document panel, all action buttons), Settings. Use `docs/architecture/05_Human_Approval_Queue.md` as reference | Figma designs — Priya & Damien pages |
| UI/UX design — Director & Admin | Designer | Design 6 pages: Governance Dashboard, Compliance Export, Exception Dashboard, Admin Dashboard, Override Analysis, Configuration Management (change-request workflow) | Figma designs — Lorraine & Marcus pages |

**Exit criteria:** DB running with test data, FastAPI app starts, proto classes generated, all 10 page designs reviewed and approved.

---

## Phase 1: Core Pipeline + Analyst/Investigator Frontend Shell (Weeks 2–4)

### Track A: Backend Pipeline (Engineer A)

Stages are sequential — each feeds the next.

| Ticket | Description | Depends On | Est. |
|--------|-------------|------------|------|
| **Ingest endpoint** | `POST /api/payments/ingest` — validate required fields, call Claude API to parse free-text references (extract policy #, intent, period count), generate PMT-XXX ID, INSERT into `payments` (status=RECEIVED), write RECEIVED audit log | Phase 0 | 3d |
| **Signal Engine — Wave 1** | Run in parallel: name similarity (hybrid w/ Haiku for gray zone 70-92%), amount variance, timing quality, duplicate check (3 exact + $2 tolerance). Modules: `matching.py` (with full algorithm breakdown: jaro_winkler, levenshtein, soundex, deterministic_score, used_llm, llm_score), `amount.py`, `temporal.py`, `duplicate.py` | Ingest | 4d |
| **Signal Engine — Wave 2** | Policy match confidence, customer match confidence, over/underpayment, historical consistency. Depends on Wave 1 outputs | Wave 1 | 3d |
| **Signal Engine — Wave 3** | Risk flags, account status, outstanding balance snapshot, payment method risk level, supporting signals, multi-period indicator, multi-method indicator, third-party indicator, time between payments, duplicate amount difference | Wave 2 | 3d |
| **Signal snapshot** | Persist all 19 signals to `payment_signals` (including full MatchingSignals breakdown), write SIGNALS_COMPUTED audit log | Waves done | 1d |

### Track B: Analyst/Investigator Frontend Shell (Engineer B + Designer)

Fully parallel with Track A — uses mock data matching the API contract.

| Ticket | Owner | Description | Depends On | Est. |
|--------|-------|-------------|------------|------|
| ~~**API types & mock data**~~ ✅ | Engineer B | TypeScript types from all proto definitions, mock API responses for analyst/investigator endpoints (queue, detail, signals, recommendation, audit trail, annotations, documents) | Phase 0 | 2d |
| **Queue Dashboard** | Engineer B + Designer | `/` — Priya's home. Open cases sorted by AI confidence score (lowest first). Columns: scenario, sender name, amount, payment method, AI recommendation, confidence band, age. Filters: scenario, confidence, payment method. PROCESSING_FAILED alert + reprocess link | Types | 2d |
| **Investigation Queue** | Engineer B + Designer | `/investigations` — Damien's home. Escalated cases sorted by risk level. Columns: sender, amount, risk indicator, payment method, time since escalation. SLA breach warning | Types | 2d |
| **Payment Detail page** | Engineer B + Designer | `/payments/[id]` — shared across Priya and Damien. Sections: payment info (incl. payment method), signals panel (visual bars + algorithm breakdown for name matching), AI reasoning panel, audit timeline, annotation panel (add/view), document panel (upload/list). Role-gated action buttons: Approve/Reject/Override (Priya), Return/Log Contact (Damien) | Types | 4d |
| **Settings page** | Engineer B + Designer | `/settings` — threshold viewer, read-only for non-admin. Shows current values. Admin link to change-request flow | Types | 1d |

**Exit criteria:** Full pipeline from ingest through signal snapshot working end-to-end. Queue Dashboard, Investigation Queue, Payment Detail, and Settings pages built with mock data.

---

## Phase 2: AI Agent + Analyst/Investigator APIs (Weeks 5–7)

### Track A: AI Agent + Persist + Analyst/Investigator Action APIs (Engineer A)

| Ticket | Description | Depends On | Est. |
|--------|-------------|------------|------|
| **Scenario Router** | Deterministic if/else routing in `router.py`. Scenario 5 first (duplicate check). Then route to 1-4: policy reference + name ≥75% + variance ≤2% → Sc1; ≤2% fails → Sc3; no policy + customer match → Sc2; all fail → Sc4. Pure Python, unit-testable | Signals done | 2d |
| **Scenario 1 — Strong Policy Match** | Claude API prompt + output parsing. Paths: auto-apply (name >90%, no risk flags, active policy, low-risk method), hold (name 75-90% OR risk flags OR high-risk method) | Router | 1.5d |
| **Scenario 2 — Customer Match, No Policy** | Single policy → APPLY w/ approval; amount matches 1 of N → APPLY w/ approval; ambiguous → HOLD. Always requires approval. Reroute to Sc3 if variance >15% | Router | 1.5d |
| **Scenario 3 — High Amount Variance** | 5 variance tiers. Special case checks (15-50%): multi-period, multi-method, third-party → HOLD. Name must be ≥90%, else reroute to Sc4 | Router | 2d |
| **Scenario 4 — No Matching Customer** | Third-party check first (valid policy + third-party pattern + amount ≤15% → HOLD). Otherwise ESCALATE with best fuzzy match | Router | 1d |
| **Scenario 5 — Duplicate Payment** | 3 exact fields + $2 amount tolerance within 72hrs. Balance >0 → HOLD, balance =0 → ESCALATE. Capture duplicate_amount_difference | Router | 1d |
| **Persist layer** | `persist.py` — single DB transaction: INSERT recommendation (decision_attribution=UNSPECIFIED), UPDATE payment status + matched IDs, set investigation_due_date on ESCALATED, auto-apply ledger (INSERT payment_history + UPDATE policy balance), write RECOMMENDATION_MADE audit log | Scenarios | 1.5d |
| **Pipeline orchestrator** | `pipeline.py` — retry wrapper: 3 attempts (1s, 3s backoff). Retryable: DB timeouts, deadlocks, Claude API timeouts/rate limits. Non-retryable: constraint violations, validation errors. Exhausted → PROCESSING_FAILED | Persist | 1d |
| **POST `/api/payments/{id}/approve`** | Validate status=HELD. Transaction: HELD → APPLIED, INSERT payment_history, UPDATE policy balance, SET decision_attribution=HUMAN_CONFIRMED, audit log APPROVED + APPLIED | Pipeline | 1.5d |
| **POST `/api/payments/{id}/reject`** | Validate status=HELD. Transaction: HELD → ESCALATED, SET investigation_due_date, audit log ESCALATED | Approve | 0.5d |
| **POST `/api/payments/{id}/override`** | Validate actor role (ANALYST or INVESTIGATOR). Transaction: update payment status, ledger update if APPLIED, INSERT case_annotation (OVERRIDE_REASON), SET decision_attribution=HUMAN_OVERRIDE, audit log OVERRIDDEN | Reject | 1d |
| **POST `/api/payments/{id}/return`** | Investigator only. Transaction: ESCALATED/PENDING_SENDER_RESPONSE → RETURNED, audit log RETURNED | Override | 0.5d |
| **POST `/api/payments/{id}/reprocess`** | Validate status=PROCESSING_FAILED. Reset to RECEIVED, re-run full pipeline | Pipeline | 0.5d |
| **SLA service** | `sla.py` — compute investigation_due_date on escalation, background job to set sla_breached=true + write SLA_BREACHED audit log when deadline passes | Reject | 1d |

### Track B: Real APIs + Frontend Wire-up (Engineer B)

| Ticket | Description | Depends On | Est. |
|--------|-------------|------------|------|
| **GET `/api/payments`** | List with filters (status, scenario, date, search) + pagination. Sort by confidence_score, has_risk_flags, payment_method, payment_date | Phase 1 frontend | 1.5d |
| **GET `/api/payments/{id}`** | Full detail: payment + signals (incl. algorithm breakdown) + recommendation + audit trail + annotations + documents. Join across 6 tables | Phase 1 frontend | 1d |
| **Annotations endpoints** | `POST /api/payments/{id}/annotations` (CASE_NOTE, OVERRIDE_REASON, CONTACT_RECORD, INVESTIGATION_NOTE), `GET /api/payments/{id}/annotations` | Phase 1 frontend | 1d |
| **Documents endpoints** | `POST /api/payments/{id}/documents` (multipart), `GET /api/payments/{id}/documents`, `GET /api/payments/{id}/documents/{doc_id}` (stream), `DELETE /api/payments/{id}/documents/{doc_id}` (soft delete). Wire to `storage.py` (local FS for PoC) | Phase 1 frontend | 2d |
| **PENDING_SENDER_RESPONSE flow** | `POST /api/payments/{id}/annotations` with CONTACT_RECORD → triggers status update to PENDING_SENDER_RESPONSE. Damien can log outreach, system tracks SLA | Annotations | 1d |
| **Wire frontend to real APIs** | Replace all mock data in Queue Dashboard, Investigation Queue, Payment Detail, Settings with real API calls. Add loading states, error toasts, empty states | APIs + Phase 1 frontend | 2d |

**Exit criteria:** End-to-end flow works for all analyst/investigator actions (ingest → signals → route → recommend → approve/reject/override/return). Annotations and document upload working. Frontend connected to real APIs for all Priya and Damien pages.

---

## Phase 3: Director/Admin Pages + Governance/Analytics/Config APIs (Weeks 8–9)

### Track A: Governance, Analytics & Config APIs (Engineer A)

| Ticket | Description | Depends On | Est. |
|--------|-------------|------------|------|
| **GET `/api/analytics/decisions`** | Decision attribution breakdown — summary counts (auto-applied, human review, held, escalated by AI/human, overrides, returned), override rate %, payment method breakdown, per-scenario breakdown (volume, attribution, avg confidence, override count, decision distribution), confidence histogram (10 buckets). Powers both Lorraine's and Marcus's dashboards | Phase 2 | 2d |
| **GET `/api/analytics/overrides`** | Override analysis filterable by scenario, confidence band, date range, reason category. Powers Marcus's Override Analysis page | Decisions | 1d |
| **Governance endpoints** | `POST/GET /api/governance/reviews` (Lorraine records period review), `POST/GET /api/governance/anomalies` (Lorraine flags anomaly for Marcus), `PATCH /api/governance/anomalies/{id}` (Marcus updates investigation/resolution), `GET /api/governance/export` (audit-ready report, date range + scope) | Phase 2 | 2d |
| **Config change-request workflow** | `POST /api/settings/change-requests` (Marcus proposes), `GET /api/settings/change-requests`, `POST .../approve` (Lorraine), `POST .../reject` (Lorraine, mandatory comment), `POST .../deploy` (Marcus, creates ConfigurationThresholdVersion, updates active threshold atomically), `POST .../rollback` (emergency, requires Lorraine approval), `GET /api/settings/thresholds/history` | Phase 2 | 3d |

### Track B: Director/Admin Frontend Pages (Engineer B + Designer)

| Ticket | Owner | Description | Depends On | Est. |
|--------|-------|-------------|------------|------|
| **Governance Dashboard** | Engineer B + Designer | `/governance` — Lorraine's home. Metric cards (Auto-Applied by AI, Applied after Human Review, Held, Escalated by AI/Human, Human Overrides, Returned). Payment method breakdown chart. Override rate trend. SLA adherence. Confidence score histogram. Date range filter | Analytics API | 3d |
| **Compliance Export** | Engineer B + Designer | `/governance/export` — date range selector, export scope (decisions/overrides/config_changes/all), download structured report | Governance API | 1d |
| **Exception Dashboard** | Engineer B + Designer | `/governance/exceptions` — SLA-breached cases, anomaly flags (with status + resolution notes), config change requests pending Lorraine's approval/rejection | Governance API + Config API | 2d |
| **Admin Dashboard** | Engineer B + Designer | `/admin` — Marcus's home. Per-scenario analytics: case volume trend, decision distribution, override rate by confidence band, confidence score histogram | Analytics API | 2d |
| **Override Analysis** | Engineer B + Designer | `/admin/overrides` — filterable table (scenario, confidence band, date range, override reason category) | Analytics API | 1d |
| **Configuration Management** | Engineer B + Designer | `/admin/config` — current thresholds table, propose change form (parameter, current value, proposed value, rationale, projected impact), change request list with status tracking (PENDING/APPROVED/REJECTED/DEPLOYED/ROLLED_BACK), version history, deploy/rollback controls | Config API | 3d |

**Exit criteria:** All 10 frontend pages functional with real APIs. Config change-request workflow (propose → approve → deploy → rollback) working end-to-end. Governance and analytics dashboards showing real data.

---

## Phase 4: Integration & Polish (Week 10) — All Hands

| Ticket | Owner | Description |
|--------|-------|-------------|
| **E2E test: Scenario 1** | Engineer A | Strong match auto-apply + hold (ambiguous name, risk flags, high-risk method) |
| **E2E test: Scenario 2** | Engineer A | Single policy, amount disambiguates, ambiguous multi-policy |
| **E2E test: Scenario 3** | Engineer A | Each variance tier + multi-period + multi-method + third-party special cases |
| **E2E test: Scenario 4** | Engineer A | No match escalate + third-party hold |
| **E2E test: Scenario 5** | Engineer A | Exact duplicate, $2 tolerance, balance justifies, outside window |
| **E2E test: Analyst flows** | Engineer A | Approve, reject, override (APPLY and ESCALATE), reprocess. Verify decision_attribution set correctly |
| **E2E test: Investigator flows** | Engineer A | Return, log contact → PENDING_SENDER_RESPONSE, SLA breach detection |
| **E2E test: Config workflow** | Engineer A | Propose → approve → deploy → verify new payments use new threshold. Rollback → verify reverted |
| **E2E test: Retry & failure** | Engineer A | Simulate transient failures (DB timeout, Claude API timeout), verify 3 retries, PROCESSING_FAILED, reprocess |
| **Frontend integration testing** | Engineer B | Real API calls across all 10 pages, error states, empty states, loading spinners, role-gating (correct buttons per role) |
| **Analytics accuracy** | Engineer B | Verify decision attribution counts, override rate %, confidence histogram match actual data |
| **UI polish** | Designer + Engineer B | Responsive layout, empty states, error toasts, edge case screens, accessibility |

**Exit criteria:** All 5 scenarios tested end-to-end. All 4 persona flows verified (Priya, Damien, Lorraine, Marcus). Config change workflow tested. Analytics accurate. Frontend polished and responsive.

---

## Parallelization Summary

```
Week 1:   [================== Phase 0: Foundation (all hands) ==================]
                  Engineer A                         Engineer B + Designer
               ──────────────────             ──────────────────────────────────
Week 2:    Ingest endpoint                    API types + mock data
Week 3:    Signal Engine (Waves 1-2)          Queue Dashboard + Investigation Queue
Week 4:    Signal Engine (Wave 3) + Snapshot  Payment Detail + Settings

Week 5:    Scenario Router + Sc 1-2           GET /payments, GET /payments/{id}
Week 6:    Sc 3-5 + Persist + Pipeline        Annotations + Documents endpoints
Week 7:    Approve/Reject/Override/Return     Wire frontend to real APIs
           + SLA service

Week 8:    Analytics + Governance APIs        Governance Dashboard + Export
                                              + Exception Dashboard
Week 9:    Config change-request APIs         Admin Dashboard + Override Analysis
                                              + Configuration Management

Week 10:  [================== Phase 4: Integration & Polish (all hands) =========]
```

---

## Risk & Dependencies

| Risk | Mitigation |
|------|-----------|
| Claude API latency in pipeline | Retry wrapper handles transient issues; async calls prevent blocking |
| Gray-zone name matching accuracy | Haiku calls logged with both scores for tuning; gray zone bounds configurable |
| Frontend blocked on API contract | Mock data defined upfront from proto types; frontend never waits on backend |
| Complex scenario edge cases | Deterministic router is fully unit-testable in isolation; Final_Scenario_Definitions.md has worked examples |
| Config change workflow complexity | Change-request table + version history are fully defined in proto; workflow is linear (propose → approve → deploy) |
| Analytics query performance | Aggregation queries on large payment tables — add indexes on status, scenario_route, created_timestamp in Phase 3 |
| Role-gating correctness | Auth middleware enforces role at API level, not just UI; test each endpoint with wrong role in Phase 4 |

---

## Key Reference Documents

| Document | Purpose |
|----------|---------|
| `docs/architecture/00_Summary.md` | Architecture overview + user roles |
| `docs/architecture/01-07_*.md` | Detailed docs per pipeline stage |
| `docs/architecture/05_Human_Approval_Queue.md` | All 10 frontend pages across 4 roles |
| `docs/architecture/06_API_Reference.md` | All ~35 endpoints with request/response shapes |
| `docs/Final_Scenario_Definitions.md` | Authoritative decision logic with full examples |
| `docs/Step3_Feature_Signals.md` | All 19 signals with computation methods |
| `docs/Database_Design.md` | Proto-to-DB mapping, relationships, design notes |
| `proto/*.proto` | Source of truth for all data models (11 files) |
| `db/schema.sql` | PostgreSQL schema |

---

*End of Document*
