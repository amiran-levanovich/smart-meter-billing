.PHONY: install dev dev-backend dev-frontend demo test lint crosscheck types

install:
	cd backend && uv sync
	cd frontend && npm ci

dev:
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

demo:
	cd backend && uv run python -m scripts.seed_demo

test:
	cd backend && uv run pytest -q
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint && npm run typecheck

crosscheck:
	cd backend && uv run --group crosscheck python scripts/crosscheck.py

types:
	cd backend && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))" > ../frontend/openapi.json
	cd frontend && npx openapi-typescript openapi.json -o src/api.d.ts
