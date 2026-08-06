# SPEC-003 — Product API: Create and Retrieve Product

## Status

Completed

## Objective

Expose the existing product domain and repository through exactly two versioned HTTP operations: create a foundational product and retrieve one product by UUID.

## User Story

As a catalogue operator, I want to create a foundational industrial product and retrieve it by its identifier so later workflows can reference a validated, persistently stored record.

## Scope

- A focused application service with `create_product` and `get_product`.
- FastAPI dependency providers for the DynamoDB repository and product service.
- `POST /api/v1/products` and `GET /api/v1/products/{product_id}` only.
- Stable camelCase request, response, validation, and product error contracts.
- Safe request identifiers, global exception mapping, and product event logging.
- Service, API, validation, error, and OpenAPI tests.

## Out of Scope

Product list, update, delete, frontend pages/forms, authentication, authorization, uploads, extraction, S3, AI, technical attributes, validation/review workflows, scores, dashboards, search, export, batch processing, deployment, and CI/CD.

## Functional Requirements

1. Accept only the approved create fields and generate all system-managed fields in the domain layer.
2. Persist through `ProductRepository`, never directly from a route.
3. Return the persisted record with HTTP 201 and camelCase public fields.
4. Validate retrieve identifiers as UUIDs and return a matching product with HTTP 200.
5. Convert missing, duplicate, persistence, validation, and unexpected failures into stable safe envelopes.
6. Add request IDs to error envelopes and response headers.
7. Generate accurate OpenAPI for both—and only both—product operations.

## Non-Functional Requirements

- Preserve the SPEC-001 router/configuration structure and SPEC-002 domain/repository contracts.
- Keep route functions thin, dependencies overridable, and the service independent of FastAPI.
- Do not expose raw DynamoDB data, table names, AWS request identifiers, stack traces, or secrets.
- Maintain the existing coverage threshold, strict mypy, Ruff, and frontend checks.

## Existing Dependencies

SPEC-003 reuses `Product`, `ProductCategory`, `ProductStatus`, `ProductCreate`, `ProductRecord`, `ProductRepository`, `DynamoDBProductRepository`, configured Boto3 client creation, Pydantic Settings, and controlled repository exceptions. No new third-party dependency is required.

## Service-Layer Design

`ProductService` accepts a `ProductRepository` protocol. `create_product` accepts `ProductCreate`, constructs `Product.create`, persists it, and returns the stored domain entity. `get_product` accepts a UUID, returns the stored entity, and raises `ProductNotFoundError` when the repository returns `None`. It contains no HTTP or FastAPI imports and preserves repository exceptions.

## API Contracts

- `POST /api/v1/products`: camelCase `ProductCreate` body; returns camelCase `ProductRecord`, HTTP 201.
- `GET /api/v1/products/{product_id}`: UUID path; returns the same `ProductRecord`, HTTP 200.
- Both expose documented 422 validation and 503 persistence responses; create documents 409 and retrieve documents 404.
- No list, update, or delete operation is mounted.

## Dependency Injection

A cached low-level DynamoDB client uses the existing deployment-aware settings. `get_product_repository` constructs the configured repository using `{prefix}-products`; `get_product_service` receives the protocol dependency and constructs the service. Routes depend only on `get_product_service`, and tests override it.

## Error Handling

Global handlers return:

- `ProductNotFoundError`: 404, `PRODUCT_NOT_FOUND`.
- `ProductAlreadyExistsError`: 409, `PRODUCT_ALREADY_EXISTS`.
- Other `ProductRepositoryError`: 503, `PRODUCT_STORAGE_UNAVAILABLE`.
- FastAPI request validation: 422, `REQUEST_VALIDATION_FAILED`.
- Unexpected exception: 500, `INTERNAL_SERVER_ERROR`.

Each envelope contains `error.code`, a stable generic `error.message`, safe `error.details`, and `requestId`. The persistence handler logs once and never returns exception text.

## Validation Rules

Existing Pydantic/domain validation enforces names, optional-text normalization, allowed enums, description lengths, extra-field rejection, immutable system fields, and UUID path parsing. A shared alias generator exposes camelCase while continuing to accept internal snake_case construction.

## Security Considerations

Clients cannot choose IDs, statuses, counts, timestamps, versions, table names, expressions, or AWS options. Request bodies and descriptions are not logged. CORS is changed only to add the required POST method to existing configured origins. Error responses contain no infrastructure metadata.

## Logging Requirements

The service records concise `product.created`, `product.retrieved`, and `product.not_found` events using product ID/category only. The repository error handler records `product.persistence_failed` once with request ID and exception type. Unexpected failures are logged once server-side while client responses remain generic.

## Edge Cases

- Blank/one-character names, invalid categories, excessive descriptions, unknown fields, and client-supplied system fields.
- Empty optional values and case-preserving model numbers.
- Malformed UUID paths and absent products.
- UUID collision surfaced as duplicate conflict.
- Repository outage or corrupt persistence response without AWS leakage.
- OpenAPI drift or accidental mounting of unsupported HTTP methods.

## Acceptance Criteria

All 36 criteria from the approved SPEC-003 request must pass, including the two exact routes, service/protocol separation, dependency overrides, error mapping, OpenAPI accuracy, backend/frontend quality gates, complete documentation/checklist, and a clean out-of-scope scan.

## Test Plan

- Unit-test service creation/defaults/repository calls/returned values and all preserved errors with a fake repository.
- API-test valid create/retrieve, camelCase models, normalization, validation, system/extra-field rejection, duplicate/not-found/storage errors, request IDs, and absence of infrastructure leakage.
- Inspect generated OpenAPI for operations, models, UUID/enums, status responses, and the absence of list/update/delete product methods.
- Run all backend tests/coverage, Ruff lint/format, strict mypy, frontend tests/lint/format/build, Compose validation, and scope scans.

## Implementation Notes

The API alias change is non-breaking internally because schemas accept both field names and aliases. Product HTTP errors use dedicated global handlers; the existing readiness endpoint retains its SPEC-001 response contract. Normal API tests use service dependency overrides and require no DynamoDB.

## Completion Record

Completed on 2026-08-06.

- Implemented `ProductService` over the repository protocol, deployment-aware repository/service dependency providers, generated request IDs, safe global API error mappings, and concise product event logging.
- Implemented only `POST /api/v1/products` and `GET /api/v1/products/{product_id}` with stable camelCase `ProductRecord` responses and accurate OpenAPI documentation.
- Added 22 focused service/API tests covering successful contracts, defaults, normalization, validation, duplicate/missing/storage/unexpected errors, request IDs, leakage prevention, and OpenAPI route/schema assertions.
- Full backend result: 75 passed, one opt-in DynamoDB Local repository test skipped, 93.11% coverage.
- Ruff lint passed; Ruff formatting confirmed 55 files formatted; strict mypy passed all 36 source files.
- Existing frontend Vitest, ESLint, Prettier, and Vite production build checks passed unchanged; Docker Compose validation passed.
- Scope scan confirmed no product list/update/delete operation, product frontend, upload, S3, PDF/AI extraction, authentication, dashboard, search, or deployment implementation.
- All 36 acceptance criteria passed. SPEC-004 was not started.
