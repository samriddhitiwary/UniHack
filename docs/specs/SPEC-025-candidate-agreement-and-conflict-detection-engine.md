# SPEC-025 — Candidate Agreement and Conflict Detection Engine

## Status
Completed

## Objective
Compare SPEC-024 normalized candidates per canonical attribute and produce explainable agreement, tolerance, conflict, indeterminate, and validity assessments without selecting a value.

## User Story
As a catalog reviewer, I need to see where independent evidence agrees or disagrees while retaining every candidate and its provenance.

## Scope
Backend-only grouping, deterministic Decimal/text comparison, global numeric tolerance, agreement groups, assessment confidence, immutable results, product-level job orchestration, composite DynamoDB persistence, tests, and documentation.

## Out of Scope
Winner selection, ranking, final values, missing-field/completeness detection, business validation, Product mutation, APIs, AI, frontend, S3, authentication, and deployment.

## Functional Requirements
Group only by `attribute_name`; classify each group; retain candidate IDs and distinct sources; explain value groups; aggregate overall status; persist before completing the job.

## Non-Functional Requirements
Deterministic Decimal comparison, bounded attributes/candidates/groups/items, integer basis-point confidence, no scans, immutable upstream input, safe errors/logging, and no semantic similarity.

## Existing Dependencies
SPEC-024 normalization results, SPEC-023 extraction lineage, SPEC-022 schema lineage, SPEC-021 classification lineage, processing-job transitions, and composite persistence conventions.

## Conflict Detection Input
One explicit normalization ID on a product-level `ATTRIBUTE_CONFLICT_DETECTION` job. Never resolve “latest” implicitly or re-normalize candidates.

## Candidate Grouping
Group by canonical attribute name and preserve upstream order within schema-derived candidate order. Different attributes are never compared.

## Comparable Candidate Rules
`NORMALIZED`, `NORMALIZED_WITH_CONVERSION`, and conservative `RAW_TEXT_PRESERVED` values are comparable. Invalid/unsupported candidates are excluded. Unit-missing candidates compare only with other unit-missing candidates; a mixture with unit-bearing numeric candidates is indeterminate.

## Exact Agreement
Two or more comparable candidates with equal Decimal value/unit or equal conservative text comparison forms produce `AGREEMENT`.

## Numeric Agreement
NUMBER values use Decimal and matching canonical units; INTEGER values require exact equality and never use tolerance.

## Numeric Tolerance
NUMBER pairs agree with tolerance when absolute difference ≤ `0.000001` or relative difference ≤ 50 basis points (0.5%). Every pair must fit; no averaging or majority resolution occurs.

## Text Agreement
Trimmed, whitespace-collapsed, case-insensitive exact text equality only. No semantic, fuzzy, or synonym comparison.

## Boolean Agreement
Compare canonical `true`/`false` exactly.

## Enum Agreement
Compare canonical or raw-preserved values conservatively using the same exact text form.

## Incomparable Candidates
Invalid and unsupported candidates remain referenced but excluded. All excluded yields `NO_VALID_CANDIDATES`; a missing-unit/unit-bearing mixture yields `INDETERMINATE`.

## Conflict Types
`VALUE_CONFLICT`, `UNIT_INDETERMINATE`, `MIXED_VALIDITY`, and `MULTIPLE_VALUE_GROUPS`. Valid disagreement uses `VALUE_CONFLICT`; mixed validity is a warning, not a winner rule.

## Attribute Consensus Model
Immutable attribute identity/type/status, candidate/comparable/excluded/source/group counts, conflict type, all candidate IDs, agreement groups, assessment confidence, and warnings. No selected value or winner ID.

## Confidence and Evidence Strength
Assessment confidence: exact independent-source agreement 10000, exact same-source agreement 8500, tolerance independent-source agreement 9000 (same-source 8000), clear conflict 10000, single candidate 6000, indeterminate 5000, and no valid candidates 10000. This measures confidence in the assessment, never candidate truth.

## Result Model
Immutable job/product/normalization/extraction/classification/category/schema lineage, attribute outcome counts, ordered consensus records, warnings, engine `deterministic-conflict-detector-v1`, version, and UTC creation time.

## DynamoDB Persistence
`attribute-conflict-detection-results` uses `conflictDetectionId`/`recordKey`, with `META`, ordered `ATTRIBUTE#`, and `GROUP#attribute#group` records; conditional creation; 390 KB guards; complete pagination; consistent ID reads; and sparse `JobIdIndex`.

## Processing Job Lifecycle
Validate explicit normalization and same-product/internal lineage before PENDING→RUNNING; detect and persist; then RUNNING→COMPLETED at 100 with a result reference. Post-start technical failures attempt FAILED.

## Safety Limits
Maximum 100 attributes, 100 candidates per attribute, and 100 groups per attribute. No silent truncation.

## Error Handling
Controlled errors cover invalid jobs, missing/cross-product normalization, attribute/candidate/group limits, engine failure, oversized items, storage, malformed partitions, and completion consistency risk. Actual conflicts are successful outcomes.

## Logging Requirements
Log safe lifecycle, attribute name, counts, status, conflict type, confidence, and aggregate outcomes; never full evidence excerpts or raw source content.

## Security Considerations
Explicit lineage, Decimal-only numeric operations, fixed comparisons, no arbitrary expressions, no semantic AI/internet/filesystem, and no upstream mutation.

## Edge Cases
Zero comparisons, absolute tolerance near zero, integer disagreement, missing-unit mixtures, all-excluded groups, same-source repetition, multi-source corroboration, three-candidate splits, and equivalent converted candidates.

## Acceptance Criteria
All 135 criteria in the supplied SPEC-025 contract must pass.

## Test Plan
Cover exact/converted/tolerance agreement, conflicts, zero/integer/text/boolean/enum cases, exclusions, missing units, sources, three-candidate splits, confidence, lineage, domain/persistence/lifecycle failures, and all unchanged repository gates.

## Implementation Notes
Tolerance is global and pairwise. Agreement groups use exact normalized comparison keys for explanation and never create a representative final value.

## Completion Record
Completed on 2026-08-13. The implementation groups immutable SPEC-024 candidates, applies
deterministic exact/tolerance/conflict rules, persists explainable META/ATTRIBUTE/GROUP records,
and completes the product-level lifecycle without selecting a value. Verification passed with
1,198 backend tests (11 optional integration skips), 90.30% coverage, Ruff lint/format, strict
mypy, unchanged frontend test/lint/format/build, Docker Compose validation, and Git whitespace.
