.PHONY: proto install db-up db-down up down migrate seed dev dev-frontend logs

# Requires protoc: brew install protobuf  OR  conda install -c conda-forge protobuf
proto:
	./scripts/compile_protos.sh

install:
	pip install -r backend/requirements.txt

# --- Docker targets ---

# Start only the database (for local dev with hot-reload)
db-up:
	docker compose up -d db
	@echo "Waiting for Postgres to be ready..."
	@until docker compose exec db pg_isready -U ces_user -d ces; do sleep 1; done

db-down:
	docker compose down

# Start the full stack (db + backend + frontend) in Docker
up:
	docker compose up -d --build
	@echo "Waiting for Postgres to be ready..."
	@until docker compose exec db pg_isready -U ces_user -d ces; do sleep 1; done
	@echo "\nStack running:"
	@echo "  Frontend → http://localhost:3000"
	@echo "  Backend  → http://localhost:8000"
	@echo "  API docs → http://localhost:8000/docs"

down:
	docker compose down

logs:
	docker compose logs -f

# --- Database targets ---

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python scripts/seed.py

# Full setup for a new engineer (after cloning the repo)
# Option A: full Docker stack
setup: up
	docker compose exec backend alembic upgrade head
	docker compose exec backend python scripts/seed.py
	@echo "\nSetup complete. Visit http://localhost:3000"

# Option B: local dev with hot-reload (needs Python + Node installed)
setup-local: install db-up migrate seed
	@echo "\nSetup complete. Run 'make dev' and 'make dev-frontend' in separate terminals."

# --- Local dev targets (hot-reload, no Docker for app) ---

dev:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev
