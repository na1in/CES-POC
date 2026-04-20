# CES — Project Status

> **How to use this doc**  
> Update your ticket's status emoji and add a short note when you pick something up, hit a blocker, or finish. Keep it current — this is the team's single source of truth.  
> Status key: ✅ Done · 🔄 In Progress · 🚫 Blocked · ⬜ Not Started

---

## Overview

| Field | Value |
|-------|-------|
| **Repo** | https://github.com/na1in/CES-POC |
| **Current week** | Week 1 |
| **Active phase** | Phase 0 complete → Phase 1 starting |
| **Last updated** | 2026-04-18 |

## Team

| Role | Name | Tracks |
|------|------|--------|
| PM | Nalin | Coordination, Linear, this doc |
| Engineer A | — | Backend pipeline, AI agent, DB |
| Engineer B | — | Frontend, read APIs, docs/annotations |
| Designer | — | Figma designs for all 10 pages |

---

## Phase Summary

| Phase | Weeks | Focus | Status |
|-------|-------|-------|--------|
| **Phase 0 — Foundation** | 1 | DB, protos, FastAPI skeleton, frontend scaffold | ✅ Done |
| **Phase 1 — Core Pipeline + Frontend Shell** | 2–4 | Ingest → signals, analyst/investigator pages | ⬜ Not Started |
| **Phase 2 — AI Agent + Analyst APIs** | 5–7 | Scenarios 1–5, approve/reject/override, wire frontend | ⬜ Not Started |
| **Phase 3 — Director/Admin + Governance APIs** | 8–9 | All remaining pages + analytics/config APIs | ⬜ Not Started |
| **Phase 4 — Integration & Polish** | 10 | E2E tests, role-gating, UI polish | ⬜ Not Started |

---

## Phase 0 — Foundation ✅ Complete

### What was delivered

| Ticket | Owner | Status | Notes |
|--------|-------|--------|-------|
| PostgreSQL setup + `schema.sql` applied | Eng A | ✅ | Docker Compose — `docker compose up -d` |
| Alembic migrations (versioned, async) | Eng A | ✅ | `make migrate` runs `alembic upgrade head` |
| Seed data (users, customers, policies, thresholds) | Eng A | ✅ | `make seed` — idempotent, safe to re-run |
| Proto compilation pipeline | Eng A | ✅ | `make proto` — uses system `protoc` |
| Python classes generated from 11 protos | Eng A | ✅ | Output: `backend/app/proto_gen/proto/` |
| FastAPI skeleton — DB session, auth middleware | Eng A | ✅ | `app/database.py`, `app/auth.py`, JWT + role guards |
| `requirements.txt` complete | Eng A | ✅ | All deps incl. jellyfish, python-jose, alembic |
| Next.js + Tailwind v4 scaffold | Eng B | ✅ | |
| shadcn/ui initialized (Tailwind v4 compatible) | Eng B | ✅ | Button, Card, Badge, Table, Separator in `src/components/ui/` |
| All 11 `.proto` files authored | PM / Eng A | ✅ | Source of truth for all data models |
| All architecture + scenario docs | PM | ✅ | `docs/architecture/`, `docs/scenarios/` |
| Figma — Analyst & Investigator pages | Designer | ⬜ | 4 pages: Queue, Investigations, Detail, Settings |
| Figma — Director & Admin pages | Designer | ⬜ | 6 pages: Governance, Export, Exceptions, Admin, Overrides, Config |

### Phase 0 exit checklist
- [x] DB running with test data
- [x] FastAPI app starts + `/health` returns 200
- [x] Proto classes generated
- [x] `ANTHROPIC_API_KEY` slot in `.env`
- [ ] Figma designs reviewed and approved ← **blocking designer**

---

## Phase 1 — Core Pipeline + Frontend Shell (Weeks 2–4)

### Track A: Backend Pipeline (Engineer A)

