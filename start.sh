#!/usr/bin/env bash
# start.sh — boots the full CES stack and tells you when it's ready
# Run from the repo root: bash start.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

BACKEND_PORT=8000
FRONTEND_PORT=3001

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

log()  { echo -e "${BOLD}[CES]${RESET} $*"; }
ok()   { echo -e "${GREEN}[CES] ✓ $*${RESET}"; }
warn() { echo -e "${YELLOW}[CES] ⚠ $*${RESET}"; }
die()  { echo -e "${RED}[CES] ✗ $*${RESET}"; exit 1; }

cleanup() {
  log "Shutting down…"
  [[ -n "${BACKEND_PID:-}"  ]] && kill "$BACKEND_PID"  2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── 1. Docker Desktop ─────────────────────────────────────────────────────────
log "Checking Docker…"
if ! docker info &>/dev/null; then
  warn "Docker Desktop is not running. Launching it now…"
  open -a Docker
  echo -n "    Waiting for Docker to start"
  for i in $(seq 1 30); do
    sleep 2
    echo -n "."
    docker info &>/dev/null && break
    [[ $i -eq 30 ]] && die "Docker did not start after 60s. Open Docker Desktop manually and re-run."
  done
  echo ""
fi
ok "Docker is running"

# ── 2. PostgreSQL container ───────────────────────────────────────────────────
log "Starting database…"
cd "$ROOT"
docker compose up -d db &>/dev/null

echo -n "    Waiting for PostgreSQL to be healthy"
for i in $(seq 1 30); do
  sleep 2
  echo -n "."
  status=$(docker inspect --format='{{.State.Health.Status}}' ces-db-1 2>/dev/null || echo "not_found")
  [[ "$status" == "healthy" ]] && break
  [[ $i -eq 30 ]] && die "Database did not become healthy after 60s."
done
echo ""
ok "Database is healthy"

# ── 3. Schema + seed ─────────────────────────────────────────────────────────
log "Applying schema and seeding data…"

# Apply schema (idempotent — uses CREATE IF NOT EXISTS / DO NOTHING)
docker exec -i ces-db-1 psql -U ces_user -d ces \
  < "$ROOT/db/schema.sql" &>/dev/null \
  && ok "Schema applied" \
  || warn "Schema apply had warnings (may already exist — continuing)"

# Seed (idempotent — safe to re-run)
cd "$BACKEND"
python scripts/seed.py \
  && ok "Seed data loaded" \
  || die "Seed script failed. Check backend/.env and try again."

# ── 4. Backend ────────────────────────────────────────────────────────────────
log "Starting backend on :${BACKEND_PORT}…"

# Kill anything already on the port
lsof -ti:"$BACKEND_PORT" | xargs kill -9 2>/dev/null || true

cd "$BACKEND"
python -m uvicorn app.main:app --port "$BACKEND_PORT" --reload \
  > /tmp/ces-backend.log 2>&1 &
BACKEND_PID=$!

echo -n "    Waiting for backend"
for i in $(seq 1 30); do
  sleep 2
  echo -n "."
  curl -s "http://localhost:${BACKEND_PORT}/health" | grep -q '"ok"' && break
  [[ $i -eq 30 ]] && die "Backend did not start. Check /tmp/ces-backend.log."
done
echo ""
ok "Backend is up"

# ── 5. Frontend ───────────────────────────────────────────────────────────────
log "Starting frontend on :${FRONTEND_PORT}…"

lsof -ti:"$FRONTEND_PORT" | xargs kill -9 2>/dev/null || true

cd "$FRONTEND"
npx next dev -p "$FRONTEND_PORT" \
  > /tmp/ces-frontend.log 2>&1 &
FRONTEND_PID=$!

echo -n "    Waiting for frontend to compile"
for i in $(seq 1 60); do
  sleep 3
  echo -n "."
  curl -s -o /dev/null -w "%{http_code}" "http://localhost:${FRONTEND_PORT}/" \
    | grep -q "200" && break
  [[ $i -eq 60 ]] && die "Frontend did not start after 3 minutes. Check /tmp/ces-frontend.log."
done
echo ""
ok "Frontend is up"

# ── Ready ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  CES is ready!${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  App:      ${BOLD}http://localhost:${FRONTEND_PORT}${RESET}"
echo -e "  API:      http://localhost:${BACKEND_PORT}/docs"
echo ""
echo -e "  ${BOLD}Users:${RESET}"
echo -e "    Priya Sharma    — Analyst       (queue dashboard)"
echo -e "    Damien Torres   — Investigator  (investigation queue)"
echo -e "    Lorraine Chen   — Director      (governance dashboard)"
echo -e "    Marcus Webb     — Admin         (admin dashboard)"
echo ""
echo -e "  Logs:  /tmp/ces-backend.log  |  /tmp/ces-frontend.log"
echo -e "  Stop:  Ctrl+C"
echo ""

# Open browser automatically
open "http://localhost:${FRONTEND_PORT}" 2>/dev/null || true

# Keep running so Ctrl+C triggers cleanup
wait
