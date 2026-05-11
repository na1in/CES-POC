# CES — Project State

**Last updated:** 2026-05-11  
**Current phase:** Phase 2 complete (backend) · Phase 3 starting  
**Repository:** https://github.com/na1in/CES-POC  
**Branch:** `nalin-dev` (open PR #9 against main)  
**Team:** 2 Engineers (A & B) + 1 Designer

---

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| **Phase 0 — Foundation** | ✅ Complete | DB schema, protos, docs, scaffold, auth, seed data |
| **Phase 1 — Core Pipeline + Frontend Shell** | ✅ Complete | Ingest → signals → snapshot (backend); Queue/Detail/Settings pages (frontend) |
| **Phase 2 — AI Agent + Analyst/Investigator APIs** | ✅ Backend complete · 🔄 Frontend wire-up pending | All backend APIs live; Praneetha wiring frontend to real APIs |
| **Phase 3 — Director/Admin + Governance/Analytics/Config APIs** | ⬜ Not started | Next up for Engineer A |
| **Phase 4 — Integration & Polish** | ⬜ Not started | Week 10 |

---

## What's Built

### Foundation (Phase 0)
- [x] `db/schema.sql` — complete PostgreSQL schema (all tables, enums, indexes)
- [x] `proto/*.proto` — all 11 proto files (source of truth for data models)
- [x] `backend/app/main.py` — FastAPI app with JWT auth, role guards, health check
- [x] `backend/app/auth.py` — JWT + `require_roles()` dependency factory; Priya/Damien/Lorraine/Marcus role guards
- [x] `backend/app/config.py` — Pydantic settings (DATABASE_URL, ANTHROPIC_API_KEY, JWT_SECRET_KEY)
- [x] `backend/requirements.txt` — fastapi, uvicorn, sqlalchemy, asyncpg, anthropic, jellyfish, python-jose, alembic
- [x] Docker Compose + Alembic migrations + idempotent seed data
- [x] `docs/` — all specification, architecture, scenario, and implementation docs

### Phase 1 — Backend Pipeline (Engineer A) ✅
- [x] `backend/app/routers/payments.py` — `POST /api/payments/ingest` (CES-7)
- [x] `backend/app/services/ingest.py` — Claude Haiku reference parsing with fallback (CES-7)
- [x] `backend/app/services/signals/matching.py` — hybrid name matching + policy/customer confidence (CES-8, CES-9)
- [x] `backend/app/services/signals/amount.py` — variance, historical consistency, multi-period, multi-method, third-party (CES-8, CES-10)
- [x] `backend/app/services/signals/temporal.py` — timing quality, days since last payment (CES-8)
- [x] `backend/app/services/signals/duplicate.py` — 72hr duplicate detection with $2 tolerance (CES-8)
- [x] `backend/app/services/signals/risk.py` — risk flags, account status, balance snapshot, payment method risk, supporting signals (CES-10)
- [x] `backend/app/services/signal_engine.py` — 3-wave orchestrator + snapshot to `payment_signals` (CES-11)
- [x] 77 unit tests across signal waves; all passing without DB

### Phase 1 — Frontend Shell (Engineer B + Designer) ✅
- [x] TypeScript types from all 11 proto definitions (CES-12)
- [x] Mock API responses for all analyst/investigator endpoints (CES-12)
- [x] Queue Dashboard `/` — sorted by confidence score, payment method column, scenario filter (CES-13)
- [x] Investigation Queue `/investigations` — escalated cases, risk-sorted, SLA breach indicator (CES-14)
- [x] Payment Detail `/payments/[id]` — signals panel, reasoning, audit timeline, action buttons, annotations, documents (CES-15)
- [x] Settings `/settings` — threshold viewer, read-only for non-admin (CES-16)

### Phase 2 — AI Agent + Persist + Pipeline (Engineer A) ✅
- [x] `backend/app/services/agent/router.py` — deterministic scenario routing: S5→S4→S3→S1→S2 (CES-17)
- [x] `backend/app/services/agent/scenarios/sc1.py` — Strong Policy Match (CES-18)
- [x] `backend/app/services/agent/scenarios/sc2.py` — Customer Match, No Policy (CES-19)
- [x] `backend/app/services/agent/scenarios/sc3.py` — High Amount Variance, 5 tiers (CES-20)
- [x] `backend/app/services/agent/scenarios/sc4.py` — No Matching Customer (CES-21)
- [x] `backend/app/services/agent/scenarios/sc5.py` — Duplicate Payment (CES-22)
- [x] `backend/app/services/agent/reasoning.py` — shared Claude Sonnet wrapper with fallback
- [x] `backend/app/services/persist.py` — single-transaction save; auto-apply ledger; `_target_status()` (CES-23)
- [x] `backend/app/services/pipeline.py` — 3-attempt retry orchestrator; `_mark_failed()` (CES-24)

### Phase 2 — Analyst/Investigator APIs (Engineer A + B) ✅
- [x] `backend/app/routers/approvals.py` — approve, reject, override, return, reprocess (CES-25/26)
- [x] `backend/app/routers/payments.py` — `GET /api/payments` (filtered/paginated list) + `GET /api/payments/{id}` (full detail, signals grouped by category) (CES-28)
- [x] `backend/app/routers/annotations.py` — POST/GET annotations; contact_record → pending_sender_response (CES-29/31)
- [x] `backend/app/routers/documents.py` — multipart upload, list, stream, soft delete (CES-30)
- [x] `backend/app/services/storage.py` — local FS abstraction (UPLOAD_DIR env, MIME allowlist, 20MB cap) (CES-30)
- [x] `backend/app/services/sla.py` — `compute_due_date()`, `check_and_mark_breaches()`, asyncio background monitor (CES-27)
- [x] 176 unit tests total; all passing without DB

### Phase 2 — Frontend Wire-up (Engineer B) 🔄 In Progress
- [x] Governance Dashboard `/governance` — Lorraine's metrics (CES-34/36) [built with mock data]
- [x] Compliance Export `/governance/export` (CES-35) [built with mock data]
- [x] Exception Dashboard `/governance/exceptions` (CES-36) [built with mock data]
- [x] Admin Dashboard `/admin` (CES-37) [built with mock data]
- [x] Override Analysis `/admin/overrides` (CES-38) [built with mock data]
- [x] Configuration Management `/admin/config` (CES-39) [built with mock data]
- [ ] Wire analyst/investigator pages to real APIs (replace mock data in Queue, Detail, Investigations, Settings)

---

## What's NOT Built Yet

### Phase 3 — Governance/Analytics/Config APIs (Engineer A)
- [ ] `GET /api/analytics/decisions` — attribution counts, method breakdown, per-scenario breakdown, confidence histogram
- [ ] `GET /api/analytics/overrides` — filterable by scenario, confidence band, date, reason category
- [ ] `POST/GET /api/governance/reviews` — Lorraine period review log
- [ ] `POST/GET /api/governance/anomalies` + `PATCH .../anomalies/{id}` — anomaly flag workflow
- [ ] `GET /api/governance/export` — audit-ready report (date range + scope)
- [ ] `POST /api/settings/change-requests` + full workflow (approve/reject/deploy/rollback)
- [ ] `GET /api/settings/thresholds/history`

### Phase 3 — Director/Admin Frontend Wire-up (Engineer B)
- [ ] Wire Governance Dashboard, Exception Dashboard, Admin Dashboard, Override Analysis, Config Management to real APIs

### Phase 4 — Integration & Polish
- [ ] E2E tests for all 5 scenarios + analyst/investigator/config flows
- [ ] Frontend integration testing across all 10 pages
- [ ] UI polish, accessibility, empty/error states

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
| Override reason | Mandatory (form blocks submit) | Marcus's feedback loop + audit |
| Document storage | Local FS for PoC (`UPLOAD_DIR`), S3-compatible interface | Swap with one config change |
| Decision attribution | Set at case closure in `persist.py` | Lorraine's AI vs human metrics |
| Config changes | Require formal change request + Lorraine approval | Separation of duties (compliance) |
| Scenario 5 | Always runs first on every payment | Duplicate check before any routing |
| Update order | protos → schema → scenario docs → architecture docs → reference docs | Maintain consistency |
| SLA default | 72 hours (`_SLA_HOURS` in `persist.py`) | Imported by approvals.py and sla.py |
| contact_record annotation | Transitions escalated → pending_sender_response | SLA timer starts at first contact log |

---

## Open Questions (Resolved + Outstanding)

| Question | Status |
|----------|--------|
| Does "Hold requires approval" mean peer analyst review or system timeout? | **Resolved:** Priya approves HELD → APPLIED or rejects HELD → ESCALATED. No peer review. |
| Is there a defined SLA for Damien's investigation queue? | **Resolved:** 72 hours, configurable via `_SLA_HOURS`. Breach detection runs every 60s in background. |
| Is Marcus a dedicated admin role or senior analyst? | **Resolved for PoC:** dedicated `admin` role (USR-0004) |
| Notification channel for policyholder outreach? | **Open** — contact_record model logs phone/email/letter; no notification service built |
| Staging environment — anonymised production or synthetic data? | **Open** — PoC uses synthetic seed data only |

---

## Developer Setup

```bash
git clone https://github.com/na1in/CES-POC
cd CES-POC
cp backend/.env.example backend/.env
# Add ANTHROPIC_API_KEY to backend/.env
make setup        # installs deps + starts Docker Postgres + migrates + seeds
make proto        # compile proto files → backend/app/proto_gen/
make dev          # FastAPI on :8000
make dev-frontend # Next.js on :3000 (separate terminal)
```

Test users (password not checked in PoC — use user_id as username):

| User ID | Name | Role |
|---------|------|------|
| USR-0001 | Priya Sharma | analyst |
| USR-0002 | Damien Torres | investigator |
| USR-0003 | Lorraine Chen | director |
| USR-0004 | Marcus Webb | admin |

Run tests (no DB required for pure-helper tests):
```bash
cd backend && python -m pytest tests/ -v
# 176 pass; 1 expected DB-integration error (needs Postgres running)
```
