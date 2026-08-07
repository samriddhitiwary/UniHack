# SPEC-012 — Product Source API: Update Source Metadata and Status

## Status

Completed

## Objective

Expose one safe, product-scoped partial-update workflow for approved source metadata and status using optimistic concurrency.

## User Story

As an API consumer, I can update a source display name, processing status, or error message without replacing its content or overwriting a newer update.

## Scope

- `PATCH /api/v1/products/{product_id}/sources/{source_id}`
- A dedicated strict update request containing required `version` and at least one approved field
- Explicit status-transition validation
- Product and composite-key source validation
- Existing repository conditional update behavior
- Safe errors, structured logging, tests, OpenAPI, and documentation

## Out of Scope

Source deletion, file/text replacement, upload replacement, download, processing/retry jobs, parsing, OCR, AI, frontend editing, authentication, S3, deployment, and placeholders for those capabilities.

## Functional Requirements

1. Accept only `version`, `displayName`, `status`, and `errorMessage`.
2. Require a positive strict-integer version and at least one explicitly supplied editable field.
3. Preserve omitted values and clear nullable values when explicitly set to null or normalized from blank text.
4. Validate direct status transitions and allow same-status writes.
5. Validate the parent and source before merging and conditionally updating.
6. Return the updated camel-case `ProductSourceRecord` with HTTP 200.

## Non-Functional Requirements

Routes remain thin. The update workflow contains no FastAPI, Boto3, filesystem, or object-storage access. Repository errors remain controlled, client responses remain safe, and no scan or new index is introduced.

## Existing Dependencies

- Immutable `ProductSource` entity and `ProductSourceStatus`
- `ProductRepository.get_by_id`
- `ProductSourceRepository.get_by_id` and `update`
- DynamoDB conditional update from SPEC-007
- Explicit-field merge semantics from SPEC-005
- Existing source dependency injection, response schema, exception envelope, request ID, logging, and OpenAPI conventions

## Update Request Contract

`ProductSourceUpdate` requires strict integer `version >= 1` and at least one of `displayName`, `status`, or `errorMessage`. Unknown and immutable fields are rejected. The model uses camel-case aliases externally and tracks explicitly supplied fields.

## Editable Fields

- `display_name` / `displayName`
- `status`
- `error_message` / `errorMessage`

## Immutable Fields

`sourceId`, `productId`, `sourceType`, `originalFilename`, `storageKey`, `mimeType`, `fileSizeBytes`, `checksumSha256`, `textContent`, `createdAt`, `updatedAt`, and the stored `version` are not request fields. Identity, content, file metadata, and creation time are preserved by immutable-entity merge and repository update behavior.

## Explicit Null Semantics

Omitted editable fields remain unchanged. Explicit null or blank `displayName` clears the display name. Explicit null or blank `errorMessage` clears the error. `status: null` is invalid. The required request `version` is never merged into the entity.

## Status Transition Rules

Approved direct transitions are `PENDING → READY`, `PENDING → FAILED`, `READY → PROCESSING`, `READY → FAILED`, `PROCESSING → COMPLETED`, `PROCESSING → FAILED`, and `FAILED → READY`. `COMPLETED` has no outgoing transition. Same-status updates are allowed and advance the version. No intermediate transition is inferred.

Transitioning from `FAILED` to `READY` or from `PROCESSING` to `COMPLETED` clears `errorMessage` deterministically, including when the request supplies another error value, because retaining an error after recovery/completion is misleading. Other updates retain an omitted error message.

## Product and Source Validation

The service verifies the parent product first, then retrieves with both product and source UUIDs. A missing parent short-circuits source access with `PRODUCT_NOT_FOUND`. A missing or cross-product source returns the same `PRODUCT_SOURCE_NOT_FOUND` response.

## Optimistic Concurrency

