# SPEC-014 — Product Source Processing Job Domain and Persistence

## Status

Completed

## Objective

Create an immutable processing-job domain and DynamoDB persistence foundation for future source-processing attempts without executing work or exposing an API.

## User Story

As a future processing service, I can persist, retrieve, page, and conditionally update safe job metadata for one product source.

## Scope

- Processing-job types, statuses, immutable entity, transition policy, and boundary schemas
- DynamoDB serialization, scoped opaque cursors, mockable repository, and implementation
- `{prefix}-processing-jobs` local table with two approved GSIs
- Domain, schema, serialization, repository, pagination, concurrency, table, and opt-in local-contract tests

## Out of Scope

Job APIs, services, workers, queues, schedulers, polling/claiming, retry execution, parsing, extraction, OCR, AI, result storage, frontend work, authentication, S3, and deployment.

## Functional Requirements

Jobs record one attempt for one product/source and support conditional create, consistent get, newest-first product/source lists, and optimistic update. Domain policy controls progress, timestamps, transitions, and terminal states. No scan, global list, delete, or worker query is provided.

## Non-Functional Requirements

Use immutable UTC-safe entities, strict bounded values, generic DynamoDB serialization, safe controlled errors, opaque identity-bound cursors, repository protocols, and idempotent local table creation.

## Existing Dependencies

Product-source domain/repository patterns, SPEC-007 scoped cursors, SPEC-012 optimistic concurrency, centralized DynamoDB primitives, low-level Boto3 repositories, local table script, test stubbers, and camel-case schemas.

## Processing Job Domain Model

`ProcessingJob` contains `job_id`, `product_id`, `source_id`, `job_type`, `status`, `attempt`, `progress_percent`, `error_code`, `error_message`, `result_reference`, `created_at`, `started_at`, `completed_at`, `updated_at`, and `version`. `create` generates UUID identity, PENDING/0 state, attempt default 1, equal UTC timestamps, and version 1.

## Job Status Model

Statuses are PENDING, RUNNING, COMPLETED, FAILED, and CANCELLED. PENDING has no lifecycle timestamps and progress 0. RUNNING has `started_at`, no `completed_at`, and progress below 100. COMPLETED has both timestamps, progress 100, and no errors. FAILED has `completed_at`. CANCELLED has `completed_at` and may have no start time.

## Job Type Model

Approved types are SOURCE_PROCESSING, PDF_TEXT_EXTRACTION, PDF_TABLE_EXTRACTION, IMAGE_ANALYSIS, and CSV_PROCESSING. They are metadata categories only and trigger no execution.

## DynamoDB Access Patterns

Conditional create and update, consistent get by job ID, descending list by product, and descending list by product/source. No scan, global listing, status dashboard, claim-next, retry, sweep, or delete exists.

## DynamoDB Table Design

`{prefix}-processing-jobs` has string partition key `jobId`. `ProductCreatedAtIndex` uses `productId`/`createdAt`. `SourceCreatedAtIndex` uses server-derived `sourceScope = productId#sourceId`/`createdAt`. Both project all fields; no other index is created.

## Serialization Rules

Central primitives handle UUIDs, enums, UTC datetimes, integers, optional values, and reject Python floats. Job mapping adds/removes internal `sourceScope`, verifies it matches product/source identity, and wraps malformed data as `ProcessingJobSerializationError`.

## Repository Contract

`create`, `get_by_id`, `list_by_product`, `list_by_source`, and `update` return domain entities/pages. Lists accept limits 1–100 and opaque cursors. No delete or worker claim method exists.

## Optimistic Concurrency

Updates require positive `expected_version`, condition on stored version, increment exactly once, refresh UTC `updatedAt`, and preserve job/product/source/type/attempt/created identity. Missing and stale conditional failures are distinguished by a consistent read.

## Error Handling

Controlled exceptions cover duplicate, missing, version conflict, invalid transition, invalid cursor, serialization, and repository failures. Raw Boto3/AWS details never cross the repository.

## Logging Requirements

Repository events may include job/product/source IDs, type, status, attempt, progress, result count, and pagination presence. They exclude error-message/result contents, raw items/responses, tables, and AWS metadata.

## Security Considerations

Enforce UUIDs, enums, positive integers, progress bounds, bounded normalized text, logical non-path result references, product/source-scoped indexes, identity-bound safe cursors, no scans, no arbitrary expressions, no raw outputs, and no execution.

## Edge Cases

Malformed stored identities/enums/timestamps/scopes are controlled serialization errors. Product cursors cannot cross products or be used for source queries; source cursors bind both IDs. Terminal states cannot transition. RUNNING cannot reach 100 without completion.

## Acceptance Criteria

All 76 authoritative acceptance criteria must pass, including domain invariants, schemas, serialization, both scoped indexes/cursors, conditional persistence, table idempotence, full verification, documentation, and absence of APIs/workers/processing.

## Test Plan

Focused domain and transition matrices; schema allowlist/alias tests; job wire round trips and malformed/float tests; stubbed create/get/list/pagination/update/failure tests; table-definition/idempotence tests; opt-in DynamoDB Local contract test; full backend/frontend/quality/infrastructure checks.

## Implementation Notes

Status transition application is centralized in the domain policy and produces a new immutable entity. Repository `update` persists an already valid candidate and owns only concurrency, server update time, and version increment.

## Completion Record

Completed on 2026-08-07. The immutable processing-job domain, centralized transition
policy, strict schemas, safe DynamoDB mapping, identity-bound pagination cursors,
mockable repository, conditional persistence, optimistic updates, and idempotent local
table creation are implemented without adding an API or processing execution.

Verification completed with 604 backend tests passing and 3 opt-in DynamoDB Local
tests skipped, 92.16% backend coverage against the 90% threshold, Ruff lint and format,
strict mypy across 61 source files, the unchanged frontend test/lint/format/build suite,
Docker Compose configuration validation, and Git whitespace validation all passing.
