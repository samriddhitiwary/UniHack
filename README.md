# CatalogIQ AI

CatalogIQ AI is a JavaScript React frontend and Python FastAPI backend prepared for a cost-conscious AWS serverless deployment. The repository implements SPEC-001 through **SPEC-020: OCR and Nameplate Text Recognition Engine**.

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

The table command is idempotent: it creates the configured products, sources, processing-jobs, extraction-results, table-extraction-results, csv-processing-results, image-analysis-results, and image-ocr-results tables with only their documented indexes, or reports that a table already exists without deleting data. `make dynamodb-create-tables` is the equivalent Make command.

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

The backend contains product, product-source, processing-job, object-storage, PDF extraction, CSV processing, image-analysis, and local image-OCR foundations. Processing-job APIs create and read records but expose no execution endpoint. Processing engines are invoked directly in backend code, store evidence separately, and update job lifecycle without changing source status. Content/file replacement, bulk deletion, restore, and download are not exposed. No product classification, structured attribute extraction, unit normalization, hosted OCR/AI, S3, workers, frontend processing UI, authentication, real AWS resources, or deployment pipeline exists.

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
PATCH /api/v1/products/{product_id}/sources/{source_id}
DELETE /api/v1/products/{product_id}/sources/{source_id}?version=1
POST /api/v1/products/{product_id}/sources/{source_id}/jobs
GET  /api/v1/processing-jobs/{job_id}
GET  /api/v1/products/{product_id}/processing-jobs?limit=20
GET  /api/v1/products/{product_id}/sources/{source_id}/jobs?limit=20
```

Create returns HTTP 201; list, retrieve, and update return HTTP 200; delete returns an empty HTTP 204. PATCH and DELETE use the client’s current positive version for optimistic concurrency. The list limit defaults to 20 and is bounded at 100, and continuation cursors are opaque. Requests and responses use camelCase JSON. See the [Product API documentation](docs/api/products.md) for examples and stable error codes.

Text-source creation returns HTTP 201 after confirming the parent product. It stores normalized plain text with a UTF-8 size and SHA-256 checksum directly in source metadata and does not use filesystem/object storage. See the [Product Source API documentation](docs/api/product-sources.md).

The multipart upload endpoint validates and streams PDF, PNG, JPEG, WEBP, or CSV through configured object storage. It returns server-derived size/checksum metadata and compensates by deleting the object if source persistence fails. Local storage remains development-only.

Source listing verifies the parent and returns metadata newest first with a limit from 1 through 100 and a product-bound opaque cursor. Source retrieval also verifies the parent and uses the product/source composite key, so a source cannot be discovered through another product's path. Empty lists return `items: []` and `nextCursor: null`; neither read endpoint accesses object storage or returns file bytes.

Source PATCH requires the last retrieved positive `version` and at least one of `displayName`, `status`, or `errorMessage`. It preserves omitted and immutable fields, distinguishes explicit null from omission, enforces direct status transitions, and returns `409` for stale versions or invalid transitions. It does not replace content, access object storage, or start processing.

Source DELETE requires the last retrieved positive `version`. It validates the parent and product-scoped source, rejects obvious stale requests before storage access, deletes file-backed objects through `ObjectStorage`, skips storage for TEXT, and conditionally deletes metadata. Success is an empty 204. The object-first strategy avoids successful metadata deletion leaving an orphan, but a final database conflict/failure can occur after bytes are removed; this risk is logged and not reported as success.

Processing-job creation accepts only `jobType`, verifies the product and product-scoped source, enforces source/job compatibility, and returns one PENDING record with HTTP 201. Retrieval and both newest-first lists return HTTP 200. List limits default to 20 and use opaque identity-bound cursors. See the [Processing Job API documentation](docs/api/processing-jobs.md). No job starts automatically, and there are no update, cancel, retry, worker, extraction, or AI operations.

The PDF text-extraction service processes only PENDING `PDF_TEXT_EXTRACTION` jobs for stored PDF sources. It uses pypdf through `ObjectStorage.open`, preserves blank and text pages, enforces configurable bounds, stores composite META/PAGE result records, and completes even for LOW_TEXT or NO_TEXT outcomes. Scanned/image-only PDFs are identified as NO_TEXT but are not OCR-processed. There is no execution or extraction-result API. See the [PDF extraction architecture](docs/architecture/pdf-text-extraction.md).

The PDF table-extraction service processes only PENDING `PDF_TABLE_EXTRACTION` jobs. It uses pdfplumber through `ObjectStorage.open`, preserves ordered row/cell evidence and empty cells, enforces page/table/row/column/cell/text limits, and stores META/TABLE records separately. Readable PDFs without detectable tables complete as NO_TABLES. It performs no OCR, semantic joining, or AI, and exposes no execution or result API. See the [PDF table extraction architecture](docs/architecture/pdf-table-extraction.md).

The CSV processing service processes only PENDING `CSV_PROCESSING` jobs. It uses strict standard-library CSV parsing through `ObjectStorage.open`, accepts UTF-8/BOM and comma/semicolon/tab/pipe delimiters, preserves string evidence and malformed-row warnings, enforces independent limits, and stores META/ROW records separately. It performs no formula evaluation or semantic conversion and exposes no execution or result API. See the [CSV processing architecture](docs/architecture/csv-processing.md).

The image-analysis service processes only PENDING `IMAGE_ANALYSIS` jobs for stored IMAGE sources. Pillow validates PNG, JPEG, and WEBP format/MIME agreement under bounded byte, dimension, pixel, animation, and decompression-bomb controls. Results contain safe metadata, six deterministic regions, and a geometry-only nameplate-candidate heuristic in composite META/REGION records. It performs no OCR, object detection, AI vision, or attribute extraction and exposes no execution or result API. See the [image analysis architecture](docs/architecture/image-analysis.md).

The image-OCR service processes only PENDING `IMAGE_OCR` jobs after a compatible completed SPEC-019 analysis. It uses local RapidOCR ONNX Runtime models, reuses and maps deterministic regions into an oriented full-image coordinate system, and stores bounded normalized text, reading order, boxes, and integer confidence basis points in META/BLOCK records. NO_TEXT and LOW_CONFIDENCE_TEXT are successful outcomes. The nameplate-text score is deterministic and non-AI; no product category, structured attribute, or normalized unit is produced. There is no OCR execution/result API. See the [image OCR architecture](docs/architecture/image-ocr.md).

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
- [SPEC-012](docs/specs/SPEC-012-product-source-api-update-source-metadata-and-status.md)
- [SPEC-013](docs/specs/SPEC-013-product-source-api-delete-source-and-stored-object.md)
- [SPEC-014](docs/specs/SPEC-014-product-source-processing-job-domain-and-persistence.md)
- [SPEC-015](docs/specs/SPEC-015-processing-job-api-create-retrieve-and-list-jobs.md)
- [SPEC-016](docs/specs/SPEC-016-pdf-text-extraction-engine.md)
- [SPEC-017](docs/specs/SPEC-017-pdf-table-extraction-engine.md)
- [SPEC-018](docs/specs/SPEC-018-csv-processing-engine.md)
- [SPEC-019](docs/specs/SPEC-019-image-and-nameplate-analysis-foundation.md)
- [SPEC-020](docs/specs/SPEC-020-ocr-and-nameplate-text-recognition-engine.md)
- [Product API](docs/api/products.md)
- [Product Source API](docs/api/product-sources.md)
- [Processing Job API](docs/api/processing-jobs.md)
- [System overview](docs/architecture/system-overview.md)
- [DynamoDB data model](docs/architecture/dynamodb-data-model.md)
- [Object storage](docs/architecture/object-storage.md)
- [PDF text extraction](docs/architecture/pdf-text-extraction.md)
- [PDF table extraction](docs/architecture/pdf-table-extraction.md)
- [CSV processing](docs/architecture/csv-processing.md)
- [Image and nameplate analysis](docs/architecture/image-analysis.md)
- [OCR and nameplate text recognition](docs/architecture/image-ocr.md)
- [AWS serverless architecture](docs/architecture/aws-serverless-architecture.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
