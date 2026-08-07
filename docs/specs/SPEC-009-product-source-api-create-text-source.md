# SPEC-009 — Product Source API: Create Text Source

## Status

Completed

## Objective

Expose one backend endpoint that attaches normalized plain-text product information to an existing product as a persisted `TEXT` product-source record.

## User Story

As an API client, I need to attach supplier notes or other bounded plain text to an existing product so future processing can consume the source without requiring a file upload.

## Scope

Add a dedicated text-source request model, focused product-source application service, repository/service dependency providers, one create route, safe exception mappings, structured logs, focused service/API/OpenAPI tests, and API documentation.

## Out of Scope

File or multipart uploads, object-storage use, S3, source listing/retrieval/update/deletion, processing, extraction, parsing, OCR, AI, frontend work, authentication, authorization, deployment, and automatic product source-count updates are excluded.

## Functional Requirements

- Implement only `POST /api/v1/products/{product_id}/sources/text`.
- Accept exactly optional `displayName` and required `textContent`, rejecting unknown or system-managed fields.
- Normalize surrounding whitespace, convert a blank display name to `None`, and reject blank or over-50,000-character text.
- Verify the parent through `ProductRepository.get_by_id` before creating a source.
- Create `TEXT` metadata with `READY`, `text/plain`, normalized text, its UTF-8 byte size and SHA-256, null file/storage fields, version 1, and domain-generated identity/timestamps.
- Persist through `ProductSourceRepository.create` and return `ProductSourceRecord` with HTTP 201.

## Non-Functional Requirements

Routes contain only HTTP binding and response conversion. The service contains no FastAPI, Boto3, filesystem, or object-storage dependency. Existing repository protocols, DynamoDB implementations, camelCase schemas, request IDs, global error envelopes, structured logging, and existing product operations remain unchanged.

## Existing Dependencies

SPEC-009 reuses the SPEC-007 `ProductSource` entity, enums, 50,000-character text and 200-character display-name limits, public record schema, and DynamoDB repository; the existing product repository; the current FastAPI dependency, router, request-ID, exception, OpenAPI, and test conventions; and standard-library UTF-8 encoding and SHA-256.

## Service-Layer Design

`ProductSourceService` receives `ProductRepository` and `ProductSourceRepository`. `create_text_source(product_id, request)` logs a content-safe request event, checks the product, computes metadata from normalized schema values, constructs the immutable domain source, changes only the newly created status from the domain-wide `PENDING` default to `READY`, persists it, logs safe completion metadata, and returns it. Controlled repository exceptions pass unchanged.

## API Contract

`POST /api/v1/products/{product_id}/sources/text` accepts JSON `{ "displayName": string|null?, "textContent": string }`, validates `product_id` as UUID, and returns HTTP 201 with `ProductSourceRecord`. OpenAPI documents 404, 409, 422, and 503 errors. No alias or other source operation is added.

## Text Source Creation Rules

The created record always has `source_type=TEXT`, `status=READY`, `original_filename=None`, `storage_key=None`, `mime_type=text/plain`, UTF-8 byte size, lowercase SHA-256 of the same encoded normalized text, normalized display name, normalized text content, `error_message=None`, and version 1. No content is parsed, summarized, processed, or stored outside DynamoDB source metadata.

## Product Existence Validation

The service calls `ProductRepository.get_by_id(product_id)` first. Absence raises `ProductNotFoundError`; the source repository is not called. Repository failures are preserved. No scan, upsert, or route-level query is introduced.

## Dependency Injection

FastAPI providers construct `DynamoDBProductSourceRepository` from the existing client and configuration-derived sources table, then construct `ProductSourceService` from the existing product-repository provider and new source-repository provider. The route depends only on the service, and providers remain overridable in tests.

## Error Handling

Existing product errors retain `PRODUCT_NOT_FOUND`/404 and `PRODUCT_STORAGE_UNAVAILABLE`/503. `ProductSourceAlreadyExistsError` maps to `PRODUCT_SOURCE_ALREADY_EXISTS`/409; other `ProductSourceRepositoryError` values map to `PRODUCT_SOURCE_STORAGE_UNAVAILABLE`/503. Validation maps to `REQUEST_VALIDATION_FAILED`/422, and unexpected failures retain `INTERNAL_SERVER_ERROR`/500. Responses expose no persistence details.

## Validation Rules

`textContent` is a required string, stripped, nonempty, and at most 50,000 characters. `displayName` is an optional string, stripped, converted to `None` when blank, and at most 200 characters. Extra fields—including every system-managed source field—are forbidden. Null, missing, non-string, blank, and oversized text are rejected before service invocation.

## Security Considerations

Bound and type-check all text, reject client-controlled identity/type/status/storage/checksum/version/timestamps, never log or interpret content, preserve CORS, call no external service, write no filesystem object, and return only the validated public schema and safe global envelopes.

## Logging Requirements

Log `product_source.text_create.requested`, `product_source.parent_product_not_found`, `product_source.text_created`, and controlled `product_source.text_create_failed` events. Include only product/source IDs, source type, UTF-8 size, display-name presence, and safe error type. Never include text, display-name content, checksum, records, request bodies, table names, or infrastructure responses.

## Edge Cases

Cover multibyte UTF-8 size, surrounding whitespace, internal newlines, blank display names, missing/null/non-string/blank/oversized text, invalid UUIDs, unknown/system fields, missing parents, duplicate IDs, both repository failure categories, unexpected failures, safe request IDs, and preservation of the existing five product operations with no additional source routes.

## Acceptance Criteria

All 56 criteria from the approved SPEC-009 request must pass, including service workflow and boundaries, exact request/response metadata, parent validation, one approved route, safe mappings, focused tests, exact OpenAPI operation scope, all quality gates, documentation/completion marking, and the out-of-scope audit.

## Test Plan

Use fake repository protocols for service tests covering success, parent ordering/absence, normalization, UTF-8 size/checksum, fixed metadata, duplicates, repository failures, and dependency exclusions. Use FastAPI dependency overrides for API success, validation/system fields, missing parent, duplicate and persistence failures, unexpected safety/request IDs, and exact OpenAPI paths/responses. Run the full backend suite with coverage, Ruff, strict mypy, unchanged frontend checks/build, Compose validation, and Git whitespace/scope checks.

## Implementation Notes

Extend `schemas/product_sources` only with the dedicated public request. Add one service, dependency module, and route module. Reuse the existing repository implementations without adding methods. Use `dataclasses.replace` only after `ProductSource.create` to select the SPEC-009 `READY` initial state while retaining the domain factory's generated identity, timestamps, and version.

## Completion Record

Completed on 2026-08-06. Added the dedicated text-source request schema, two-repository `ProductSourceService`, configured repository/service providers, one POST route, safe duplicate/source-persistence mappings, content-safe logging, service/provider/API/OpenAPI tests, and API/architecture/README documentation. The service validates the parent before source creation and persists normalized text as a `READY` `TEXT` source with `text/plain`, exact UTF-8 size, and SHA-256 metadata without using object storage.

Verification passed: 350 backend tests passed with 2 opt-in DynamoDB Local tests skipped and 91.92% coverage; Ruff lint and formatting passed; strict mypy passed across 51 source files; the unchanged frontend passed 1 Vitest test, ESLint, Prettier, and a 1,063-module Vite production build; Docker Compose validation and Git whitespace checks passed. All 56 acceptance criteria passed. OpenAPI contains exactly one source operation, the approved text-source POST. No file upload, object-storage call, other source operation, extraction, processing, frontend, authentication, or deployment feature was added.