| Ticket | Est | Status | Owner | Notes |
|--------|-----|--------|-------|-------|
| **Ingest endpoint** `POST /api/payments/ingest` — validate fields, call Claude API to parse free-text refs (policy #, intent, period count), generate PMT-XXX ID, INSERT as RECEIVED, write RECEIVED audit log | 3d | ⬜ | Eng A | |
| **Signal Wave 1** — name similarity (hybrid: jaro-winkler + levenshtein + soundex → deterministic, then Haiku for 70–92% gray zone), amount variance, timing quality, duplicate check (3 exact + $2 tolerance / 72hr window) | 4d | ⬜ | Eng A | |
| **Signal Wave 2** — policy match confidence, customer match confidence, over/underpayment, historical consistency (z-score) | 3d | ⬜ | Eng A | Depends on Wave 1 |
| **Signal Wave 3** — risk flags, account status, balance snapshot, payment method risk, supporting signals (account/amount/historical match), multi-period indicator, multi-method indicator, third-party indicator | 3d | ⬜ | Eng A | Depends on Wave 2 |
| **Signal snapshot** — persist all 19 signals to `payment_signals`, write SIGNALS_COMPUTED audit log | 1d | ⬜ | Eng A | Depends on all waves |

### Track B: Analyst/Investigator Frontend Shell (Engineer B + Designer)

| Ticket | Est | Status | Owner | Notes |
|--------|-----|--------|-------|-------|
| **TypeScript types** from all proto definitions + mock API responses for all analyst/investigator endpoints | 2d | ⬜ | Eng B | Unblocked — run parallel with Track A |
| **Queue Dashboard** `/` — open cases sorted by AI confidence score (lowest first); columns: scenario, sender, amount, payment method, AI rec, confidence band, age; filters: scenario, confidence, method; PROCESSING_FAILED alert | 2d | ⬜ | Eng B + Designer | Depends on TS types |
| **Investigation Queue** `/investigations` — Damien's home; escalated cases sorted by risk level; columns: sender, amount, risk indicator, method, time since escalation; SLA breach warning | 2d | ⬜ | Eng B + Designer | Depends on TS types |
| **Payment Detail** `/payments/[id]` — payment info (incl. method), signal bars with algorithm breakdown, AI reasoning panel, audit timeline, annotation panel (add/view), document panel (upload/list); role-gated action buttons | 4d | ⬜ | Eng B + Designer | Depends on TS types |
| **Settings** `/settings` — threshold viewer (read-only for non-admin), admin link to change-request flow | 1d | ⬜ | Eng B + Designer | Depends on TS types |

**Phase 1 exit criteria:**
- [ ] Full pipeline: ingest → signal snapshot works end-to-end
- [ ] Queue Dashboard, Investigation Queue, Payment Detail, Settings built with mock data

---

## Phase 2 — AI Agent + Analyst/Investigator APIs (Weeks 5–7)

### Track A: AI Agent + Persist + Action APIs (Engineer A)

| Ticket | Est | Status | Owner | Notes |
|--------|-----|--------|-------|-------|
| **Scenario Router** `router.py` — Sc5 first (duplicate), then Sc1–4: policy ref + name ≥75% + variance ≤2% → Sc1; no policy + customer match → Sc2; variance >2% → Sc3; all fail → Sc4 | 2d | ⬜ | Eng A | Pure Python, unit-testable |
| **Scenario 1** — Strong Policy Match: Claude API prompt, auto-apply (name >90%, no risk flags, active policy, low-risk method) vs hold | 1.5d | ⬜ | Eng A | |
| **Scenario 2** — Customer Match, No Policy: single policy → APPLY w/ approval; ambiguous → HOLD; reroute to Sc3 if variance >15% | 1.5d | ⬜ | Eng A | |
| **Scenario 3** — High Amount Variance: 5 tiers; special cases 15–50% (multi-period, multi-method, third-party → HOLD); name must be ≥90% else → Sc4 | 2d | ⬜ | Eng A | |
| **Scenario 4** — No Matching Customer: third-party check first (valid policy + pattern + amount ≤15% → HOLD); else ESCALATE with best fuzzy match | 1d | ⬜ | Eng A | |
| **Scenario 5** — Duplicate Payment: 3 exact + $2 tolerance + 72hr window; balance >0 → HOLD, =0 → ESCALATE | 1d | ⬜ | Eng A | |
| **Persist layer** `persist.py` — single transaction: INSERT recommendation, UPDATE payment status + matched IDs, SET investigation_due_date on ESCALATED, auto-apply ledger, write RECOMMENDATION_MADE audit log | 1.5d | ⬜ | Eng A | |
| **Pipeline orchestrator** `pipeline.py` — 3-retry wrapper (1s, 3s backoff); retryable: DB/Claude timeouts, deadlocks; not retryable: constraint violations; → PROCESSING_FAILED | 1d | ⬜ | Eng A | |
| **`POST /api/payments/{id}/approve`** — HELD → APPLIED, ledger update, decision_attribution = HUMAN_CONFIRMED | 1.5d | ⬜ | Eng A | |
| **`POST /api/payments/{id}/reject`** — HELD → ESCALATED, set investigation_due_date | 0.5d | ⬜ | Eng A | |
| **`POST /api/payments/{id}/override`** — update status, ledger if APPLIED, INSERT override_reason annotation, decision_attribution = HUMAN_OVERRIDE | 1d | ⬜ | Eng A | |
| **`POST /api/payments/{id}/return`** — Investigator only; → RETURNED | 0.5d | ⬜ | Eng A | |
| **`POST /api/payments/{id}/reprocess`** — PROCESSING_FAILED → RECEIVED, re-run pipeline | 0.5d | ⬜ | Eng A | |
| **SLA service** `sla.py` — compute investigation_due_date on escalation; background job sets sla_breached + writes SLA_BREACHED audit log | 1d | ⬜ | Eng A | |

### Track B: Real APIs + Frontend Wire-up (Engineer B)

| Ticket | Est | Status | Owner | Notes |
|--------|-----|--------|-------|-------|
| **`GET /api/payments`** — filters (status, scenario, date, search), pagination, sort by confidence_score / has_risk_flags / payment_method | 1.5d | ⬜ | Eng B | |
| **`GET /api/payments/{id}`** — full detail: payment + signals (incl. algorithm breakdown) + recommendation + audit trail + annotations + documents | 1d | ⬜ | Eng B | |
| **Annotations endpoints** — `POST/GET /api/payments/{id}/annotations` (case_note, override_reason, contact_record, investigation_note) | 1d | ⬜ | Eng B | |
| **Documents endpoints** — upload (multipart), list, stream download, soft delete; wire to `storage.py` | 2d | ⬜ | Eng B | |
| **PENDING_SENDER_RESPONSE flow** — CONTACT_RECORD annotation triggers status update; Damien logs outreach, SLA tracked | 1d | ⬜ | Eng B | |
| **Wire frontend to real APIs** — replace mock data in all 4 analyst/investigator pages; add loading, error, empty states | 2d | ⬜ | Eng B | Depends on real APIs + Phase 1 frontend |

**Phase 2 exit criteria:**
- [ ] End-to-end: ingest → signals → route → recommend → approve/reject/override/return
- [ ] Annotations + document upload working
- [ ] Frontend connected to real APIs for all Priya + Damien pages

---

## Phase 3 — Director/Admin Pages + Governance/Analytics/Config APIs (Weeks 8–9)

### Track A: Analytics, Governance & Config APIs (Engineer A)

| Ticket | Est | Status | Owner | Notes |
|--------|-----|--------|-------|-------|
| **`GET /api/analytics/decisions`** — summary counts, override rate %, payment method breakdown, per-scenario breakdown, confidence histogram (10 buckets) | 2d | ⬜ | Eng A | |
| **`GET /api/analytics/overrides`** — filterable by scenario, confidence band, date, reason category | 1d | ⬜ | Eng A | |
| **Governance endpoints** — `POST/GET /api/governance/reviews`, `POST/GET /api/governance/anomalies`, `PATCH /api/governance/anomalies/{id}`, `GET /api/governance/export` | 2d | ⬜ | Eng A | |
| **Config change-request workflow** — propose → approve → reject → deploy (creates ThresholdVersion, atomically updates active) → rollback → history | 3d | ⬜ | Eng A | |

### Track B: Director/Admin Frontend (Engineer B + Designer)

| Ticket | Est | Status | Owner | Notes |
|--------|-----|--------|-------|-------|
| **Governance Dashboard** `/governance` — metric cards (Auto-Applied, Human Review, Held, Escalated AI/Human, Overrides, Returned); payment method chart; override rate trend; SLA adherence; confidence histogram; date filter | 3d | ⬜ | Eng B + Designer | |
| **Compliance Export** `/governance/export` — date range, export scope, download | 1d | ⬜ | Eng B + Designer | |
| **Exception Dashboard** `/governance/exceptions` — SLA-breached cases, anomaly flags, pending config approvals | 2d | ⬜ | Eng B + Designer | |
| **Admin Dashboard** `/admin` — per-scenario: volume trend, decision distribution, override rate by confidence band, confidence histogram | 2d | ⬜ | Eng B + Designer | |
| **Override Analysis** `/admin/overrides` — filterable table (scenario, confidence band, date, reason) | 1d | ⬜ | Eng B + Designer | |
| **Configuration Management** `/admin/config` — thresholds table, propose form, change request list (PENDING/APPROVED/REJECTED/DEPLOYED/ROLLED_BACK), version history, deploy/rollback controls | 3d | ⬜ | Eng B + Designer | |

**Phase 3 exit criteria:**
- [ ] All 10 frontend pages functional with real APIs
- [ ] Config change-request workflow (propose → approve → deploy → rollback) works end-to-end
- [ ] Governance + analytics dashboards showing real data

---

## Phase 4 — Integration & Polish (Week 10)

| Ticket | Owner | Status | Notes |
|--------|-------|--------|-------|
| E2E test: Scenario 1 — auto-apply + hold (ambiguous name, risk flags, high-risk method) | Eng A | ⬜ | |
| E2E test: Scenario 2 — single policy, amount disambiguates, ambiguous multi-policy | Eng A | ⬜ | |
| E2E test: Scenario 3 — each variance tier + multi-period + multi-method + third-party | Eng A | ⬜ | |
| E2E test: Scenario 4 — no match escalate + third-party hold | Eng A | ⬜ | |
| E2E test: Scenario 5 — exact duplicate, $2 tolerance, balance justifies, outside window | Eng A | ⬜ | |
| E2E test: Analyst flows — approve, reject, override (APPLY + ESCALATE), reprocess; verify decision_attribution | Eng A | ⬜ | |
| E2E test: Investigator flows — return, log contact → PENDING_SENDER_RESPONSE, SLA breach | Eng A | ⬜ | |
| E2E test: Config workflow — propose → approve → deploy → verify new threshold; rollback → verify reverted | Eng A | ⬜ | |
| E2E test: Retry + failure — simulate DB/Claude timeouts, verify 3 retries, PROCESSING_FAILED, reprocess | Eng A | ⬜ | |
| Frontend integration — real APIs across all 10 pages, error states, empty states, loading, role-gating | Eng B | ⬜ | |
| Analytics accuracy — verify decision attribution counts, override rate %, confidence histogram | Eng B | ⬜ | |
| UI polish — responsive layout, empty states, error toasts, edge case screens, accessibility | Designer + Eng B | ⬜ | |

---

## Open Questions

| # | Question | Owner | Priority | Status |
|---|----------|-------|----------|--------|
| 1 | Does "Hold requires approval" mean a peer analyst reviews, or does Priya hold and await system timeout? | PM | 🔴 High | Open — affects approval flow |
| 2 | Is there a defined SLA for Damien's investigation queue? Who sets it — Lorraine or ops policy? | PM | 🔴 High | Open — needed before `sla.py` |
| 3 | In the PoC, is Marcus a dedicated admin role or a senior analyst with two hats? | PM | 🟡 Medium | Open — affects role seeding |
| 4 | Notification channel for policyholder outreach — in-system template, email, or phone only? | PM | 🟡 Medium | Open — affects contact record model |
| 5 | Staging/simulation environment — anonymised production data or synthetic data only? | Eng A | 🟡 Medium | Open |

---

## Key Design Decisions (Locked — do not change without team sign-off)

| Decision | Value |
|----------|-------|
| Monetary amounts | Integers in cents (BIGINT) — never floats |
| ID format | `PMT-XXX`, `CUST-XXXX`, `POL-XXXXX`, `USR-XXXX` |
| Proto files | Source of truth — schema and models derive from protos |
| DB operations | Always in transactions |
| Postgres enums | lowercase snake_case |
| Thresholds | Stored in DB, never hardcoded |
| Name matching | Hybrid: deterministic + Haiku for 70–92% gray zone; full breakdown stored |
| Override reason | Mandatory — form blocks submit without it |
| Document storage | Local FS for PoC, S3-compatible interface for swap |
| Decision attribution | Set at case closure in `persist.py` |
| Config changes | Require formal change request + Lorraine approval (compliance) |
| Scenario 5 | Always runs first on every payment |
| Update order | protos → schema → scenario docs → architecture docs → reference docs |

---

## Developer Setup (new engineer checklist)

```bash
git clone https://github.com/na1in/CES-POC
cd CES-POC
cp backend/.env.example backend/.env
# Add your ANTHROPIC_API_KEY to backend/.env
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
