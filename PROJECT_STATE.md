# CES — Project State

**Last updated:** 2026-04-25  
**Current phase:** Phase 1 in progress — Signal Engine (Waves 1–3) + TypeScript types + mocks complete; CES-11, CES-13 next  
**Repository:** https://github.com/na1in/CES-POC  
**Team:** 2 Engineers (A & B) + 1 Designer

---

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| **Phase 0 — Foundation** | ✅ Complete | DB schema, protos, docs, scaffold all done |
| **Phase 1 — Core Pipeline + Frontend Shell** | 🔄 In progress | CES-7–CES-10 (backend), CES-12 (frontend types + mocks) done; CES-11, CES-13 next |
| **Phase 2 — AI Agent + Real APIs** | ⬜ Not started | Weeks 5–6 |
| **Phase 3 — Integration & Polish** | ⬜ Not started | Week 7 |

---

## What's Built

### Foundation
- [x] `db/schema.sql` — complete PostgreSQL schema (all tables, enums, indexes)
- [x] `proto/*.proto` — all 11 proto files (source of truth for data models)
- [x] `backend/app/main.py` — FastAPI skeleton with `/health` endpoint
- [x] `backend/app/config.py` — Pydantic settings (DATABASE_URL, ANTHROPIC_API_KEY)
- [x] `backend/requirements.txt` — fastapi, uvicorn, sqlalchemy, asyncpg, anthropic, pydantic-settings
- [x] `frontend/` — Next.js + Tailwind scaffold (default page only)
- [x] `docs/` — full specification docs

### Documentation
- [x] `docs/Final_Scenario_Definitions.md` — authoritative decision logic for all 5 scenarios
- [x] `docs/Step3_Feature_Signals.md` — all 19 signals with computation methods
- [x] `docs/architecture/00-07` — architecture docs per pipeline stage
- [x] `docs/scenarios/Scenario_1-5` — per-scenario decision logic and edge cases
- [x] `docs/Implementation_Plan.md` — phased plan with tickets and estimates
- [x] `docs/Personas.pdf` — 4 user personas (Priya, Damien, Lorraine, Marcus)
- [x] `docs/User Flow.pdf` — 4 detailed user flows with alt paths and error states
- [x] `docs/user-flow-diagram.pdf` — cross-role flow diagram

### Phase 1 — Core Pipeline (Engineer A)
- [x] `backend/app/db.py` — async SQLAlchemy session management (NullPool for tests)
- [x] `backend/app/routers/payments.py` — `POST /api/payments/ingest` (CES-7)
- [x] `backend/app/services/ingest.py` — Claude Haiku reference parsing with fallback (CES-7)
- [x] `backend/app/services/signals/matching.py` — hybrid name matching + policy/customer confidence (CES-8, CES-9)
- [x] `backend/app/services/signals/amount.py` — variance, historical consistency, multi-period, multi-method, third-party (CES-8, CES-10)
- [x] `backend/app/services/signals/temporal.py` — timing quality, days since last payment (CES-8)
- [x] `backend/app/services/signals/duplicate.py` — 72hr duplicate detection with $2 tolerance (CES-8)
- [x] `backend/app/services/signals/risk.py` — risk flags, account status, balance snapshot, payment method risk, supporting signals (CES-10)
- [x] `backend/tests/` — full test suite (77 tests across waves 1–3, all passing)

### Phase 1 — Frontend (Engineer B + Designer)
- [x] `frontend/src/types/payment.ts` — PaymentStatus, PaymentMethod, Payment
- [x] `frontend/src/types/signals.ts` — PaymentSignals, MatchingSignals, AmountSignals, TemporalSignals, RiskSignals, DuplicateSignals + enums
- [x] `frontend/src/types/recommendation.ts` — PaymentRecommendation, Recommendation, ScenarioRoute, DecisionAttribution
- [x] `frontend/src/types/annotation.ts` — CaseAnnotation, AnnotationType
- [x] `frontend/src/types/document.ts` — CaseDocument, DocumentType
- [x] `frontend/src/types/user.ts` — User, UserRole, AuditLogEntry, AuditActionType, ConfigurationThreshold
- [x] `frontend/src/mocks/payments.ts` — 8 mock payments covering all 5 scenarios + processing_failed + sla_breached, with full signals, recommendations, annotations, and audit logs (CES-12)

---

## What's NOT Built Yet

### Backend — Phase 1 (Engineer A)
- [ ] Signal snapshot — persist all 19 signals to `payment_signals`, write SIGNALS_COMPUTED audit log (CES-11)
- [ ] `backend/app/services/storage.py` — document storage abstraction
- [ ] `backend/app/services/sla.py` — SLA deadline computation and breach detection

### Backend — Phase 2 (Engineer A)
- [ ] Scenario Router (`router.py`) — deterministic if/else routing
- [ ] Scenarios 1–5 (`agent/scenarios/`) — Claude API prompts + output parsing
- [ ] Persist layer (`persist.py`) — single transaction, sets `decision_attribution`
- [ ] Pipeline orchestrator (`pipeline.py`) — retry wrapper (3 attempts, 1s/3s backoff)

