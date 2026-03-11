# CES — Customer Exception System

AI-powered payment resolution for insurance operations. CES processes unidentified and miscellaneous payments, automatically determining whether to **APPLY**, **HOLD**, or **ESCALATE** each one.

## How It Works

When a payment arrives without clear identification, CES runs it through a pipeline:

1. **Ingest** — Validate the payment and parse free-text reference fields using AI to extract policy numbers, intent, and period count
2. **Compute Signals** — Calculate matching scores, amount variance, timing analysis, risk flags, and duplicate detection
3. **AI Agent** — Claude evaluates the signals, routes the payment through the appropriate scenario, and produces a recommendation with human-readable reasoning
4. **Persist** — Snapshot the signals and recommendation for auditability
5. **Human Review** — Payments marked HOLD are prioritized by AI for analyst review

## Scenarios

| # | Scenario | Trigger | Typical Outcome |
|---|----------|---------|-----------------|
| 1 | Strong Policy Match | Policy number provided, name matches | APPLY |
| 2 | Customer Match, No Policy | Customer found but policy ambiguous | APPLY with approval |
| 3 | High Amount Variance | Payment deviates from expected premium | HOLD or ESCALATE |
| 4 | No Matching Customer | Sender unknown | ESCALATE |
| 5 | Duplicate Payment | Exact match within 72 hours | ESCALATE |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy (async) + asyncpg |
| Frontend | Next.js, React, TypeScript, Tailwind CSS, shadcn/ui |
| Database | PostgreSQL |
| AI | Claude API (`anthropic` SDK) |
| Data Models | Protobuf (proto3) |

## Project Structure

```
CES/
├── backend/        # FastAPI application
├── frontend/       # Next.js application
├── proto/          # Protobuf definitions (source of truth)
├── db/             # PostgreSQL schema
└── docs/           # Design specs and scenario definitions
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+
- Anthropic API key

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # add your DATABASE_URL and ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Documentation

- [Executive Summary](docs/Executive_Summary_Scenarios.md) — overview with routing flow
- [Scenario Definitions](docs/Final_Scenario_Definitions.md) — authoritative decision logic
- [Feature Signals](docs/Step3_Feature_Signals.md) — signal computation methods
- [Database Design](docs/Database_Design.md) — schema design rationale
