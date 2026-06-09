# CES — Local Setup Guide

This guide walks you through cloning the repo and running the full CES (Customer Exception System) stack on your machine. Follow the steps in order; the Troubleshooting section at the end covers the most common issues.

---

## 1. Prerequisites

You need four tools installed. Run these commands to check — the required minimum version is shown next to each.

| Tool | Min version | Check command |
|------|-------------|---------------|
| Git | any | `git --version` |
| Docker Desktop | 4.x | `docker --version` |
| Python | 3.12+ | `python3 --version` |
| Node.js | 18+ | `node --version` |

### Install anything missing

- **Git** — https://git-scm.com/downloads
- **Docker Desktop** — https://www.docker.com/products/docker-desktop (includes `docker compose`)
- **Python 3.12+** — https://www.python.org/downloads or via `brew install python@3.12` on Mac
- **Node.js 18+** — https://nodejs.org/en/download or via `brew install node` on Mac

> **Mac tip:** If you have Homebrew, `brew install git python@3.12 node` covers three of these at once.

After installing, open a new terminal window and re-run the check commands above to confirm the versions.

---

## 2. Clone the Repository

```bash
git clone https://github.com/na1in/CES-POC.git
cd CES-POC
```

---

## 3. Create the Backend `.env` File

The backend needs a `.env` file that is **not** included in the repo (it contains secrets). A template is provided.

```bash
cp backend/.env.example backend/.env
```

Then open `backend/.env` in any text editor and fill in your OpenRouter API key:

```
DATABASE_URL=postgresql+asyncpg://ces_user:ces_password@localhost:5432/ces
OPENROUTER_API_KEY=sk-or-v1-your-key-here   ← replace this
JWT_SECRET_KEY=change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

**Getting an OpenRouter key:**
1. Go to https://openrouter.ai and sign up (free)
2. Click your avatar → Keys → Create Key
3. Paste the key into `backend/.env`

> The app uses `google/gemini-2.5-flash` via OpenRouter for AI payment reasoning. Without a valid key the pipeline will fail, but the UI and all read-only pages will still work.

---

## 4. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
cd ..
```

> If you use a virtual environment (recommended):
> ```bash
> cd backend
> python3 -m venv .venv
> source .venv/bin/activate   # Windows: .venv\Scripts\activate
> pip install -r requirements.txt
> cd ..
> ```

---

## 5. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## 6. Start the Database

PostgreSQL runs in Docker. Make sure Docker Desktop is open, then:

```bash
docker compose up -d db
```

Wait about 10 seconds, then verify the container is healthy:

```bash
docker ps
```

You should see `ces-db-1` with status `healthy`. If it shows `starting`, wait a few more seconds and run `docker ps` again.

---

## 7. Apply the Schema and Seed Data

From the repo root, apply the database schema:

```bash
docker exec -i ces-db-1 psql -U ces_user -d ces < db/schema.sql
```

Then seed the test data (users, customers, policies, payments):

```bash
cd backend
python scripts/seed.py
cd ..
```

You should see output ending with the four test user names. This is safe to re-run — it won't duplicate data.

---

## 8. Start the Backend

```bash
cd backend
python -m uvicorn app.main:app --port 8000 --reload
```

Leave this terminal open. Verify it's running in a new terminal tab:

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

## 9. Start the Frontend

Open a new terminal tab (keep the backend terminal running):

```bash
cd frontend
npx next dev -p 3001
```

The first compile takes about 60–90 seconds. When you see `✓ Ready`, open:

**http://localhost:3001**

---

## 10. Log In

The login page shows clickable user cards — no password required.

| User | Role | Home page |
|------|------|-----------|
| **Priya Sharma** | Analyst | `/` — Payment queue (apply / escalate held payments) |
| **Damien Torres** | Investigator | `/investigations` — Escalated cases |
| **Lorraine Chen** | Director | `/governance` — Governance metrics |
| **Marcus Webb** | Admin | `/admin` — Analytics + configuration |

---

## 11. Key Pages to Explore