### API Endpoints — Phase 2 (Engineer B)
- [ ] `GET /api/payments` with full filter/sort support (incl. payment_method, confidence_score)
- [ ] `GET /api/payments/{id}` — full detail with signals, recommendation, audit, annotations, documents
- [ ] `POST /api/payments/{id}/approve`
- [ ] `POST /api/payments/{id}/reject`
- [ ] `POST /api/payments/{id}/override` — mandatory reason field
- [ ] `POST /api/payments/{id}/return`
- [ ] `POST /api/payments/{id}/reprocess`
- [ ] `POST /api/payments/{id}/annotations`
- [ ] `GET /api/payments/{id}/annotations`
- [ ] `POST /api/payments/{id}/documents`
- [ ] `GET /api/payments/{id}/documents`
- [ ] `GET /api/payments/{id}/documents/{doc_id}`
- [ ] `DELETE /api/payments/{id}/documents/{doc_id}`
- [ ] `GET /api/analytics/decisions`
- [ ] `GET /api/analytics/overrides`
- [ ] Config change request workflow (`/api/settings/change-requests/*`)
- [ ] `GET /api/settings/thresholds/history`
- [ ] Governance endpoints (`/api/governance/*`)

### Frontend — Phase 1 (Engineer B + Designer)
- [x] TypeScript types from proto definitions (CES-12 ✅)
- [x] Mock API responses for all endpoints (CES-12 ✅)
- [ ] Queue Dashboard (`/`) — Priya, sorted by confidence score, includes payment_method column
- [ ] Investigation Queue (`/investigations`) — Damien, escalated only, risk-sorted
- [ ] Payment Detail (`/payments/[id]`) — signals with algorithm breakdown, annotation panel, document upload
- [ ] Settings (`/settings`) — threshold viewer, change request flow for admin

### Frontend — Phase 2 (Engineer B + Designer)
- [ ] Governance Dashboard (`/governance`) — Lorraine's metric cards + payment method breakdown chart
- [ ] Compliance Export (`/governance/export`)
- [ ] Exception Dashboard (`/governance/exceptions`)
- [ ] Admin Dashboard (`/admin`) — Marcus's per-scenario analytics
- [ ] Override Analysis (`/admin/overrides`)
- [ ] Configuration Management (`/admin/config`) — change request form, version history, simulation

---

## Key Design Decisions (Locked)

| Decision | Value | Rationale |
|----------|-------|-----------|
| Monetary amounts | Integers in cents (BIGINT) | Never floats |
| ID format | `PMT-XXX`, `CUST-XXXX`, `POL-XXXXX`, `USR-XXXX` | Prefixed for readability |
| Proto files | Source of truth | Schema and models derive from protos |
| DB operations | Always in transactions | Consistency guarantee |
| Postgres enums | lowercase snake_case | e.g., `fraud_history` not `FRAUD_HISTORY` |
| Thresholds | Stored in DB, never hardcoded | Tunable without code deploy |
| Name matching | Hybrid: deterministic + Haiku for 70–92% gray zone | Full algorithm breakdown stored |
| Override reason | Mandatory (form blocks submit without it) | Marcus's feedback loop + audit |
| Document storage | Object storage (local FS for PoC, S3-compatible interface) | Swap with one config change |
| Decision attribution | Set at case closure in `persist.py` | Lorraine's AI vs human metrics |
| Config changes | Require formal change request + Lorraine approval | Separation of duties (compliance) |
| Scenario 5 | Always runs first on every payment | Duplicate check before any other routing |
| Update order | protos → schema → scenario docs → architecture docs → reference docs | Maintain consistency |

---

## Open Questions

| Question | Owner | Priority |
|----------|-------|----------|
| Does "Hold requires approval" mean a peer analyst reviews, or does Priya hold and await system timeout? | PM | High — affects approval flow design |
| Is there a defined SLA for Damien's investigation queue? Who sets it — Lorraine or ops policy? | PM | High — needed before `sla.py` is built |
| In the PoC, is Marcus a dedicated role or a senior analyst wearing two hats? | PM | Medium — affects role seeding in DB |
| What is the notification channel for policyholder outreach — in-system template, email, or phone only? | PM | Medium — affects contact record model |
| Does the staging/simulation environment use anonymised production data or synthetic data? | Engineering | Medium — affects `sla.py` and back-test scope |
| ~~Does `jellyfish` need to be added to `requirements.txt`?~~ | ~~Engineer A~~ | ~~Resolved — jellyfish added and in use~~ |

---

## Phase 0 Exit Criteria (All Met)

- [x] DB schema complete with all tables, enums, indexes
- [x] All 11 proto files complete and consistent with schema
- [x] FastAPI app starts (`/health` returns 200)
- [x] All specification docs reviewed and in `/docs`
- [x] User personas and flows documented
- [x] Designer has wireframe reference (`docs/architecture/05_Human_Approval_Queue.md`)

## Phase 1 Entry Checklist

Before Engineer A starts the ingest endpoint:
- [ ] PostgreSQL instance running with `schema.sql` applied
- [ ] `configuration_thresholds` table seeded with defaults (see CLAUDE.md thresholds table)
- [ ] Test customers, policies, and payment history seeded
- [ ] `ANTHROPIC_API_KEY` set in `.env`
- [ ] `jellyfish` added to `requirements.txt`
- [ ] Proto Python classes generated from `proto/`

---

## Dependencies Between Tracks (Phase 1)

```
Engineer A                          Engineer B + Designer
──────────────────────              ──────────────────────────────
Ingest endpoint                     API types + mock data  (parallel)
Signal Engine Wave 1+2              Queue Dashboard + Payment List  (parallel)
Signal Engine Wave 3 + snapshot     Payment Detail + Settings  (parallel)
```

Frontend never waits for backend — mock data defined upfront from proto types.
