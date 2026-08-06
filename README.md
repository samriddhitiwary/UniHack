# CatalogIQ AI

CatalogIQ AI is a JavaScript React frontend and Python FastAPI backend prepared for a cost-conscious AWS serverless deployment. The repository implements the SPEC-001 foundation and **SPEC-002: Product Domain Model and DynamoDB Access Patterns**.

## Prerequisites

- Node.js 22+
- Python 3.12 (managed automatically by `uv` if needed)
- `uv` 0.8+
- Docker Desktop with Docker Compose
- GNU Make (optional convenience; every command has a Windows-friendly equivalent below)

## Local setup

```powershell
Copy-Item .env.example .env
Copy-Item apps/api/.env.example apps/api/.env
Copy-Item apps/web/.env.example apps/web/.env
uv sync --project apps/api --all-groups
npm --prefix=apps/web install
docker compose up -d dynamodb-local
uv run --project apps/api python scripts/dynamodb/create_tables.py
```

The example files contain only local, non-secret settings. The backend supplies dummy credentials directly to Boto3 only when a local DynamoDB endpoint is configured.

## Run the applications

Use separate PowerShell terminals:

```powershell
uv run --project apps/api uvicorn app.main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000
npm --prefix=apps/web run dev
```

Open the web app at <http://localhost:5173>. API liveness is at <http://localhost:8000/api/v1/health>; readiness is at <http://localhost:8000/api/v1/health/ready>.

The table command is idempotent: it creates `{DYNAMODB_TABLE_PREFIX}-products` with `CreatedAtIndex` and `StatusCreatedAtIndex`, or reports that the table already exists without deleting data. `make dynamodb-create-tables` is the equivalent Make command.

## Quality checks

```powershell
uv run --project apps/api pytest apps/api/tests
uv run --project apps/api ruff check apps/api scripts
uv run --project apps/api ruff format --check apps/api scripts
uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/app
npm --prefix=apps/web test -- --run
npm --prefix=apps/web run lint
npm --prefix=apps/web run format:check
npm --prefix=apps/web run build
docker compose config --quiet
```

The equivalent shortcuts are `make test`, `make lint`, `make typecheck-api`, and `make build-web`. See [local development](docs/development/local-setup.md) for service lifecycle and troubleshooting.

## Current scope

The backend now contains the foundational product entity, validation schemas, DynamoDB repository, serialization, opaque cursors, and local products-table script. No product API routes or frontend product pages exist. Uploads, file processing, AI logic, review workflows, authentication, real AWS resources, and deployment pipelines remain unimplemented.

## Documentation

- [SPEC-001](docs/specs/SPEC-001-project-repository-foundation.md)
- [SPEC-002](docs/specs/SPEC-002-product-domain-model-and-dynamodb-access-patterns.md)
- [System overview](docs/architecture/system-overview.md)
- [DynamoDB data model](docs/architecture/dynamodb-data-model.md)
- [AWS serverless architecture](docs/architecture/aws-serverless-architecture.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
