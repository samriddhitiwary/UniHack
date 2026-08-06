.PHONY: setup dev api web dynamodb-up dynamodb-down dynamodb-create-tables dynamodb-reset test test-api test-web lint format typecheck-api build-web clean

setup:
	uv sync --project apps/api --all-groups
	npm --prefix=apps/web install

dev:
	@echo "Run 'make dynamodb-up', 'make api', and 'make web' in separate terminals."

api:
	uv run --project apps/api uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000

web:
	npm --prefix=apps/web run dev

dynamodb-up:
	docker compose up -d dynamodb-local

dynamodb-down:
	docker compose down

dynamodb-create-tables:
	uv run --project apps/api python scripts/dynamodb/create_tables.py

dynamodb-reset:
	docker compose down
	uv run --project apps/api python scripts/dynamodb/reset_local.py
	docker compose up -d dynamodb-local

test: test-api test-web

test-api:
	uv run --project apps/api pytest apps/api/tests

test-web:
	npm --prefix=apps/web test -- --run

lint:
	uv run --project apps/api ruff check apps/api scripts
	npm --prefix=apps/web run lint

format:
	uv run --project apps/api ruff format apps/api scripts
	npm --prefix=apps/web run format

typecheck-api:
	uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/app

build-web:
	npm --prefix=apps/web run build

clean:
	uv run --project apps/api python scripts/development/clean.py
	npm --prefix=apps/web run clean
