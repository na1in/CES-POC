# CES — Project Status

> **How to use this doc**  
> Update your ticket's status emoji and add a short note when you pick something up, hit a blocker, or finish. Keep it current — this is the team's single source of truth.  
> Status key: ✅ Done · 🔄 In Progress · 🚫 Blocked · ⬜ Not Started

---

## Overview

| Field | Value |
|-------|-------|
| **Repo** | https://github.com/na1in/CES-POC |
| **Current week** | Week 5 |
| **Active phase** | Phase 2 backend complete → Phase 3 starting |
| **Last updated** | 2026-05-11 |
| **Open PR** | #9 — CES-17–31 (Phase 2 complete) against `main` |

## Team

| Role | Name | Tracks |
|------|------|--------|
| PM + Engineer A | Nalin | Backend pipeline, AI agent, DB, APIs |
| Engineer B | Praneetha | Frontend pages (all 10 built with mock data); wire-up pending |
| Designer | — | Figma designs (referenced in docs) |

---

## Phase Summary

| Phase | Weeks | Focus | Status |
|-------|-------|-------|--------|
| **Phase 0 — Foundation** | 1 | DB, protos, FastAPI skeleton, frontend scaffold | ✅ Done |
| **Phase 1 — Core Pipeline + Frontend Shell** | 2–4 | Ingest → signals, analyst/investigator pages | ✅ Done |
| **Phase 2 — AI Agent + Analyst APIs** | 5–7 | Scenarios 1–5, approve/reject/override, annotations, documents, SLA | ✅ Backend done · 🔄 Frontend wire-up in progress |
| **Phase 3 — Director/Admin + Governance APIs** | 8–9 | Analytics/Governance/Config APIs + wire Director/Admin pages | ⬜ Not Started |
| **Phase 4 — Integration & Polish** | 10 | E2E tests, role-gating, UI polish | ⬜ Not Started |

---

## Phase 0 — Foundation ✅ Complete

| Ticket | Owner | Status | Notes |
|--------|-------|--------|-------|
| PostgreSQL setup + `schema.sql` applied | Eng A | ✅ | Docker Compose — `docker compose up -d` |
| Alembic migrations (versioned, async) | Eng A | ✅ | `make migrate` runs `alembic upgrade head` |
| Seed data (users, customers, policies, thresholds) | Eng A | ✅ | `make seed` — idempotent |
| Proto compilation pipeline | Eng A | ✅ | `make proto` — uses system `protoc` |
| Python classes generated from 11 protos | Eng A | ✅ | Output: `backend/app/proto_gen/` |
| FastAPI skeleton — DB session, auth middleware | Eng A | ✅ | JWT + role guards in `auth.py` |
| `requirements.txt` complete | Eng A | ✅ | All deps incl. jellyfish, python-jose, alembic |
| Next.js + Tailwind v4 scaffold | Eng B | ✅ | |
| shadcn/ui initialized | Eng B | ✅ | Button, Card, Badge, Table, Separator |
| All 11 `.proto` files authored | PM / Eng A | ✅ | Source of truth for all data models |
| All architecture + scenario docs | PM | ✅ | `docs/architecture/`, `docs/scenarios/` |

---

## Phase 1 — Core Pipeline + Frontend Shell ✅ Complete

### Track A: Backend Pipeline (Engineer A)

| Ticket | Est | Status | Notes |
|--------|-----|--------|-------|
| **CES-7** `POST /api/payments/ingest` — validate fields, Claude Haiku ref parsing, PMT-XXX ID, INSERT RECEIVED + audit | 3d | ✅ | 23 tests passing |
| **CES-8** Signal Wave 1 — name similarity (hybrid jaro-winkler + levenshtein + soundex + Haiku gray zone 70–92%), amount variance, timing quality, duplicate check | 4d | ✅ | 25 tests |
| **CES-9** Signal Wave 2 — policy/customer match confidence, over/underpayment, historical consistency (z-score) | 3d | ✅ | |
| **CES-10** Signal Wave 3 — risk flags, account status, balance snapshot, payment method risk, supporting signals, multi-period, multi-method, third-party | 3d | ✅ | |
| **CES-11** Signal snapshot — persist all 19 signals to `payment_signals`, write SIGNALS_COMPUTED audit | 1d | ✅ | |

