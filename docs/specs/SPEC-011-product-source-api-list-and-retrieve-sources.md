# SPEC-011 — Product Source API: List and Retrieve Sources

## Status

Completed

## Objective

Expose read-only, product-scoped APIs that list source metadata newest first and retrieve one source by its composite product/source identity.

## User Story

As an API consumer, I can inspect the sources attached to an existing product without receiving file bytes or learning about sources owned by other products.

## Scope

- `GET /api/v1/products/{product_id}/sources`
- `GET /api/v1/products/{product_id}/sources/{source_id}`
- Parent-product existence validation in the service layer
- Product-scoped source retrieval
- Bounded, opaque, product-bound cursor pagination
- Existing public product-source response schemas, repositories, error envelopes, logging, and OpenAPI conventions

## Out of Scope

Source mutation, deletion, download, streaming, content-specific endpoints, filters, search, counts, batch operations, presigned URLs, parsing, extraction, processing, AI, frontend work, authentication, S3, deployment, and placeholders for those features.

## Functional Requirements

1. List sources for an existing product with optional `limit` and `cursor` query parameters.
2. Default `limit` to 20 and accept only values from 1 through 100.
3. Return `ProductSourceListResult` with camel-case fields, newest-first items, and an opaque `nextCursor` or `null`.
4. Return `200` with `items: []` and `nextCursor: null` when an existing product has no sources.
5. Retrieve a source with both `product_id` and `source_id`, returning `ProductSourceRecord`.
6. Return the established safe errors for missing parents, missing scoped sources, invalid cursors, validation failures, repository failures, and unexpected failures.

## Non-Functional Requirements

- Keep routes thin and services independent from FastAPI, Boto3, and object storage for read workflows.
- Preserve existing source create and upload behavior.
- Do not scan, sort in memory, expose raw DynamoDB keys, or issue total-count queries.
- Emit structured logs containing identifiers and pagination facts only.

## Existing Dependencies

- `ProductRepository.get_by_id`
- `ProductSourceRepository.get_by_id` and `list_by_product`
- `DynamoDBProductSourceRepository`
- `ProductCreatedAtIndex`
- Product-source cursor helpers from SPEC-007
- `ProductSourceRecord` and `ProductSourceListResult`
- Global request validation, request ID, error-envelope, and exception-handler conventions

## Service-Layer Design

`ProductSourceService.list_sources` verifies the parent, calls `list_by_product` with the exact product ID, limit, and cursor, and maps the repository page to `ProductSourceListResult`. `ProductSourceService.get_source` verifies the parent, calls composite-key `get_by_id`, and raises `ProductSourceNotFoundError` when absent. Controlled repository and cursor exceptions pass through unchanged.

## List API Contract

`GET /api/v1/products/{product_id}/sources` returns HTTP 200 and `ProductSourceListResult`. `limit` is optional, defaults to 20, and is bounded from 1 through 100. `cursor` is optional, opaque, non-empty, and at most 4,096 characters. No total count or raw pagination key is returned.

## Retrieve API Contract

`GET /api/v1/products/{product_id}/sources/{source_id}` validates both path segments as UUIDs and returns HTTP 200 with `ProductSourceRecord`. It never reads file content or object storage.

## Product Existence Validation

Both service methods call `ProductRepository.get_by_id(product_id)` first. An absent product raises `ProductNotFoundError`; in that case the source repository is not called. A present product with zero sources returns a valid empty page.

## Product-Scoped Source Access

Retrieval calls `ProductSourceRepository.get_by_id(product_id, source_id)`. An absent composite key raises `ProductSourceNotFoundError` without revealing whether the source ID exists under another product.

## Pagination Design

The existing SPEC-007 cursor format is reused unchanged. It uses the `product_sources` scope, binds the cursor to the product UUID, safely JSON/base64-decodes an opaque envelope, rejects malformed, wrong-scope, and wrong-product values, and never exposes a raw key through the API. DynamoDB queries `ProductCreatedAtIndex` with `ScanIndexForward=False` for stable newest-first pages.

## Filtering Decision

No filters are supported in SPEC-011. Only `limit` and `cursor` are accepted, avoiding scans, new indexes, incomplete in-memory filtering, or unbounded reads.

## Dependency Injection

The existing `get_product_source_service` dependency continues to inject the product repository and product-source repository. Routes call exactly one service method and do not access repositories directly.

## Error Handling

- Missing product: `404 PRODUCT_NOT_FOUND`
- Missing scoped source: `404 PRODUCT_SOURCE_NOT_FOUND`
- Invalid or product-mismatched source cursor: `400 INVALID_PRODUCT_SOURCE_CURSOR`
- Invalid path/query input: `422 REQUEST_VALIDATION_FAILED`
- Product repository failure: `503 PRODUCT_STORAGE_UNAVAILABLE`
- Product-source repository failure: `503 PRODUCT_SOURCE_STORAGE_UNAVAILABLE`
- Unexpected failure: `500 INTERNAL_SERVER_ERROR`

## Logging Requirements

Log safe structured request and completion/failure events with product ID, source ID when applicable, requested limit, cursor presence, result count, next-cursor presence, and error type. Do not log cursor contents, source records, text content, filenames, storage keys, checksums, DynamoDB keys, table names, or AWS responses.

## Security Considerations

Enforce UUID validation, bounded pages, safe product-bound cursors, composite-key isolation, safe errors, and unchanged CORS behavior. Do not expose file bytes, local paths, raw database data, or global source enumeration.

## Edge Cases

- Existing product with no sources returns an empty 200 response.
- Limits 1 and 100 are accepted; 0, 101, and non-integers are rejected.
- Malformed and wrong-product cursors return the same safe cursor error.
- A source ID owned by a different product is indistinguishable from a missing source.
- Invalid product/source UUIDs are rejected before service invocation.

## Acceptance Criteria

All 76 acceptance criteria in the authoritative SPEC-011 request must pass, including the two approved GET operations, parent validation, scoped isolation, cursor safety, newest-first GSI access, error mappings, exact four-operation OpenAPI surface, full checks, documentation, and scope control.

## Test Plan

- Service tests for successful/empty list, pagination forwarding, parent-first ordering, missing parent/source, cross-product isolation, and controlled repository/cursor failures.
- API tests for camel-case records, empty pages, limit boundaries, cursor forwarding/errors, UUID validation, missing records, repository/unexpected failures, request IDs, and route absence.
- Repository regression coverage for descending GSI queries, composite keys, and scoped cursors.
- OpenAPI verification for exactly the two existing POST and two new GET operations.
- Full backend, coverage, Ruff, mypy, unchanged frontend, Docker Compose, and Git whitespace checks.

## Implementation Notes

The repository protocol, DynamoDB access patterns, domain model, schemas, and cursor encoding already satisfy SPEC-011 and require no feature expansion. The source service, router, global exception mappings, focused tests, and documentation will be extended minimally.

## Completion Record

Completed on 2026-08-07. The API now provides product-scoped source listing and retrieval, validates the parent before source access, reuses the descending GSI and product-bound opaque cursor, maps missing sources and invalid cursors safely, and exposes exactly the four approved source operations.

Verification passed: 415 backend tests passed and 2 skipped with 92.17% coverage; Ruff lint and formatting passed; strict mypy passed for 52 source files; the unchanged frontend test, ESLint, Prettier, and Vite build passed; Docker Compose configuration and Git whitespace checks passed. All 76 acceptance criteria passed, and the scope audit found no source mutation, download, filter, search, extraction, processing, AI, frontend, authentication, S3, or deployment implementation.
