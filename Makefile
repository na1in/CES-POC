.PHONY: proto install db-up db-down migrate seed dev

# Requires protoc: brew install protobuf  OR  conda install -c conda-forge protobuf
proto:
	./scripts/compile_protos.sh

install:
	pip install -r backend/requirements.txt

db-up:
	docker compose up -d
	@echo "Waiting for Postgres to be ready..."
	@until docker compose exec db pg_isready -U ces_user -d ces; do sleep 1; done

db-down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python scripts/seed.py

# Full setup for a new engineer (after cloning the repo)
setup: install db-up migrate seed
	@echo "\nSetup complete. Start the API with: make dev"

dev:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev
