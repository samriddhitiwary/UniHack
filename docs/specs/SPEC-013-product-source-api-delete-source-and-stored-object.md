# SPEC-013 — Product Source API: Delete Source and Stored Object

## Status

Completed

## Objective

Delete one product-scoped source with optimistic concurrency and remove its stored object when the source is file-backed.

## User Story

As an API consumer, I can delete a source using the version I last retrieved, without deleting another product's source or leaving an intentionally deleted file behind after successful metadata deletion.

## Scope

- `DELETE /api/v1/products/{product_id}/sources/{source_id}?version={version}`
- Parent and composite-key source validation
- Service pre-check and repository conditional version enforcement
- ObjectStorage deletion for PDF, IMAGE, and CSV sources
- Storage bypass for TEXT sources
- Safe consistency errors, logging, tests, OpenAPI, and documentation

## Out of Scope

Bulk/cascade deletion, soft delete, restore, trash, orphan cleanup workers, download, replacement, processing/retry, parsing, OCR, AI, frontend work, authentication, S3, deployment, and placeholders for those capabilities.

## Functional Requirements

1. Require UUID product/source path parameters and a positive integer `version` query parameter.
2. Verify the parent before composite-key source retrieval.
3. Reject a stale pre-check before any storage or repository deletion.
4. Delete file-backed objects through `ObjectStorage`; skip storage for TEXT.
5. Conditionally delete metadata through `ProductSourceRepository`.
6. Return an empty HTTP 204 only after all required deletion steps succeed.

## Non-Functional Requirements

Keep the route thin and the service independent from FastAPI, Boto3, concrete storage, and direct filesystem operations. Preserve safe errors and high-signal consistency logging without keys or paths.

## Existing Dependencies

- `ProductSource`, `ProductSourceType`, and stored version
- `ProductRepository.get_by_id`
- `ProductSourceRepository.get_by_id` and conditional `delete`
- `ObjectStorage.delete`
- `LocalObjectStorage` object/sidecar deletion semantics
- SPEC-006 deletion and SPEC-012 concurrency conventions
- Existing dependency injection, exception envelope, request IDs, logging, and OpenAPI tests

## Delete API Contract

`DELETE /api/v1/products/{product_id}/sources/{source_id}` requires query parameter `version` with no default and minimum 1. Success is HTTP 204 with no body or deleted record.

## Product and Source Validation

The service checks `ProductRepository.get_by_id` first, then calls `ProductSourceRepository.get_by_id(product_id, source_id)`. Missing parents short-circuit all source/storage work. Missing and cross-product sources return the same safe source 404.

## File-Backed vs Text Sources

PDF, IMAGE, and CSV are file-backed and must have a logical `storage_key`; their object is deleted exactly once through the storage protocol. TEXT has no key and never calls storage. A file-backed record without a key raises `ProductSourceStorageConsistencyError` and retains its metadata.

## Delete Ordering

The service verifies the parent, retrieves the source, compares its version, deletes a required object, and finally performs conditional metadata deletion. Metadata-first ordering is rejected because a later storage failure would create a less discoverable orphan.

## Optimistic Concurrency

The service compares the retrieved version before storage deletion. The repository still atomically requires the same expected version to protect the race after the pre-check. Neither conflict is retried or weakened.

## Object Storage Behaviour

Only `ObjectStorage.delete(storage_key)` is used. Missing objects raise the existing `ObjectNotFoundError`, map through `ObjectStorageError` to `503 OBJECT_STORAGE_UNAVAILABLE`, and prevent metadata deletion because storage contradicts the source record. Local storage owns object and sidecar cleanup.

## Repository Behaviour

The existing composite-key conditional delete is reused unchanged. It requires record existence and matching version, distinguishes missing from stale records, uses no scan, and performs no unconditional deletion.

## Failure and Consistency Strategy

Storage failure leaves metadata intact and returns failure. If object deletion succeeds but repository deletion fails or detects a final race, the repository error remains primary, success is not returned, and `product_source.delete_consistency_risk` is logged without the key. The deleted bytes cannot be recreated and the metadata remains; this architecture has no distributed transaction.

## Error Handling

- `404 PRODUCT_NOT_FOUND`
- `404 PRODUCT_SOURCE_NOT_FOUND`
- `409 PRODUCT_SOURCE_VERSION_CONFLICT`
- `422 REQUEST_VALIDATION_FAILED`
- `503 PRODUCT_STORAGE_UNAVAILABLE`
- `503 PRODUCT_SOURCE_STORAGE_UNAVAILABLE`
- `503 OBJECT_STORAGE_UNAVAILABLE`
- `500 INTERNAL_SERVER_ERROR` for corrupt file-backed metadata or unexpected failures

## Logging Requirements

Log requested, object-started/completed, deleted, not-found, pre/final conflict, failure, and consistency-risk events with product/source IDs, source type, expected version, and whether object deletion was required. Never log object keys, paths, filenames, checksums, content, raw repository/storage responses, or exception payloads.

## Security Considerations

Enforce UUIDs, positive required version, product scope, pre-check plus atomic version enforcement, type-derived storage deletion, server-owned keys, no wildcard/prefix deletion, safe errors, and unchanged CORS. Do not expose local paths or add authorization in this specification.

## Edge Cases

- Missing/invalid version fails before service invocation.
- TEXT ignores storage entirely.
- File-backed metadata without a key is an internal consistency failure.
- Missing object is a storage inconsistency, not a missing source.
- Final conditional failure may occur after bytes are removed.
- Repository failure after TEXT deletion has no object consistency risk.

## Acceptance Criteria

All 78 authoritative acceptance criteria must pass, including the exact endpoint, storage/type behavior, concurrency checks, empty 204, controlled errors, six-operation OpenAPI surface, complete verification, documentation, and scope audit.

## Test Plan

- Service tests for TEXT/PDF/IMAGE/CSV, parent/source isolation, pre/final conflicts, missing keys/objects, storage/repository/unexpected failures, consistency-risk logging, and dependency boundaries.
- API tests for empty 204, required/positive version, UUIDs, missing records, conflicts, safe infrastructure/internal failures, and request IDs.
- Temporary local-storage integration proving object and sidecar removal plus TEXT storage bypass and fake metadata deletion.
- Existing repository regression tests and exact six-operation OpenAPI verification.
- Full backend, coverage, Ruff, mypy, unchanged frontend, build, Compose, whitespace, and scope checks.

## Implementation Notes

The repository and storage protocols already provide the required operations. Implementation is limited to a consistency exception/mapping, one service workflow, one route, test fakes/scenarios, and documentation.

## Completion Record

Completed on 2026-08-07. The API now deletes one product-scoped source with a required version, service pre-check, repository conditional delete, file-backed object/sidecar cleanup, TEXT storage bypass, and safe consistency-risk handling.

Verification passed: 520 backend tests passed and 2 skipped with 92.48% coverage; Ruff lint and formatting passed; strict mypy passed for 53 source files; the unchanged frontend test, ESLint, Prettier, and Vite build passed; Docker Compose configuration and Git whitespace checks passed. All 78 acceptance criteria passed, and the scope audit found no bulk/cascade deletion, soft delete, restore, download, replacement, cleanup worker, processing/retry, parsing, OCR, AI, frontend deletion UI, authentication, S3, or deployment implementation.