### Track B: Frontend Shell (Engineer B + Designer)

| Ticket | Est | Status | Notes |
|--------|-----|--------|-------|
| **CES-12** TypeScript types from all protos + mock API responses | 2d | ✅ | 8 mock payments covering all 5 scenarios |
| **CES-13** Queue Dashboard `/` — confidence-sorted, payment method column, scenario filter | 2d | ✅ | |
| **CES-14** Investigation Queue `/investigations` — risk-sorted, SLA breach indicator | 2d | ✅ | |
| **CES-15** Payment Detail `/payments/[id]` — signals panel, reasoning, audit timeline, action buttons, annotations, docs | 4d | ✅ | |
| **CES-16** Settings `/settings` — threshold viewer, read-only for non-admin | 1d | ✅ | |

---

## Phase 2 — AI Agent + Analyst/Investigator APIs

### Track A: AI Agent + Persist + Action APIs (Engineer A) ✅ Complete

| Ticket | Est | Status | Notes |
|--------|-----|--------|-------|
| **CES-17** Scenario Router — S5→S4→S3→S1→S2 deterministic routing; thresholds from DB | 2d | ✅ | 32 unit tests |
| **CES-18** Scenario 1 — Strong Policy Match; auto-apply path (name >90%, no risk, active, low-risk method) | 1.5d | ✅ | |
| **CES-19** Scenario 2 — Customer Match, No Policy; always requires human approval | 1.5d | ✅ | |
| **CES-20** Scenario 3 — High Amount Variance; 5 tiers; multi-period/multi-method/third-party special cases | 2d | ✅ | |
| **CES-21** Scenario 4 — No Matching Customer; third-party hold path | 1d | ✅ | 49 scenario tests total |
| **CES-22** Scenario 5 — Duplicate Payment; balance >0 → HOLD, =0 → ESCALATE | 1d | ✅ | |
| **CES-23** Persist layer — single transaction: INSERT rec, UPDATE payments, auto-apply ledger, audit | 1.5d | ✅ | 12 tests |
| **CES-24** Pipeline orchestrator — 3-retry wrapper (1s/3s backoff); PROCESSING_FAILED on exhaustion | 1d | ✅ | 13 tests |
| **CES-25** `POST /approve` — analyst; HELD → applied + ledger + human_confirmed | 1.5d | ✅ | 17 tests |
| **CES-26** `POST /reject`, `/override`, `/return`, `/reprocess` | 1.5d | ✅ | |
| **CES-27** SLA service — `compute_due_date()`, `check_and_mark_breaches()`, asyncio background monitor | 1d | ✅ | 8 tests |

### Track B: Read APIs + Annotations + Documents (Engineer A) ✅ Complete

| Ticket | Est | Status | Notes |
|--------|-----|--------|-------|
| **CES-28** `GET /api/payments` (filtered/paginated) + `GET /api/payments/{id}` (full detail, signals by category) | 2.5d | ✅ | 10 tests |
| **CES-29** Annotations — `POST/GET /api/payments/{id}/annotations`; all 4 types | 1d | ✅ | 19 tests |
| **CES-30** Documents — upload (multipart, 20MB, MIME allowlist), list, stream, soft delete + `storage.py` | 2d | ✅ | 9 tests |
| **CES-31** PENDING_SENDER_RESPONSE flow — contact_record → pending_sender_response status transition | 1d | ✅ | Covered by annotation tests |

### Track B: Frontend Wire-up (Engineer B) 🔄 In Progress

| Ticket | Est | Status | Notes |
|--------|-----|--------|-------|
| **CES-32** Wire analyst/investigator pages to real APIs — Queue, Detail, Investigations, Settings | 2d | 🔄 | Replace mock data; add loading/error/empty states |

### Track B: Director/Admin Pages (Engineer B) ✅ Built (with mock data)

| Ticket | Est | Status | Notes |
|--------|-----|--------|-------|
| **CES-34** Governance Dashboard `/governance` | 3d | ✅ | Mock data — needs Phase 3 API wire-up |
| **CES-35** Compliance Export `/governance/export` | 1d | ✅ | Mock data |
| **CES-36** Exception Dashboard `/governance/exceptions` | 2d | ✅ | Mock data |
| **CES-37** Admin Dashboard `/admin` | 2d | ✅ | Mock data |
| **CES-38** Override Analysis `/admin/overrides` | 1d | ✅ | Mock data |
| **CES-39** Configuration Management `/admin/config` | 3d | ✅ | Mock data |

