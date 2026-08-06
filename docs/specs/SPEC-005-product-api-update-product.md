# SPEC-005 — Product API: Update Product

## Status

Completed

## Objective

Expose the existing optimistic DynamoDB update capability through one safe partial-update API endpoint.

## User Story

As an API consumer, I want to update selected fields of an existing product using the version I last read so concurrent changes are not silently overwritten.

## Scope

Implement only `PATCH /api/v1/products/{product_id}` with a required positive expected version, at least one explicitly supplied editable field, immutable-field protection, and a complete `ProductRecord` response.

## Out of Scope

Deletion, restoration, PUT replacement, bulk updates, lifecycle transition rules, frontend product editing, dashboards, search, uploads, file processing, AI, technical attributes, authentication, authorization, and deployment are excluded.

## Functional Requirements

- Retrieve the existing product before updating it.
- Apply only explicitly supplied editable fields.
- Require a positive expected `version` and pass it to the repository update operation.
- Preserve identity, creation timestamp, source count, and every unspecified field.
- Permit explicit null only for manufacturer, model number, and description.
- Return the complete updated public record after the repository increments version and refreshes `updatedAt`.
- Preserve missing-product, stale-version, storage, validation, and unexpected error conventions.

## Non-Functional Requirements

The route remains thin, merge behavior remains outside HTTP code, the service remains independent of FastAPI and Boto3, the immutable domain entity is never mutated in place, and no unrelated access pattern or dependency is added.

## Existing Dependencies

SPEC-005 reuses `Product`, `ProductUpdate`, `ProductRecord`, product enums, `ProductRepository.get_by_id`, `ProductRepository.update`, `DynamoDBProductRepository` optimistic concurrency, dependency providers, request-ID middleware, and global safe errors from SPEC-001 through SPEC-004.

## Service-Layer Design

`ProductService.update_product(product_id, request) -> Product` retrieves the current entity, raises `ProductNotFoundError` when absent, derives an immutable replacement with only `request.model_fields_set` editable values, and calls `repository.update(candidate, expected_version=request.version)`. Controlled repository errors are preserved.

## API Contract

`PATCH /api/v1/products/{product_id}` accepts a UUID and camelCase `ProductUpdate`, returns HTTP 200 with `ProductRecord`, and documents 404, 409, 422, and 503 responses. Existing POST and GET operations remain unchanged; PUT and DELETE are not mounted.

## Update Semantics

Editable fields are `name`, `manufacturer`, `modelNumber`, `category`, `status`, and `description`. Missing fields retain their stored values. Explicit null clears manufacturer, model number, or description. Null name, category, or status is rejected. A request with only `version` is rejected. Supplying the same current value is accepted and still performs an update.

## Optimistic Concurrency

The request `version` is the expected stored version, not the requested result version. The repository conditionally updates only when it matches, assigns exactly `expected_version + 1`, and refreshes `updatedAt`. Conflicts are not retried and map to HTTP 409.

## Immutable Fields

`productId`, `createdAt`, `updatedAt`, `sourceCount`, and `entityType` are rejected by the extra-forbid request model. `product_id`, `created_at`, and `source_count` are preserved during merging. The result version and update timestamp remain repository-managed.

## Error Handling

- Missing product: HTTP 404, `PRODUCT_NOT_FOUND`.
- Stale expected version: HTTP 409, `PRODUCT_VERSION_CONFLICT`.
- Invalid UUID, body, version, editable value, null, extra field, or no-op body: HTTP 422, `REQUEST_VALIDATION_FAILED`.
- Repository failure: HTTP 503, `PRODUCT_STORAGE_UNAVAILABLE`.
- Unexpected failure: HTTP 500, `INTERNAL_SERVER_ERROR`.

## Validation Rules

Version is required, integer, non-boolean, and at least 1. At least one editable field must be explicitly supplied. Existing name and text lengths, enum values, whitespace normalization, alias generation, and unknown-field rejection remain active. Supplied-field tracking distinguishes omission from null.

## Security Considerations

The UUID, version, fields, lengths, enums, and nullability are validated. Client field names never become DynamoDB expressions. Immutable and unknown fields are rejected. Responses and errors expose no table names, condition expressions, stored records, raw dictionaries, or AWS metadata. CORS remains unchanged.

## Logging Requirements

Emit safe structured update-requested, updated, not-found, and version-conflict events using product ID, expected/result version, status, and sorted updated field names only. Never log field values, descriptions, full bodies or records, persistence responses, credentials, table names, or client-facing stack traces.

## Edge Cases

- A request containing only version is rejected, but an explicitly supplied same-value field is updated and advances the version.
- Explicit null and a missing nullable field have different meanings.
- Concurrent deletion may surface as not found from the repository update.
- Concurrent modification returns conflict and does not overwrite stored data.
- Invalid UUIDs and forbidden system-managed aliases return the standard validation envelope.

## Acceptance Criteria

All 51 criteria from the approved SPEC-005 request must pass, including request validation, explicit-field merge semantics, immutable preservation, optimistic concurrency, exact routing/OpenAPI, stable errors, focused regression coverage, all backend/frontend quality gates, completed documentation/checklist, and a clean scope audit.

## Test Plan

Add schema tests for version, editable-field presence, nullability, aliases, forbidden fields, normalization, and enums. Add service tests for single/multiple/same-value updates, preservation, nullable clearing, repository arguments, missing records, and controlled errors. Add API tests for successful variants, version advancement/timestamp refresh, validation, missing/conflict/storage/unexpected failures, route safety, and exact OpenAPI. Run the complete backend suite with coverage, Ruff, strict mypy, unchanged frontend tests, ESLint, Prettier, Vite build, and Git whitespace/scope checks.

## Implementation Notes

Refine the existing unused `ProductUpdate` model rather than introduce a duplicate request model. Use `dataclasses.replace` to re-run domain validation while preserving immutable values. The existing repository already performs conditional update, missing-versus-conflict resolution, version increment, and timestamp refresh, so no repository change is planned.

## Completion Record

Completed on 2026-08-06. Refined `ProductUpdate`, added the single approved PATCH route and service merge operation, reused the existing conditional repository update, mapped version conflicts safely, and added schema, service, API, failure, route-safety, and OpenAPI coverage. No repository changes or new dependencies were required.

Verification passed: 144 backend tests with 1 optional DynamoDB Local test skipped and 93.67% coverage; Ruff lint and formatting; strict mypy across 36 source files; 1 unchanged frontend test; ESLint; Prettier; Vite production build; Docker Compose configuration; and Git whitespace/scope inspection. All 51 acceptance criteria passed, and no out-of-scope feature was implemented.
