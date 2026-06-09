# Running the App

Step-by-step guide to get CES running locally for development and demo.

> **First time on this repo?** See [`SETUP.md`](SETUP.md) for a full onboarding guide with prerequisites, dependency install steps, and detailed troubleshooting.

---

## Prerequisites

- Docker Desktop (for PostgreSQL)
- Python 3.12+ with `pip`
- Node.js 18+ with `npm`
- Conda or virtualenv (optional but recommended)

---

## 1. Start the Database

PostgreSQL runs in Docker. Make sure Docker Desktop is open first, then:

```bash
docker compose up -d db
```

Verify it's healthy:

```bash
docker ps   # db-1 should show "healthy"
```

> **Note:** `docker compose up -d` (no service name) starts all three services — db, backend (:8000), and frontend (:3000). Use this when you want a quick full-stack run without a dev server. For active development, run backend and frontend locally (steps 2–3) so `--reload` and hot-reload pick up your changes.

---

## 2. Start the Backend

Run from the `backend/` directory. The `--reload` flag picks up code changes automatically — no need to restart manually.

```bash
cd backend
python -m uvicorn app.main:app --port 8000 --reload
```

Verify:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

The backend reads credentials from `backend/.env`. The file is already configured for the local Docker database — no changes needed. If you don't have a `.env` yet, copy the template: `cp backend/.env.example backend/.env` and fill in `OPENROUTER_API_KEY`.

---

## 3. Start the Frontend

Run from the `frontend/` directory. Use port **3001** to avoid clashing with the Docker frontend container on 3000.

```bash
cd frontend
npx next dev -p 3001
```

First startup takes ~90 seconds to compile. Subsequent page loads are fast.

Open: **http://localhost:3001**

---

## 4. Log In

The login page shows clickable user cards — no password needed.

| Name | Role | Home page |
|------|------|-----------|
| Priya Sharma | Analyst | `/` — Queue Dashboard |
| Damien Torres | Investigator | `/investigations` — Investigation Queue |
| Lorraine Chen | Director | `/governance` — Governance Dashboard |
| Marcus Webb | Admin | `/admin` — Admin Dashboard |

---

## 5. Key Pages to Review

| URL | Who | What |
|-----|-----|------|
| `http://localhost:3001/` | Priya | Payment queue — apply/escalate held payments |
| `http://localhost:3001/investigations` | Damien | Escalated cases — contact sender, apply or return |
| `http://localhost:3001/payments/PMT-ESC-001` | Damien | Pre-seeded escalated case for testing investigator workflow |
| `http://localhost:3001/governance` | Lorraine | Governance metrics + Exception Dashboard button |
| `http://localhost:3001/governance/exceptions` | Lorraine | Config change approvals, SLA breaches, anomaly flags |
| `http://localhost:3001/admin/config` | Marcus | Propose threshold changes, deploy approved ones, rollback |

---

## 6. Run the API Demo Script

With the backend running, from the `backend/` directory:

```bash
bash demo.sh all
```

Or run individual scenarios:

```bash
bash demo.sh scenario1     # Strong policy match
bash demo.sh gray_zone     # Name matching in gray zone (triggers Gemini)
bash demo.sh variance      # High amount variance
bash demo.sh multi_period  # Multi-period payment
bash demo.sh duplicate     # Duplicate detection
bash demo.sh no_customer   # No matching customer
```

Each call ingests a payment, runs the full pipeline, and returns the AI recommendation.

---

## 7. Run the Tests

### Backend

```bash
cd backend
python -m pytest tests/ -v
```

Uses mocked LLM calls by default. To run against real Gemini (requires OpenRouter key in `.env`):

```bash
python -m pytest tests/ -v --live-llm
```

### Frontend (Playwright)

Requires both backend (`:8000`) and frontend dev server (`:3001`) to be running:

```bash
cd frontend
npx playwright test
```

---

## Troubleshooting

**Backend won't start — "Connection refused"**
The Docker DB container isn't running. Open Docker Desktop and run `docker compose up -d db`.

**Port 8000 already in use**
```bash
lsof -ti:8000 | xargs kill -9
```

**Rollback / approve errors in the UI**
Make sure you're running the local backend (`uvicorn` from step 2), not the Docker `backend-1` container. The Docker image is built from an older snapshot and won't have the latest code changes.
