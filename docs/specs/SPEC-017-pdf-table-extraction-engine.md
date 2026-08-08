# SPEC-017 — PDF Table Extraction Engine

## Status
Completed

## Objective
Extract bounded, page-level structured tables from stored PDF product sources, retain table/row/cell evidence, persist results independently, and drive the associated processing job lifecycle.

## User Story
As a downstream catalog-processing service, I need deterministic table evidence from a PDF so later features can interpret product data without reopening or mutating the source.

## Scope
Pure-Python PDF table parsing, conservative cell normalization, immutable evidence, quality assessment, DynamoDB persistence, direct service orchestration, limits, safe errors, logging, tests, and documentation.

## Out of Scope
OCR, scanned-table recognition, semantic interpretation, cross-page merging, CSV/image processing, AI, APIs, workers, retries, frontend, S3, authentication, and deployment.

## Functional Requirements
- Process only PENDING `PDF_TABLE_EXTRACTION` jobs whose product-scoped source is a stored PDF.
- Open content only through `ObjectStorage`, extract pages and tables in source order, and preserve explicit empty cells.
- Persist a result before completing the job; valid PDFs without tables complete with `NO_TABLES`.
- Mark controlled post-start failures as FAILED with safe metadata.

## Non-Functional Requirements
The engine is deterministic, dependency-injected, backend-only, bounded, immutable at the domain boundary, and free of external executables and direct filesystem access.

## Existing Dependencies
Processing-job/source repositories, job transition policy, `ObjectStorage`, DynamoDB serialization helpers, and SPEC-016 composite-result conventions.

## PDF Table Extraction Input
A `PDF_TABLE_EXTRACTION` job and its matching product-scoped PDF source with a non-null logical storage key.

## Table Parser Design
Use `pdfplumber` page-by-page. Each page's table candidates are normalized without semantic inference. Parser exceptions become controlled parse failures.

## Table Evidence Model
Immutable `PdfTableCell`, `PdfTableRow`, and `PdfExtractedTable` values retain zero-based cell coordinates and one-based page/table numbers.

## Extraction Result Model
`PdfTableExtractionResult` contains identities, parser metadata, aggregate counts, quality, ordered tables, warnings, and a UTC creation timestamp. It never contains PDF bytes.

## DynamoDB Persistence
Use `{prefix}-table-extraction-results`, partitioned by `extractionId` and sorted by `recordKey`. Store `META` and `TABLE#{page:06d}#{table:06d}` records with a sparse `JobIdIndex` on metadata. Reject records that approach DynamoDB's item-size ceiling.

## Processing Job Lifecycle
Validate before start, transition PENDING to RUNNING before storage access, persist the result, then transition RUNNING to COMPLETED with progress 100 and `table-extraction-results/{extractionId}`. Controlled post-start failures attempt RUNNING to FAILED.

## Object Storage Integration
Open the source using `ObjectStorage.open(storage_key)` in a context manager. The service has no filesystem knowledge.

## Extraction Quality Rules
`TABLES_FOUND` means at least one valid non-empty table. `NO_TABLES` is a successful readable PDF with no valid table candidates. `PARTIAL` is reserved for actual recoverable parser degradation and is not emitted because the selected parser exposes no deterministic warning contract.

## Safety Limits
Defaults: 300 pages, 500 tables, 5,000 rows per table, 200 columns per table, 500,000 total cells, and 20,000 characters per cell. All values are positive and breaches fail without truncation.

## Error Handling
Invalid jobs/sources fail before RUNNING. Missing objects, storage errors, corrupt PDFs, limit breaches, and result persistence failures use controlled exceptions and safe job messages. A completion-update failure preserves the result and logs a consistency risk.

## Logging Requirements
Log safe identifiers, parser/version, counts, quality, and controlled error codes. Never log content, bytes, storage keys, paths, or raw parser exceptions.

## Security Considerations
PDF and job types are allow-listed; resource use and item sizes are bounded; no OCR, binaries, embedded-attachment extraction, arbitrary writes, or content logging is permitted.

## Edge Cases
Blank cells, ragged rows, all-empty parser artefacts, multiple tables per page, multi-page PDFs, no-table PDFs, malformed PDFs, duplicate results, incomplete record sets, and completion consistency risks are handled explicitly.

## Acceptance Criteria
All 86 criteria in the controlling SPEC-017 amendment must pass, including complete tests, coverage of at least 90%, quality checks, documentation, and scope verification.

## Test Plan
Unit-test normalization, immutable invariants, real synthetic PDF parsing, every safety limit, serialization, repository ordering/reconstruction/failures, service validation/lifecycle/storage/failure behavior, and optional DynamoDB Local contracts. Run all backend and unchanged frontend checks.

## Implementation Notes
Tables are never joined across pages or interpreted. Ragged rows are padded to the maximum table width. A candidate with no rows, no columns, or only empty cells is discarded as parser noise.

## Completion Record
Completed 2026-08-07. Added pdfplumber-backed page/table extraction, immutable cell/row/table evidence, conservative normalization, deterministic quality, bounded limits, composite DynamoDB persistence, and processing-job lifecycle orchestration. Verification: 810 backend tests passed and 5 opt-in DynamoDB Local tests skipped because Docker Desktop was unavailable; coverage 92.37%; Ruff lint/format, strict mypy, frontend tests/ESLint/Prettier/Vite build, Docker Compose configuration, and Git whitespace checks passed. The representative generated PDF fixture was rendered and visually inspected. No out-of-scope feature was added.