---

## Phase 3 — Governance/Analytics/Config APIs ⬜ Not Started

### Track A: APIs (Engineer A)

| Ticket | Est | Status | Notes |
|--------|-----|--------|-------|
| `GET /api/analytics/decisions` — attribution counts, method breakdown, per-scenario, confidence histogram | 2d | ⬜ | Powers Lorraine + Marcus dashboards |
| `GET /api/analytics/overrides` — filterable by scenario, confidence band, date, reason | 1d | ⬜ | |
| `POST/GET /api/governance/reviews` | 1d | ⬜ | Lorraine period review log |
| `POST/GET /api/governance/anomalies` + `PATCH .../anomalies/{id}` | 1d | ⬜ | Anomaly flag workflow |
| `GET /api/governance/export` — audit-ready report | 1d | ⬜ | |
| Config change-request workflow — propose → approve → reject → deploy → rollback + history | 3d | ⬜ | Atomic threshold swap, ThresholdVersion row |

### Track B: Director/Admin Wire-up (Engineer B)

| Ticket | Est | Status | Notes |
|--------|-----|--------|-------|
| Wire Governance Dashboard + Export + Exceptions to real APIs | 2d | ⬜ | Depends on Phase 3 APIs |
| Wire Admin Dashboard + Override Analysis + Config Management to real APIs | 2d | ⬜ | |

---

## Phase 4 — Integration & Polish ⬜ Not Started

| Ticket | Owner | Status |
|--------|-------|--------|
| E2E test: Scenario 1 — auto-apply + hold | Eng A | ⬜ |
| E2E test: Scenario 2 — single policy, ambiguous multi-policy | Eng A | ⬜ |
| E2E test: Scenario 3 — variance tiers + special cases | Eng A | ⬜ |
| E2E test: Scenario 4 — no match + third-party hold | Eng A | ⬜ |
| E2E test: Scenario 5 — exact dup, $2 tolerance, outside window | Eng A | ⬜ |
| E2E test: Analyst flows — approve, reject, override, reprocess | Eng A | ⬜ |
| E2E test: Investigator flows — return, contact → PENDING_SENDER_RESPONSE, SLA breach | Eng A | ⬜ |
| E2E test: Config workflow — propose → approve → deploy → verify → rollback | Eng A | ⬜ |
| E2E test: Retry + failure — simulate DB/Claude timeouts, PROCESSING_FAILED, reprocess | Eng A | ⬜ |
| Frontend integration — real APIs across all 10 pages, error/empty/loading states, role-gating | Eng B | ⬜ |
| Analytics accuracy — verify attribution counts, override rate %, histogram | Eng B | ⬜ |
| UI polish — responsive layout, empty states, error toasts, accessibility | Designer + Eng B | ⬜ |

---

## Open Questions

| # | Question | Owner | Priority | Status |
|---|----------|-------|----------|--------|
| 1 | Notification channel for policyholder outreach — in-system, email, phone? | PM | 🟡 Medium | Open — contact_record model supports phone/email/letter but no dispatch service |
| 2 | Staging/simulation environment — anonymised production data or synthetic data? | Eng A | 🟡 Medium | Open — PoC uses synthetic seed data only |

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
| Document storage | Local FS for PoC (`UPLOAD_DIR`), S3-compatible interface |
| Decision attribution | Set at case closure in `persist.py` |
| Config changes | Require formal change request + Lorraine approval (compliance) |
| Scenario 5 | Always runs first on every payment |
| SLA default | 72 hours — `_SLA_HOURS` in `persist.py`; imported by `approvals.py` and `sla.py` |
| contact_record annotation | Transitions `escalated` → `pending_sender_response`; SLA timer starts |

---

## Developer Setup

```bash
git clone https://github.com/na1in/CES-POC
cd CES-POC
cp backend/.env.example backend/.env
# Add ANTHROPIC_API_KEY to backend/.env
make setup        # installs deps + starts Docker Postgres + migrates + seeds
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

Tests:
```bash
cd backend && python -m pytest tests/ -v
# 176 pass; 1 expected DB error (needs Postgres)
```
