# SPEC-016 — PDF Text Extraction Engine

## Status

Completed

## Objective

Extract bounded page-level embedded text from an existing PDF source, persist evidence
outside source/job records, classify extraction quality, and update one processing job.

## User Story

As a processing workflow, I can turn a pending PDF text-extraction job into a durable,
page-preserving result with an accurate lifecycle and safe controlled failures.

## Scope

PDF parsing with pypdf, immutable extraction models, deterministic quality assessment,
composite DynamoDB persistence, job orchestration, safety limits, tests, and documentation.

## Out of Scope

OCR, table/image extraction, CSV parsing, classification, AI, execution/result APIs,
workers, queues, retry, frontend work, S3, authentication, and deployment.

## Functional Requirements

Validate one PENDING PDF_TEXT_EXTRACTION job and its product-scoped PDF source, transition
to RUNNING, open through ObjectStorage, parse every page, persist a complete result, then
transition to COMPLETED with a logical result reference. Controlled post-start failures
transition to FAILED where possible.

## Non-Functional Requirements

Use bounded configuration, no external executables, immutable evidence, conservative
normalization, scalable page records, repository protocols, safe logging, and no scans.

## Existing Dependencies

ProductSource and ProcessingJob models/repositories, centralized transition policy,
ObjectStorage, generic DynamoDB serialization, local table creation, and safe exceptions.

## PDF Extraction Input

Only a PENDING PDF_TEXT_EXTRACTION job is accepted. Its source is retrieved with the
job's product/source IDs and must be PDF with a server-owned storage key.

## PDF Parser Design

pypdf reads the binary ObjectStorage stream directly with no shell, filesystem path,
attachment extraction, action execution, OCR, or system dependency. Parsing is strict
about configured page and character limits.

## Page-Level Extraction Model

Each immutable page records a positive 1-based page number, conservatively normalized
text, exact character count, and derived has-text flag. Blank pages remain ordered pages.

## Extraction Result Model

An immutable result records UUID identities, parser/version, page totals, quality status,
ordered pages, safe warnings, and a UTC creation timestamp.

## DynamoDB Persistence

`{prefix}-extraction-results` uses composite `extractionId`/`recordKey` keys. `META` holds
summary metadata; `PAGE#000001` etc. hold one bounded page each. Sparse `JobIdIndex` uses
`jobId`/`createdAt` on META only. Access is create, get by ID, and get by job; no scan/list.

## Processing Job Lifecycle

Pre-start job/source validation leaves invalid jobs unchanged. PENDING transitions to
RUNNING before object access. Successful result persistence precedes RUNNING-to-COMPLETED,
which sets progress 100 and `extraction-results/{extractionId}`. Controlled post-start
failures transition RUNNING to FAILED with bounded safe code/message.

## Object Storage Integration

The service calls only ObjectStorage.open and closes its binary stream reliably. It never
constructs LocalObjectStorage, sees a filesystem path, writes files, or calls S3.

## Extraction Quality Rules

Zero total characters is NO_TEXT. Otherwise average characters per PDF page below 25 is
LOW_TEXT; all other readable results are USABLE. LOW_TEXT and NO_TEXT are successful.

## Error Handling

Controlled errors cover invalid jobs/sources, corrupt PDFs, page/text limits, duplicate
results, malformed persistence, and repository failures. Raw parser/storage details and
stack traces are never stored. Failure-state updates are best effort without masking the
original controlled error.

## Logging Requirements

Log safe IDs, counts, parser metadata, quality, and error code. Never log text, PDF bytes,
storage keys, paths, filenames, raw parser errors, tables, or AWS metadata.

## Security Considerations

Defaults are 300 pages, 100,000 characters per page, and 2,000,000 total characters; all
are positive validated settings. Exceeding limits fails without truncation or completion.

## Edge Cases

Blank pages preserve position; readable image-only PDFs yield NO_TEXT and complete;
corrupt PDFs fail; partial repository writes cannot be reported as completed; a persisted
result remains if the final job update fails, which is logged as a consistency risk.

## Acceptance Criteria

All 81 authoritative amendment criteria must pass, including parser, quality, scalable
persistence, job lifecycle, full verification, documentation, and scope control.

## Test Plan

Programmatically generate tiny PDFs for page/blank/text cases; test normalization, limits,
quality, mapping, repository access/failures, service ordering/lifecycle/failures, optional
DynamoDB Local behavior, and all unchanged repository checks.

## Implementation Notes

Page items are independently bounded and query pagination reconstructs a result, avoiding
unsafe single-item growth. Metadata is conditionally created before page writes; any
subsequent failure remains a controlled incomplete result and the job is not completed.

## Completion Record

Completed on 2026-08-07. pypdf page extraction, immutable evidence, deterministic quality,
bounded configuration, composite result persistence, optimistic job lifecycle updates,
controlled failures, tests, and documentation are implemented without an execution API,
OCR, table extraction, AI, worker, frontend, S3, authentication, or deployment work.

Verification completed with 747 backend tests passing and 4 opt-in DynamoDB Local tests
skipped, 92.73% coverage against the 90% threshold, Ruff lint and format, strict mypy
across 74 source files, unchanged frontend test/lint/format/build checks, Docker Compose
configuration validation, Git whitespace validation, and the scope audit all passing.