The client version is passed unchanged as `expected_version`. DynamoDB atomically requires the stored version to match, sets the version to `expected_version + 1`, and refreshes UTC `updatedAt`. Conflicts are not retried and return `PRODUCT_SOURCE_VERSION_CONFLICT` without overwriting newer data.

## Service-Layer Design

`ProductSourceService.update_source` validates the parent, performs composite-key retrieval, validates a supplied status, merges only explicitly supplied editable fields with `dataclasses.replace`, applies deterministic error clearing, then calls repository `update` exactly once. Controlled errors pass through unchanged.

## Repository Behaviour

The existing repository method is reused unchanged. Its conditional expression requires record existence and matching version; its update expression writes mutable metadata plus server-managed timestamp/version while retaining identity and immutable file/content fields.

## Error Handling

- `404 PRODUCT_NOT_FOUND`
- `404 PRODUCT_SOURCE_NOT_FOUND`
- `409 PRODUCT_SOURCE_VERSION_CONFLICT`
- `409 PRODUCT_SOURCE_STATUS_TRANSITION_INVALID`
- `422 REQUEST_VALIDATION_FAILED`
- `503 PRODUCT_STORAGE_UNAVAILABLE`
- `503 PRODUCT_SOURCE_STORAGE_UNAVAILABLE`
- `500 INTERNAL_SERVER_ERROR`

## Logging Requirements

Log update request, success, not-found, transition-rejection, version-conflict, and controlled-failure events using product/source IDs, expected version, statuses, and sorted editable field names. Never log error-message content, source records, filenames, keys, checksums, database expressions, tables, or raw exception payloads.

## Security Considerations

Enforce UUIDs, strict positive version, composite-key isolation, strict request allowlist, immutable-field rejection, transition rules, atomic concurrency, safe errors, and unchanged CORS. Do not access storage or expose paths/database responses.

## Edge Cases

- Version-only and empty bodies are invalid.
- Explicit null differs from omission.
- Same-status writes are accepted and versioned.
- Invalid transitions fail before repository update.
- Cross-product IDs are indistinguishable from absent sources.
- Repository conflict after a successful pre-read remains authoritative.

## Acceptance Criteria

All 80 acceptance criteria from the authoritative SPEC-012 request must pass, including schema strictness, transition matrix, deterministic error clearing, product/source isolation, optimistic concurrency, immutable preservation, five-operation OpenAPI scope, full checks, documentation, and scope control.

## Test Plan

- Schema tests for version, editable allowlist, immutable/unknown rejection, nulls, blanks, and multi-field requests.
- Transition tests for every allowed/rejected pair, same-status behavior, and deterministic error clearing.
- Service tests for merge semantics, immutable preservation, parent/source isolation, expected version, conflict/failure propagation, and dependency boundaries.
- API tests for success, validation, null clearing, transitions, missing records, UUIDs, stale writes, safe failures, request IDs, and exact OpenAPI operations.
- Existing repository regression tests plus full backend, frontend, lint, formatting, typing, build, Compose, whitespace, and scope checks.

## Implementation Notes

The existing repository update contract is sufficient and should remain unchanged. The current broad repository-boundary `ProductSourceUpdate` model will become the focused public PATCH request because no runtime repository code depends on it; schema tests will be updated to the new API contract.

## Completion Record

Completed on 2026-08-07. The API now exposes one product-scoped PATCH workflow with a strict editable-field allowlist, explicit-null merge behavior, direct status-transition validation, deterministic stale-error clearing, and repository-managed optimistic concurrency.

Verification passed: 484 backend tests passed and 2 skipped with 92.27% coverage; Ruff lint and formatting passed; strict mypy passed for 53 source files; the unchanged frontend test, ESLint, Prettier, and Vite build passed; Docker Compose configuration and Git whitespace checks passed. All 80 acceptance criteria passed, and the scope audit found no source deletion, content/file replacement, download, storage mutation in the update workflow, processing/retry job, parsing, OCR, AI, frontend editing, authentication, S3, or deployment implementation.
