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
  - `docs/Final_Scenario_Definitions.md` — authoritative decision logic
  - `docs/Step3_Feature_Signals.md` — signal computation methods
  - `docs/Executive_Summary_Scenarios.md` — overview with routing flow

## Conventions
- Monetary amounts are stored as integers in cents (never floats)
- IDs use prefixed format: `CUST-XXXX`, `POL-XXXXX`, `PMT-XXX`
- Proto files are the source of truth — schema and application models derive from them
- All DB operations use transactions
- Enums in Postgres are lowercase snake_case (`fraud_history`, not `FRAUD_HISTORY`)

## Architecture (Pipeline)
1. **Ingest** (code) — validate fields, persist payment
   - AI: parse free-text reference fields to extract policy numbers, intent, period count
2. **Compute Signals** (code) — math, lookups, queries against customer/policy/history data
3. **AI Agent** (LLM) — receives signals + context, reasons through scenarios, produces recommendation with explanations
4. **Persist** (code) — save signals snapshot + recommendation + audit log entry
5. **Human Approval Queue** — AI ranks HOLD items by urgency, analyst reviews

## Scenarios
1. Strong Policy Match — policy number provided, name matches
2. Customer Match, No Policy — customer found but policy ambiguous
3. High Amount Variance — payment deviates from expected premium
4. No Matching Customer — sender unknown
5. Duplicate Payment — exact match within 72 hours

## Signals are computed then snapshotted
Signals (name similarity, amount variance, risk flags, etc.) are computed on the fly but persisted to `payment_signals` at decision time. This preserves what the system saw when it made the recommendation, even if underlying data changes later.

## Configuration thresholds
Decision thresholds (name match %, amount tolerance %, duplicate window hours) are stored in `configuration_thresholds` table and read at runtime. Never hardcode these.
