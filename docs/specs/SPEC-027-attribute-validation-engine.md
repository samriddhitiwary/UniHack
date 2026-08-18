# SPEC-027 — Attribute Validation Engine

## Status
Completed

## Objective
Validate every SPEC-024 normalized candidate against its exact immutable category schema without selecting values or resolving conflicts.

## User Story
As a catalog reviewer, I need explainable candidate-level validation so invalid evidence is visible while all source lineage remains intact.

## Scope
Backend-only deterministic type, range, allowed-value, pattern, and unit validation; immutable results; composite persistence; processing-job lifecycle; tests and documentation.

## Out of Scope
Candidate selection, conflict resolution, completeness recalculation, missing-value generation, Product mutation, APIs, AI/LLM, frontend, S3, authentication, and deployment.

## Functional Requirements
Load one explicit normalization result and its exact schema, assess every candidate, build attribute summaries and aggregate counts, persist the result, then complete the job.

## Non-Functional Requirements
Decimal arithmetic, bounded values/patterns/issues, safe codes, immutable inputs, deterministic ordering, no scans, and no external rule execution.

## Existing Dependencies
SPEC-022 schema metadata, SPEC-024 normalized candidates, processing-job transitions, and existing composite DynamoDB conventions.

## Validation Input
A product-level `ATTRIBUTE_VALIDATION` job explicitly identifies one `attribute_normalization_id`; implicit latest-result lookup is forbidden.

## Schema Dependency
The normalization category/version selects the schema and its fingerprint must match exactly.

## Candidate Eligibility
Every normalized candidate receives an assessment. `INVALID_VALUE` is not validatable; other statuses remain eligible for applicable rules.

## Type Validation
NUMBER uses Decimal, INTEGER requires exact integral Decimal, TEXT is nonblank, BOOLEAN is canonical `true`/`false`, and ENUM is exact.

## Numeric Range Validation
Configured minimum and maximum rules are inclusive and compared as Decimal values.

## Integer Validation
Fractional values are rejected and never rounded.

## Allowed-Value Validation
Configured values require exact canonical string equality; no fuzzy matching occurs.

## Pattern Validation
Trusted bounded schema patterns use full-match semantics. Invalid or oversized patterns are technical schema-rule failures.

## Unit Compatibility Validation
Canonical normalized units must appear in the schema's allowed units. Missing units warn; unsupported units error; no conversion or inference occurs.

## Validation Severity
Issues have stable `INFO`, `WARNING`, or `ERROR` severity; candidate status follows not-validatable, error, warning, valid precedence.

## Validation Issue Model
Immutable bounded issues contain identity, type, severity, safe message code, and bounded expected/actual values.

## Candidate Validation Model
Immutable assessments preserve normalized/source candidate IDs, attribute metadata, normalized value/unit, issue counts, evidence location/type, source ID, and UTC time.

## Result Model
Immutable results preserve upstream/schema lineage, aggregate counts, ordered assessments/summaries, warnings, engine/version, and UTC creation time.

## DynamoDB Persistence
`attribute-validation-results` uses `validationId`/`recordKey`, META, ordered ASSESSMENT and SUMMARY records, conditional writes, 390000-byte guards, and sparse `JobIdIndex`.

## Processing Job Lifecycle
Validate prerequisites before RUNNING; persist before COMPLETED at 100 with a result reference; technical post-start failures attempt FAILED.

## Safety Limits
Maximum 5000 candidates, 100 attributes, 10000 value characters, 500 pattern characters, 20 issues per candidate, and 10000 total issues.

## Error Handling
Controlled errors cover invalid jobs, missing/cross-product normalization, missing/mismatched schema, unknown attributes, malformed rules, limits, engine/storage failures, malformed partitions, and completion consistency risk.

## Logging Requirements
Log safe lifecycle IDs, candidate/attribute status and counts only; never raw evidence or arbitrary exceptions.

## Security Considerations
Explicit lineage, exact fingerprints, bounds, Decimal, trusted regex only, no executable expressions, internet, LLM, filesystem, or raw-source logging.

## Edge Cases
Zero candidates, all not-validatable, missing/unsupported units, mixed valid/invalid candidates, inclusive boundaries, raw text, and valid conflicting candidates.

## Acceptance Criteria
All 136 criteria in the supplied SPEC-027 contract must pass.

## Test Plan
Cover all types, ranges, allowed values, patterns, units, normalization-invalid candidates, mixed/multiple candidates, summaries, lineage, persistence, lifecycle, and failures.

## Implementation Notes
Validation is candidate-local and schema-driven. It never changes conflict/completeness data or chooses a final value.

## Completion Record
Completed on 2026-08-13. Implemented exact-schema candidate validation, immutable issues,
assessments and summaries, composite DynamoDB persistence, product-level job orchestration,
controlled failures, safety limits, structured logging, tests, and documentation. The full backend
suite passed with 1,269 tests, 11 skips, and 90.67% coverage; Ruff formatting/lint, strict mypy,
unchanged frontend tests/lint/format/build, Docker Compose validation, and Git whitespace checks
all passed. The optional DynamoDB Local contract test was evaluated but not added because unit-level
repository and table-definition contracts cover the required behavior without a running service.