| URL | Logged in as | What you'll see |
|-----|-------------|-----------------|
| `http://localhost:3001/` | Priya | Queue of held payments with AI recommendations |
| `http://localhost:3001/payments/PMT-ESC-001` | Damien | Pre-escalated case — try "Awaiting Sender Response" |
| `http://localhost:3001/investigations` | Damien | Investigation queue with SLA report modal |
| `http://localhost:3001/governance` | Lorraine | Decision metrics, override rate, SLA adherence |
| `http://localhost:3001/governance/exceptions` | Lorraine | SLA breaches + anomaly flags |
| `http://localhost:3001/admin/config` | Marcus | Submit threshold change requests; Lorraine approves |
| `http://localhost:3001/admin` | Marcus | Per-scenario analytics + confidence histograms |
| `http://localhost:8000/docs` | — | Interactive API docs (Swagger UI) |

---

## 12. Submit a Test Payment (Optional)

With the backend running, you can ingest a payment and watch the full AI pipeline run:

```bash
cd backend
bash demo.sh scenario1       # Strong policy match
bash demo.sh scenario2       # Customer match, no policy
bash demo.sh variance        # High amount variance
bash demo.sh duplicate       # Duplicate detection
bash demo.sh no_customer     # No matching customer — escalate
bash demo.sh all             # Run all scenarios back to back
```

Each call prints the AI recommendation and confidence score. The new payment then appears in Priya's queue.

---

## Troubleshooting

### "Connection refused" when starting the backend

The database isn't running. Open Docker Desktop and check that the `ces-db-1` container is green, or run:

```bash
docker compose up -d db
```

---

### `docker ps` shows `ces-db-1` as "starting" for more than 30 seconds

The container may have failed. Check the logs:

```bash
docker logs ces-db-1
```

Common cause: port 5432 is already in use by a local Postgres installation. Stop the local Postgres service and retry:

```bash
# Mac (Homebrew)
brew services stop postgresql@16

# then restart the container
docker compose up -d db
```

---

### Port 8000 or 3001 already in use

```bash
# Kill whatever is on port 8000
lsof -ti:8000 | xargs kill -9

# Kill whatever is on port 3001
lsof -ti:3001 | xargs kill -9
```

Then restart the backend / frontend.

---

### `python scripts/seed.py` fails with "already exists" errors

The seed data is already loaded — this is safe to ignore. The script is idempotent, but some Postgres versions surface warnings instead of silently skipping. The app will work fine.

---

### Frontend compiles but the page is blank or shows "Failed to fetch"

The frontend can't reach the backend. Check:

1. Backend is running on port 8000: `curl http://localhost:8000/health`
2. You're using `npx next dev -p 3001` (not the Docker frontend container on port 3000)
3. No VPN or firewall blocking localhost connections

---

### OpenRouter / AI errors in the payment pipeline

The demo and `POST /api/payments/ingest` calls require a valid OpenRouter key. Verify:

```bash
grep OPENROUTER_API_KEY backend/.env
```

If the key looks like `sk-or-v1-your-key-here` you forgot to fill it in. Get a real key from https://openrouter.ai.

---

### `npm install` fails with Node version errors

Check your Node version: `node --version`. You need **18 or higher**. If you have an older version:

```bash
# Mac (Homebrew)
brew install node

# Or use nvm
nvm install 20
nvm use 20
```

---

### Schema apply gives "permission denied" or "database does not exist"

The database container may not be fully ready yet. Wait 15 seconds after `docker compose up -d db`, then retry:

```bash
docker exec -i ces-db-1 psql -U ces_user -d ces < db/schema.sql
```

---

## Quick Reference

```
Ports
  Backend API    http://localhost:8000
  API Docs       http://localhost:8000/docs
  Frontend       http://localhost:3001

Useful commands
  docker compose up -d db          Start the database
  docker compose down              Stop all containers
  docker logs ces-db-1             DB container logs
  curl http://localhost:8000/health Backend health check

Log files (if you used start.sh)
  /tmp/ces-backend.log
  /tmp/ces-frontend.log
```
