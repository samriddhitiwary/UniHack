# SPEC-006 — Product API: Delete Product

## Status

Completed

## Objective

Expose one safe product deletion endpoint protected by optimistic concurrency.

## User Story

As an API consumer, I want to delete an existing product using the version I last retrieved so a stale client cannot remove newer data.

## Scope

Implement only `DELETE /api/v1/products/{product_id}` with a required positive `version` query parameter, conditional persistence deletion, and an empty HTTP 204 response.

## Out of Scope

Soft deletion, restore, archive, cascading or bulk deletion, audit records, source or file cleanup, frontend deletion UI, uploads, AI, technical attributes, authentication, authorization, dashboards, search, and deployment are excluded.

## Functional Requirements

- Validate the product UUID and required positive expected version.
- Retrieve the product before deletion and return not found when absent.
- Delete atomically only when the stored version matches.
- Return conflict for stale deletion attempts without deleting newer data.
- Return HTTP 204 with zero response-body bytes after success.
- Preserve every existing product operation and safe error convention.

## Non-Functional Requirements

The route remains thin, the service remains independent of FastAPI and Boto3, persistence retains race protection, no scan/index/dependency is introduced, and internal storage details remain private.

## Existing Dependencies

SPEC-006 reuses the product domain, repository protocol, DynamoDB conditional operations, `ProductService`, dependency providers, UUID/query validation, `ProductNotFoundError`, `ProductVersionConflictError`, global exception handlers, request-ID middleware, and OpenAPI conventions from SPEC-001 through SPEC-005.

## Service-Layer Design

`ProductService.delete_product(product_id, expected_version) -> None` logs safe request metadata, retrieves through the repository, raises `ProductNotFoundError` when absent, calls `repository.delete(product_id, expected_version)`, preserves controlled errors, and returns `None` after success.

## API Contract

`DELETE /api/v1/products/{product_id}?version={positive_integer}` returns HTTP 204 without a response model or body. It documents 404, 409, 422, and 503. Existing POST, GET, and PATCH operations remain unchanged; collection DELETE, restore aliases, and PUT remain absent.

## Delete Semantics

Deletion is permanent for the product record. Deleting an absent or already deleted product returns 404 rather than idempotent success. No related resources, files, sources, audit records, or external objects are deleted.

## Optimistic Concurrency

The service pre-read establishes an early missing-product result. The repository still performs `DeleteItem` with `attribute_exists(productId) AND version = expectedVersion`, protecting the race between read and delete. A conditional failure triggers a consistent read: absence maps to not found; continued existence maps to version conflict. No retry or last-write-wins behavior is allowed.

## Error Handling

- Missing product: HTTP 404, `PRODUCT_NOT_FOUND`.
- Stale expected version: HTTP 409, `PRODUCT_VERSION_CONFLICT`.
- Invalid UUID or missing/invalid version: HTTP 422, `REQUEST_VALIDATION_FAILED`.
- Repository failure: HTTP 503, `PRODUCT_STORAGE_UNAVAILABLE`.
- Unexpected failure: HTTP 500, `INTERNAL_SERVER_ERROR`.

## Validation Rules

`product_id` must parse as UUID. `version` is a required query integer with minimum 1 and no default. Missing, empty, zero, negative, and non-numeric versions are rejected before service invocation.

## Security Considerations

Deletion is by validated UUID only, requires a positive version, and uses a server-defined conditional expression. Clients cannot supply expressions, indexes, filters, table names, or arbitrary delete criteria. Errors expose no condition expression, record, table name, request metadata, or AWS details. Existing CORS behavior remains unchanged.

## Logging Requirements

Emit safe structured requested, deleted, not-found, and version-conflict events using only product ID, expected version, and already-read category. Never log full records, descriptions, raw persistence responses, condition expressions, credentials, table names, or client-facing stack traces.

## Edge Cases

- A product may disappear after the service read; the conditional failure then maps to 404.
- A product may advance after the service read; the conditional failure maps to 409 and preserves it.
- Repeating a successful deletion returns 404.
- Invalid UUIDs and versions never reach the service or repository.
- HTTP 204 contains no JSON token, message, or deleted representation.

## Acceptance Criteria

All 48 criteria from the approved SPEC-006 request must pass, including version-aware service/repository behavior, atomic deletion, stable 204/404/409/422/503/500 contracts, exact route and OpenAPI operations, focused regression coverage, all quality gates, accurate documentation/checklist, and a clean scope audit.

## Test Plan

Add service tests for pre-read, exact conditional-delete arguments, success, missing, conflict, and persistence failures. Refine repository tests for correct version conditions, stale-versus-missing resolution, invalid versions, and wrapped failures. Add API tests for 204 bytes/headers, validation, retrieval after deletion, safe failures, unsupported routes, existing operation regression, and exact OpenAPI. Run the full backend suite with coverage, Ruff, strict mypy, unchanged frontend tests, ESLint, Prettier, Vite build, Compose, and Git whitespace/scope checks.

## Implementation Notes

The existing protocol and DynamoDB delete method lack expected-version support, so they require a minimal signature and conditional-expression correction. The update conflict-resolution helper can be generalized and reused. No schema is necessary because the approved request uses a validated query parameter.

## Completion Record

Completed on 2026-08-06. Added the single approved DELETE route and delete service operation, minimally upgraded the repository protocol and DynamoDB implementation to require an expected version, reused safe missing/conflict handling, and added focused repository, service, API, response-body, route-safety, and OpenAPI coverage. No new schema, index, or dependency was required.

Verification passed: 167 backend tests with 1 optional DynamoDB Local test skipped and 94.02% coverage; Ruff lint and formatting; strict mypy across 36 source files; 1 unchanged frontend test; ESLint; Prettier; Vite production build; Docker Compose configuration; and Git whitespace/scope inspection. All 48 acceptance criteria passed, and no out-of-scope feature was implemented.
