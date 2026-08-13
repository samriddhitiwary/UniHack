# SPEC-026 — Missing Required Attribute and Completeness Detection Engine

## Status
Completed

## Objective
Evaluate every exact-schema attribute against one immutable SPEC-025 result and calculate deterministic required, optional, and overall completeness without selecting values.

## User Story
As a catalog reviewer, I need missing, invalid, conflicted, indeterminate, single-source, and corroborated fields distinguished so that schema coverage is explainable.

## Scope
Backend-only attribute-state mapping, required/optional metrics, integer basis-point percentages, immutable results, composite DynamoDB persistence, product-level job orchestration, tests, and documentation.

## Out of Scope
Final values, conflict resolution, business validation, missing-value generation, Product mutation, APIs, AI/LLM, frontend, S3, authentication, and deployment.

## Functional Requirements
Load the exact schema referenced by one explicit conflict result; evaluate every schema attribute in display order; preserve candidate IDs and consensus metadata; calculate counts, percentages, and overall status; persist before job completion.

## Non-Functional Requirements
Deterministic integer arithmetic, immutable inputs, bounded attributes/candidate IDs/items, no scans, safe errors/logging, complete partition reconstruction, and no dynamic or semantic rules.

## Existing Dependencies
SPEC-022 schemas, SPEC-023 extraction lineage, SPEC-024 normalization lineage, SPEC-025 consensus results, processing-job transitions, and composite DynamoDB conventions.

## Completeness Input
One explicit `attribute_conflict_detection_id` on a product-level `ATTRIBUTE_COMPLETENESS` job. Never resolve “latest” implicitly.

## Schema Dependency
Load `category` plus `schema_version`, then require an exact `schema_fingerprint` match. Never substitute the current active schema.

## Attribute State Model
`PRESENT`, `PRESENT_WITH_TOLERANCE`, `PRESENT_SINGLE_SOURCE`, `CONFLICTED`, `INDETERMINATE`, `INVALID_ONLY`, and `MISSING` map exactly from SPEC-025 status or absence.

## Required Attribute Evaluation
Available includes present, single-source, tolerance, conflict, and indeterminate. Resolved includes the three present states. Verified includes only corroborated exact/tolerance states. Missing and invalid-only are unavailable.

## Optional Attribute Evaluation
Apply identical state/count rules, but optional deficiencies never downgrade the primary required completeness status.

## Missing Attribute Detection
A schema attribute absent from SPEC-025 ATTRIBUTE records is `MISSING`. Invalid evidence is never relabeled missing.

## Invalid Attribute Detection
`NO_VALID_CANDIDATES` maps to `INVALID_ONLY`, preserving candidate IDs and warning metadata.

## Conflict-Aware Completeness
Conflicted and indeterminate attributes remain available but unresolved and unverified. No conflict is resolved or hidden.

## Completeness Metrics
Track required, optional, and total available/resolved/verified/missing/conflicted/indeterminate/invalid counts. Percentages use floor-divided integer basis points; a zero denominator returns 10000.

## Result Model
Immutable lineage, status, all counts/percentages, ordered assessments, warnings, engine `deterministic-completeness-engine-v1`, version, and UTC creation time. No value field.

## DynamoDB Persistence
`attribute-completeness-results` uses `completenessId`/`recordKey`, META and ordered ATTRIBUTE records, conditional creation, 390000-byte guards, consistent paginated reads, complete validation, and sparse `JobIdIndex`.

## Processing Job Lifecycle
Validate pending job/product/conflict/schema lineage before RUNNING; evaluate and persist; then COMPLETED at 100 with `attribute-completeness-results/{id}`. Post-start technical failures attempt FAILED.

## Safety Limits
Maximum 100 schema attributes and 100 candidate IDs per assessment. Never truncate evidence silently.

## Error Handling
Controlled errors cover invalid jobs, missing/cross-product conflict results, unavailable/mismatched schema, limits, engine failure, oversized items, storage, malformed partitions, and completion consistency risk. Incomplete business outcomes are successful.

## Logging Requirements
Log safe lifecycle IDs, category/schema version, result status, required/optional counts and required resolved BP; never raw evidence.

## Security Considerations
Explicit immutable lineage, exact schema fingerprint, bounded arrays, integer-only percentages, no internet/LLM/dynamic rules/filesystem, and no source-content logging.

## Edge Cases
No usable evidence, optional-only evidence, zero required fields, conflict plus missing precedence, missing plus indeterminate precedence, invalid versus missing, and 2/3 floor division.

## Acceptance Criteria
All 137 criteria in the supplied SPEC-026 contract must pass.

## Test Plan
Cover motor/pump schemas, every state mapping, required/optional behavior, precedence, integer percentages, lineage, immutable domain validation, serialization/persistence, lifecycle, failures, and unchanged repository gates.

## Implementation Notes
Status precedence is: no usable attributes, required conflict, required missing/invalid, required indeterminate, complete with single source, complete. Optional states do not alter it.

## Completion Record
Completed on 2026-08-13. Implemented exact-schema completeness evaluation, immutable domain and
serialization models, composite DynamoDB persistence, product-level processing-job orchestration,
controlled failures, safety limits, structured logging, tests, and documentation. The full backend
suite passed with 1,231 tests, 11 skips, and 90.44% coverage; Ruff formatting/lint, strict mypy,
unchanged frontend tests/lint/format/build, Docker Compose validation, and Git whitespace checks
all passed. The optional DynamoDB Local contract test was evaluated but not added because the
repository and table-definition contracts are fully covered without requiring a running local
service.
