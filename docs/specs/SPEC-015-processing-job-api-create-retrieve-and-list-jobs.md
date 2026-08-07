# SPEC-015 — Processing Job API: Create, Retrieve and List Jobs

## Status

Completed

## Objective

Expose safe processing-job creation and read APIs without starting or executing jobs.

## User Story

As an API client, I can create one compatible pending job for a product source, retrieve a
job, and page product- or source-scoped job history.

## Scope

Four create/retrieve/list endpoints, application service orchestration, source/job type
compatibility, dependency providers, safe error mappings, tests, and documentation.

## Out of Scope

Job updates, start/cancel/retry operations, workers, queues, schedulers, processing,
parsing, extraction, OCR, AI, frontend work, S3, authentication, and deployment.

## Functional Requirements

Validate parent ownership, create exactly one PENDING job, retrieve by job ID, and list
newest-first through existing product/source repository access patterns and cursors.

## Non-Functional Requirements

Keep routes thin, services infrastructure-independent, responses camel-case, errors
stable and safe, logs content-free, cursors opaque, and existing CORS unchanged.

## Existing Dependencies

SPEC-014 processing-job domain/repository/schemas/cursors, product and source repository
protocols, established FastAPI dependency injection, global handlers, and error envelope.

## Job Creation API

`POST /api/v1/products/{product_id}/sources/{source_id}/jobs` accepts only `jobType`,
validates product and product-scoped source, creates one attempt-1 PENDING job with domain
defaults, persists it conditionally, and returns the safe record with HTTP 201.

## Job Retrieval API

`GET /api/v1/processing-jobs/{job_id}` retrieves by UUID and returns HTTP 200 or the safe
`PROCESSING_JOB_NOT_FOUND` 404 without exposing `sourceScope`.

## Product Job Listing API

`GET /api/v1/products/{product_id}/processing-jobs` validates the product and delegates a
newest-first, limit-1–100 query to the existing product index. The default limit is 20.

## Source Job Listing API

`GET /api/v1/products/{product_id}/sources/{source_id}/jobs` validates the product and its
scoped source before delegating to the existing source index. The default limit is 20.

## Product and Source Validation

Application services check the product first. Create and source-list then retrieve the
source by both IDs. Missing and cross-product sources share the same safe 404.

## Job Type Rules

TEXT supports SOURCE_PROCESSING. PDF additionally supports PDF_TEXT_EXTRACTION and
PDF_TABLE_EXTRACTION. IMAGE additionally supports IMAGE_ANALYSIS. CSV additionally
supports CSV_PROCESSING. All incompatible pairs are rejected centrally.

## Pagination

Both lists accept an optional opaque cursor. Product cursors bind the product; source
cursors bind product and source. Scope/identity failures map to a controlled HTTP 400.

## Dependency Injection

A processing-job repository provider constructs the configured DynamoDB repository. A
service provider injects product, source, and job repository protocols. Routes depend
only on the service.

## Error Handling

Stable mappings cover product/source/job absence, incompatible types, duplicate IDs,
invalid cursors, request validation, each repository family, and unexpected failures.

## Logging Requirements

Log safe IDs, enum values, counts, and cursor presence. Never log source content, raw
cursors/items, tables, infrastructure metadata, results, or error-message contents.

## Security Considerations

Enforce UUIDs, strict body allowlists, bounded limits, source ownership, compatibility,
opaque identity-bound cursors, no scans, and no client-controlled job state or identity.

## Edge Cases

Missing parents stop downstream calls; cross-product access is indistinguishable from
absence; empty pages remain successful; malformed/mixed cursors fail safely; repository
and unexpected errors never leak internal messages.

## Acceptance Criteria

All 88 authoritative criteria in the implementation amendment must pass, including the
exact four OpenAPI operations and absence of mutation/execution features.

## Test Plan

Add compatibility matrices, isolated service call-order/default/failure tests, API
validation/error/pagination/isolation tests, and exact OpenAPI operation assertions; then
run complete backend, coverage, static, frontend, Compose, whitespace, and scope checks.

## Implementation Notes

The API-specific request schema exposes only `jobType`; it does not reuse the internal
SPEC-014 persistence create schema that includes product/source identity and attempt.

## Completion Record

Completed on 2026-08-07. The exact four processing-job create/retrieve/list operations,
source-type compatibility policy, application service, dependency providers, safe error
mappings, logging, tests, and documentation are implemented without execution features.

Verification completed with 682 backend tests passing and 3 opt-in DynamoDB Local tests
skipped, 92.67% coverage against the 90% threshold, Ruff lint and format, strict mypy
across 65 source files, unchanged frontend test/lint/format/build checks, Docker Compose
configuration validation, Git whitespace validation, and the scope audit all passing.
