# CatalogIQ AI

CatalogIQ AI is a JavaScript React frontend and Python FastAPI backend prepared for a cost-conscious AWS serverless deployment. The repository implements SPEC-001 through **SPEC-011: Product Source API — List and Retrieve Sources**.

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

The table command is idempotent: it creates `{DYNAMODB_TABLE_PREFIX}-products` with `CreatedAtIndex` and `StatusCreatedAtIndex`, plus `{DYNAMODB_TABLE_PREFIX}-sources` with `ProductCreatedAtIndex`, or reports that either table already exists without deleting data. `make dynamodb-create-tables` is the equivalent Make command.

`STORAGE_BACKEND=local` selects development-only filesystem storage. `LOCAL_STORAGE_ROOT=../../storage` is resolved from `apps/api`, and the root is created when storage is first requested. Stored objects use generated logical keys, streamed writes, SHA-256 metadata, size enforcement, exclusive no-overwrite finalization, and path-containment checks. There is no S3 implementation. See the [object-storage architecture](docs/architecture/object-storage.md).

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

The backend contains foundational product and product-source metadata entities, DynamoDB repositories, and provider-independent object storage. Product APIs support create/list/retrieve/update/delete. Product-source APIs create normalized text sources, accept validated local file uploads, list a product's sources, and retrieve one product-scoped source. Source update/delete and file download are not exposed. No S3, extraction, processing, frontend source UI, authentication, real AWS resources, or deployment pipeline exists.

## Product API

With DynamoDB Local and the products table running:

```text
POST /api/v1/products
GET  /api/v1/products?limit=20&status=DRAFT
GET  /api/v1/products/{product_id}
PATCH /api/v1/products/{product_id}
DELETE /api/v1/products/{product_id}?version=1
POST /api/v1/products/{product_id}/sources/text
POST /api/v1/products/{product_id}/sources/upload
GET  /api/v1/products/{product_id}/sources?limit=20
GET  /api/v1/products/{product_id}/sources/{source_id}
```

Create returns HTTP 201; list, retrieve, and update return HTTP 200; delete returns an empty HTTP 204. PATCH and DELETE use the client’s current positive version for optimistic concurrency. The list limit defaults to 20 and is bounded at 100, and continuation cursors are opaque. Requests and responses use camelCase JSON. See the [Product API documentation](docs/api/products.md) for examples and stable error codes.

Text-source creation returns HTTP 201 after confirming the parent product. It stores normalized plain text with a UTF-8 size and SHA-256 checksum directly in source metadata and does not use filesystem/object storage. See the [Product Source API documentation](docs/api/product-sources.md).

The multipart upload endpoint validates and streams PDF, PNG, JPEG, WEBP, or CSV through configured object storage. It returns server-derived size/checksum metadata and compensates by deleting the object if source persistence fails. Local storage remains development-only.

Source listing verifies the parent and returns metadata newest first with a limit from 1 through 100 and a product-bound opaque cursor. Source retrieval also verifies the parent and uses the product/source composite key, so a source cannot be discovered through another product's path. Empty lists return `items: []` and `nextCursor: null`; neither read endpoint accesses object storage or returns file bytes.

## Documentation

- [SPEC-001](docs/specs/SPEC-001-project-repository-foundation.md)
- [SPEC-002](docs/specs/SPEC-002-product-domain-model-and-dynamodb-access-patterns.md)
- [SPEC-003](docs/specs/SPEC-003-product-api-create-and-retrieve.md)
- [SPEC-004](docs/specs/SPEC-004-product-api-list-products.md)
- [SPEC-005](docs/specs/SPEC-005-product-api-update-product.md)
- [SPEC-006](docs/specs/SPEC-006-product-api-delete-product.md)
- [SPEC-007](docs/specs/SPEC-007-product-source-domain-model-and-dynamodb-access-patterns.md)
- [SPEC-008](docs/specs/SPEC-008-local-object-storage-foundation.md)
- [SPEC-009](docs/specs/SPEC-009-product-source-api-create-text-source.md)
- [SPEC-010](docs/specs/SPEC-010-product-source-api-local-file-upload.md)
- [SPEC-011](docs/specs/SPEC-011-product-source-api-list-and-retrieve-sources.md)
- [Product API](docs/api/products.md)
- [Product Source API](docs/api/product-sources.md)
- [System overview](docs/architecture/system-overview.md)
- [DynamoDB data model](docs/architecture/dynamodb-data-model.md)
- [Object storage](docs/architecture/object-storage.md)
- [AWS serverless architecture](docs/architecture/aws-serverless-architecture.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
