# SPEC-018 — CSV Processing Engine

## Status
Completed

## Objective
Safely parse a stored CSV source into ordered string-only evidence, persist it independently, and update its CSV processing job.

## User Story
As a downstream catalog service, I need auditable CSV rows and cells so later features can interpret source data without reopening or mutating the source.

## Scope
UTF-8 CSV decoding, allowlisted delimiter detection, standard quoting, headers, malformed-row evidence, bounded parsing, immutable results, DynamoDB persistence, job orchestration, safe errors/logging, tests, and documentation.

## Out of Scope
Classification, attribute/header interpretation, type/date/unit conversion, validation, AI, APIs, workers, retries, frontend, S3, authentication, and deployment.

## Functional Requirements
- Process only PENDING `CSV_PROCESSING` jobs for product-scoped stored CSV sources.
- Preserve headers, row order, cell text, leading zeroes, formula-looking text, empty cells, and extra columns.
- Complete recoverably ragged inputs with warnings; reject structurally unparseable input.
- Persist results before completing jobs and safely fail controlled post-start errors.

## Non-Functional Requirements
The engine is deterministic, dependency-injected, standard-library based, bounded, immutable at the domain boundary, and contains no direct filesystem, HTTP, Boto3, formula evaluation, or semantic logic.

## Existing Dependencies
SPEC-010 CSV upload validation, processing-job/source repositories, transition policy, `ObjectStorage`, DynamoDB serialization utilities, and SPEC-016/017 composite-result conventions.

## CSV Processing Input
A `CSV_PROCESSING` job and matching product-scoped CSV source with a logical storage key.

## CSV Parser Design
Read the binary stream in bounded chunks, decode once, detect a delimiter from a bounded sample, and parse with Python `csv.reader(..., strict=True)`. Blank parser rows are ignored; explicitly quoted empty fields remain rows.

## Encoding Rules
Decode strictly with `utf-8-sig`, accepting UTF-8 with or without BOM. Invalid bytes fail as `CSV_ENCODING_UNSUPPORTED`; no legacy guessing or replacement occurs.

## Delimiter Rules
Only comma, semicolon, tab, and pipe are allowed. `csv.Sniffer` examines the configured bounded sample. If it fails, comma is accepted only when unquoted comma structure is clear; otherwise processing fails with `CSV_DELIMITER_UNDETERMINED`.

## Header Model
The first meaningful parsed row is the required header. Order, duplicate names, and explicit empty names are preserved as indexed immutable `CsvHeaderCell` values.

## Row and Cell Model
Data rows are numbered from one. Regular cells always match header width. Short rows are padded and warned; extra values are preserved in `extra_cells` and warned. All values remain normalized strings.

## Processing Result Model
`CsvProcessingResult` stores identities, encoding, delimiter, header, aggregate counts, ordered rows, deterministic quality, unique warning codes, and a UTC timestamp. It stores no source bytes.

## DynamoDB Persistence
Use `{prefix}-csv-processing-results` with `processingId`/`recordKey`, a `META` record, ordered `ROW#{rowNumber:09d}` records, and sparse `JobIdIndex`. Reject any serialized item above 390,000 bytes before writes.

## Processing Job Lifecycle
Validate before start; update PENDING to RUNNING before storage access; persist the result; then update RUNNING to COMPLETED with progress 100 and `csv-processing-results/{processingId}`. Controlled post-start failures attempt FAILED.

## Object Storage Integration
Use `ObjectStorage.open(storage_key)` as a context-managed binary stream. The service contains no path or provider-specific code.

## Safety Limits
Defaults: 5,242,880 file bytes, 100,000 rows, 500 columns, 1,000,000 data cells, 50,000 characters per header/data cell, and a 65,536-byte delimiter sample. All limits are positive and breaches fail without truncation.

## Malformed CSV Behaviour
Short and extra-column rows are recoverable, preserved, and produce row/result warnings plus `VALID_WITH_WARNINGS`. CSV syntax errors, empty files, unknown delimiters, and hard limits fail without successful results.

## Error Handling
Invalid setup fails before RUNNING. Storage, encoding, delimiter, syntax, limit, item-size, and persistence failures use controlled exceptions and safe job metadata. Completion-update failures preserve the valid result and log consistency risk.

## Logging Requirements
Log safe identities, encoding, delimiter, counts, quality, and controlled codes. Never log bytes, storage keys/paths, row/cell values, or raw exception messages.

## Security Considerations
Enforce CSV/job allowlists, UTF-8, delimiter and resource bounds, plain-text formula-looking values, item-size guards, no macro/formula/code execution, and no content logging.

## Edge Cases
BOM, quoted delimiters/newlines/escaped quotes, empty and duplicate headers, header-only data, blank lines, explicit empty rows, leading zeroes, short/extra rows, invalid bytes, malformed quotes, and incomplete result partitions are covered.

## Acceptance Criteria
All 99 acceptance criteria in the controlling amendment must pass, including coverage of at least 90%, unchanged frontend checks, documentation, and scope verification.

## Test Plan
Test parser dialects/quoting/normalization/limits and malformed input; immutable domain invariants; schemas and DynamoDB round trips; repository ordering/pagination/errors/size guard; service validation/lifecycle/failures; optional DynamoDB Local; and complete repository quality checks.

## Implementation Notes
`total_cell_count` counts all preserved data cells, including padded regular cells and extra cells, but excludes header cells. `empty_cell_count` counts empty regular and extra data cells. Result warnings are the ordered union of row warnings.

## Completion Record
Completed 2026-08-08. Added strict standard-library UTF-8 CSV parsing, allowlisted delimiter detection, immutable header/row/cell evidence, recoverable malformed-row warnings, defensive limits, composite DynamoDB persistence, and processing-job lifecycle orchestration. Verification: 885 backend tests passed and 6 opt-in DynamoDB Local tests skipped; coverage 92.21%; Ruff lint/format, strict mypy, unchanged frontend tests/ESLint/Prettier/Vite build, Docker Compose configuration, and Git whitespace checks passed. No out-of-scope feature was added.
