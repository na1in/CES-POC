# CES Payment Resolution System — Architecture Summary

**Version:** 1.1
**Date:** April 8, 2026
**Status:** Proposed

---

## What This System Does

The CES Payment Resolution System is an AI-agent-powered pipeline that processes unidentified/miscellaneous insurance payments. Payments enter the system without sufficient reference information (missing policy numbers, incorrect references, unmatched amounts) and land in a "misc bucket" requiring manual investigation.

The AI agent classifies each payment, identifies the likely policy/customer match, and recommends one of three actions:
- **APPLY** — allocate payment to the identified policy
- **HOLD** — keep in suspense for manual analyst review
- **ESCALATE** — route to investigation queue

---

## User Roles

Four personas interact with the system. Role is assigned at auth time and controls home screen, data access scope, and decision authority.

| Role | Persona | Responsibilities |
|------|---------|-----------------|
| Analyst | Priya | Daily queue, apply/hold/escalate HELD payments, add case notes, upload documents |
| Investigator | Damien | Escalated cases only — final determination, outreach logging, fraud review, mark returns |
| Director | Lorraine | Governance dashboard, compliance export, exception dashboard, approve config changes |
| Admin | Marcus | Config management, performance monitoring, override analysis, propose threshold changes |

---

## Architecture at a Glance

The system is a 5-stage pipeline. Each stage has a single responsibility:

```
┌─────────────┐    ┌──────────────────┐    ┌───────────────┐    ┌──────────────┐    ┌──────────────────┐
│   INGEST     │───>│  COMPUTE SIGNALS │───>│   AI AGENT    │───>│   PERSIST    │───>│  HUMAN APPROVAL  │
│ (Event Mon.) │    │ (Context Layer)  │    │ (Decision Eng)│    │(Action Exec.)│    │ (Audit/Explain.) │
└─────────────┘    └──────────────────┘    └───────────────┘    └──────────────┘    └──────────────────┘
```

| Stage | What It Does | Who Does the Work |
|-------|-------------|-------------------|
| 1. Ingest | Validate payment, parse free-text references | Code + Claude API |
| 2. Compute Signals | Calculate 19 analytical signals (name match, amount variance, third-party, etc.) | Deterministic code + Haiku for gray-zone names |
| 3. AI Agent | Route to scenario, reason about decision | Deterministic routing + Claude API reasoning |
| 4. Persist | Save recommendation, update status, write audit trail | Code (single DB transaction) |
| 5. Human Approval | Analyst dashboard to review, approve/reject HOLD items | Next.js frontend |

---

## The 5 Scenarios

Every payment is routed to one of 5 scenarios based on match quality:

| Scenario | Trigger | Typical Outcome |
|----------|---------|-----------------|
| 1. Strong Policy Match | Policy # provided, name matches, amount within tolerance, low risk method | APPLY (auto or with approval) |
| 2. Customer Match, No Policy | Customer found but no policy reference | APPLY with approval (if unambiguous) |
| 3. High Amount Variance | Match found but amount deviates significantly | HOLD or ESCALATE |
| 4. No Matching Customer | Cannot identify sender | ESCALATE (or HOLD if third-party detected) |
| 5. Duplicate Payment | Match within 72 hours (amount within $2 tolerance) | HOLD or ESCALATE |

Scenario 5 runs **first** on every payment. Then the system routes to 1, 2, 3, or 4.

---

## Where AI Is Used (3 Places)

| Location | Model | Purpose |
|----------|-------|---------|
| Ingest — reference parsing | Claude (Sonnet/Opus) | Extract policy numbers, intent, period count from free-text |
| Signals — name matching | Claude Haiku | Gray-zone fallback (70-92%) for nicknames, format variations |
| Agent — scenario reasoning | Claude (Sonnet/Opus) | Weigh signals, produce recommendation + explanations |

Everything else is deterministic code — the AI is constrained to specific, controlled points.

---

## Key Design Principles

- **Deterministic routing** — scenario selection is pure if/else, fully testable
- **Config-driven thresholds** — all decision boundaries stored in DB, editable at runtime
- **Signals snapshotted** — what the system saw at decision time is preserved forever
- **Human-in-the-loop** — HOLD items require analyst approval before ledger update
- **Full audit trail** — every action logged with actor, timestamp, and details
- **Retry on failure** — transient failures retried 3 times; permanent failures flagged for review
- **Amounts in cents** — all monetary values stored as integers to avoid floating-point issues

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI (async) |
| Database | PostgreSQL 15+, SQLAlchemy (async) + asyncpg |
| AI (reasoning) | Claude API — Sonnet/Opus (anthropic SDK) |
| AI (name matching) | Claude Haiku (gray-zone fallback) |
| Data Models | Protobuf proto3 (source of truth) |
| Frontend | Next.js, React, TypeScript, Tailwind CSS + shadcn/ui |
| String Matching | jellyfish (Jaro-Winkler, Levenshtein, Soundex) |

---

## Detailed Architecture Documents

Each stage of the pipeline is documented in its own file:

| Document | Covers |
|----------|--------|
| [01_Ingest_Layer.md](./01_Ingest_Layer.md) | Payment ingestion, field validation, free-text reference parsing |
| [02_Compute_Signals.md](./02_Compute_Signals.md) | 19 signals across 5 categories, 3-wave computation, hybrid name matching with full algorithm breakdown |
| [03_AI_Agent.md](./03_AI_Agent.md) | Scenario routing, per-scenario decision logic, Claude API reasoning |
| [04_Persist_Layer.md](./04_Persist_Layer.md) | Saving recommendations, ledger updates, retry & failure strategy |
| [05_Human_Approval_Queue.md](./05_Human_Approval_Queue.md) | 10 frontend pages across 4 roles (Analyst, Investigator, Director, Admin) |
| [06_API_Reference.md](./06_API_Reference.md) | All REST endpoints, request/response formats |
| [07_Data_Flow.md](./07_Data_Flow.md) | End-to-end sequence, pipeline orchestration, payment lifecycle |

---

*End of Summary*
