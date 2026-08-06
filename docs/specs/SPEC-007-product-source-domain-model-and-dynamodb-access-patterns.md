# SPEC-007 — Product Source Domain Model and DynamoDB Access Patterns

## Status

Completed

## Objective

Create the backend-only domain, validation, serialization, cursor, repository, and local-table foundation for product source metadata.

## User Story

As a future ingestion workflow, I need validated metadata records for product PDFs, images, CSV files, and text inputs so later upload and processing features can build on stable persistence contracts.

## Scope

Implement immutable product-source entities and enums, repository-boundary Pydantic schemas, centralized item conversion, scoped pagination cursors, a mockable repository, a DynamoDB implementation, and idempotent local source-table creation.

## Out of Scope

Source APIs, file uploads or bytes, local/S3 storage, URLs, PDF/CSV/image parsing, OCR, processing jobs, background workers, AI, evidence, technical attributes, duplicate detection, frontend source UI, authentication, authorization, and deployment are excluded.

## Functional Requirements

- Model source identity, ownership, type, status, metadata, optional text, safe error text, timestamps, and version.
- Validate file versus text source requirements, MIME types, checksums, sizes, paths, and bounds.
- Support conditional create, composite-key retrieve, newest-first list by product, optimistic update, conditional delete, and opaque scoped pagination.
- Create `{prefix}-sources` alongside the existing products table without altering existing data.

## Non-Functional Requirements

Domain objects remain immutable and infrastructure-independent. Repositories return domain objects and contain no FastAPI dependency. Queries are bounded, use one approved GSI, never scan, and expose no raw keys or infrastructure details. No new runtime dependency is required.

## Existing Dependencies

SPEC-007 reuses UUID/UTC/domain conventions, camelCase Pydantic aliases, DynamoDB primitive serialization, Botocore Stubber tests, configuration-derived table names, controlled exception chaining, opaque URL-safe cursors, and the idempotent table script from SPEC-001 through SPEC-006.

## Product Source Domain Model

`ProductSource` contains `source_id`, `product_id`, `source_type`, `status`, `original_filename`, `storage_key`, `mime_type`, `file_size_bytes`, `checksum_sha256`, `display_name`, `text_content`, `error_message`, `created_at`, `updated_at`, and `version`. `create` generates the source UUID, UTC timestamps, `PENDING`, and version 1. `ProductSourcePage` contains an immutable tuple and optional opaque cursor.

## Source Type and Status Enums

Types are exactly `PDF`, `IMAGE`, `CSV`, and `TEXT`. Statuses are exactly `PENDING`, `READY`, `PROCESSING`, `COMPLETED`, and `FAILED`. No workflow-transition restrictions are introduced.

## DynamoDB Access Patterns

Support only conditional create; retrieve by product/source ID; newest-first bounded list for one product; optimistic metadata/status update; conditional delete; and continuation of that product list. Cross-product, status, type, MIME, filename, checksum, search, and batch access are unsupported.

## DynamoDB Table Design

`{DYNAMODB_TABLE_PREFIX}-sources` uses String partition key `productId` and String sort key `sourceId`. `ProductCreatedAtIndex` uses `productId` and `createdAt`, projects all fields, and is queried descending. No other index or scan is added.

## Serialization Rules

Persist camelCase attributes, UUID strings, enum values, UTC microsecond `Z` timestamps, safe integral numbers, and explicit null optional values. Reuse centralized primitive serialization and rejection of Python floats. Source conversion rejects malformed keys, enums, timestamps, values, and item shapes using `ProductSourceSerializationError`. No file bytes, base64 data, extracted content, prompts, or AI output is stored.

## Repository Contract

`ProductSourceRepository` defines `create`, `get_by_id`, `update`, `list_by_product`, and `delete`. Missing `get_by_id` returns `None`. Create is conditional. Update increments version exactly once and refreshes `updatedAt`; delete and update require the expected version. Conditional failures use a consistent read to distinguish not found from version conflict.

## Validation Rules

UUIDs and aware timestamps are mandatory; version is positive; size is a non-boolean non-negative integer; checksum is 64 lowercase-normalized hex characters; strings are trimmed and bounded. Filenames cannot contain path separators, storage keys cannot be absolute paths, and MIME types normalize lowercase. PDF, IMAGE, and CSV require filenames and reject text content; their MIME types use only approved lists. TEXT may omit a filename, may contain at most 50,000 characters, normally has no storage key, and accepts only `text/plain` when MIME is supplied.

## Error Handling

Controlled source exceptions cover duplicate, missing, version conflict, invalid cursor, serialization, and all other repository failures. Boto3/validation causes are chained but messages never expose table names, request IDs, raw records, or condition expressions.

## Security Considerations

Enforce bounded metadata/text, checksum format, non-negative sizes, safe relative storage keys, approved MIME types, scoped cursor/product matching, fixed DynamoDB expressions, no scans, and no binary/base64 content. Storage keys are metadata only and never trusted as filesystem paths or credentials.

## Edge Cases

Handle blank optional values, uppercase MIME/checksum normalization, naive timestamps, invalid enums, file sources with text, text sources without filenames, malformed/cross-product/cross-scope cursors, empty/final pages, concurrent deletion, stale mutations, missing composite keys, and corrupt persisted records.

## Acceptance Criteria

All 66 criteria from the approved SPEC-007 request must pass, including the exact domain/enums/schemas, validation, centralized conversion, scoped pagination, composite-key repository behavior, conditional writes, idempotent two-table creation, tests and quality gates, accurate documentation, no routes, and a clean out-of-scope audit.

## Test Plan

Add focused enum/entity tests for every type and validation rule; schema tests for allowed/system/immutable fields, nulls, bounds, and cross-field behavior; conversion and cursor round-trip/error tests; Stubber repository request/response tests for all access patterns, concurrency, pagination, GSI use, no scans, and wrapped failures; table-definition/idempotence tests; and one opt-in DynamoDB Local source contract. Run all backend coverage/Ruff/mypy and unchanged frontend/Compose/Git checks.

## Implementation Notes

Use dedicated `domain/product_sources` and `schemas/product_sources` packages. Extend `utils/dynamodb.py` only with source item conversion and `utils/cursors.py` only with a scoped source cursor envelope. No service or API route is needed. The products table definition and behavior remain unchanged.

## Completion Record

Completed on 2026-08-06. Added immutable source entities and approved enums, create/update/record/list schemas, source item conversion, product-scoped opaque cursors, controlled source exceptions, a repository protocol, a composite-key DynamoDB repository with conditional writes and GSI listing, idempotent source-table creation, and focused unit plus opt-in local contract coverage. No service, API route, file handling, storage, processing, or dependency was added.

Verification passed: 241 backend tests with 2 opt-in DynamoDB Local tests skipped and 92.62% coverage; Ruff lint and formatting; strict mypy across 43 source files; 1 unchanged frontend test; ESLint; Prettier; Vite production build; Docker Compose validation; and Git whitespace/scope inspection. All 66 acceptance criteria passed.
