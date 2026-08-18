# SPEC-028 — Final Attribute Candidate Selection and Review Preparation Engine

## Status
Completed

## Objective
Produce conservative proposed attribute selections or explicit review requirements without publishing values.

## User Story
As a catalog reviewer, I need corroborated proposals and unresolved alternatives prepared transparently.

## Scope
Backend-only deterministic ranking, proposed selection, review preparation, immutable persistence, lifecycle, tests, and documentation.

## Out of Scope
Product mutation/publication, human decisions, conflict resolution, generated values, APIs, AI/LLM, frontend, S3, authentication, and deployment.

## Functional Requirements
Load four explicitly referenced upstream results, verify exact lineage, evaluate every schema attribute, persist ordered proposals, then complete the job.

## Non-Functional Requirements
Conservative deterministic policy, integer confidence, bounded arrays, immutable inputs, no scans, safe logging, and no hidden reconciliation.

## Existing Dependencies
SPEC-024 normalization, SPEC-025 conflict, SPEC-026 completeness, SPEC-027 validation, job transitions, and composite persistence conventions.

## Selection Input
One explicit conflict, validation, completeness, and normalization result from the same pipeline run.

## Lineage Requirements
Product, normalization, extraction, classification, category, schema version/fingerprint, and direct conflict linkage must match.

## Candidate Eligibility
Only `VALID` candidates auto-select. All warnings block automatic selection in v1; INVALID and NOT_VALIDATABLE never select.

## Candidate Ranking
Equivalent eligible candidates rank by validation, extraction confidence, normalization confidence, then stable candidate ID.

## Agreement-Aware Selection
Exact/tolerance agreement may select only with configured independent-source corroboration and confidence. Tolerance never averages.

## Validation-Aware Selection
Any non-VALID competing assessment blocks auto-selection under the conservative v1 policy.

## Review-Required Conditions
Conflict, indeterminate, single source, warning, insufficient corroboration, or unresolved required evidence requires review.

## Selection Confidence
Integer basis points: exact multi-source 10000, tolerance multi-source 9000, same-source 7000, single-source 6000, conflict 0.

## Selection Reason Model
Stable codes explain exact/tolerance agreement, single source, conflict, indeterminate units, missing/invalid evidence, warnings, and insufficient corroboration.

## Proposed Attribute Model
Ordered immutable state, proposal only for AUTO_SELECTED, primary/supporting IDs, all review IDs, counts, consensus, confidence, reasons, and warnings.

## Product Review Summary
Required and optional auto-selected/review/unresolved counts with deterministic overall status.

## Result Model
Immutable exact lineage, aggregate counts, ordered attributes, review summary, warnings, engine/version, and UTC timestamp.

## DynamoDB Persistence
`attribute-selection-results` stores META plus ordered ATTRIBUTE records using `selectionId`/`recordKey`, sparse JobIdIndex, conditional creation, pagination, and 390000-byte guards.

## Processing Job Lifecycle
Prerequisites precede RUNNING; result persistence precedes COMPLETED at 100; technical failures attempt FAILED.

## Safety Limits
100 attributes, 100 candidate IDs per attribute, 20 reason codes per attribute, configurable source/confidence thresholds.

## Error Handling
Controlled failures cover missing/mismatched upstream data, limits, engine/storage failures, malformed partitions, and completion consistency risk.

## Logging Requirements
Safe IDs, attribute status/counts/confidence and aggregate status only; never evidence content.

## Security Considerations
Explicit lineage, bounded arrays, fixed ranking, no arbitrary rules, mutation, internet, AI, or source logging.

## Edge Cases
Zero candidates, required/optional missing or invalid, same-source repetition, mixed validity, tolerance, and three-candidate conflicts.

## Acceptance Criteria
All 141 supplied criteria must pass.

## Test Plan
Cover exact/converted/tolerance agreement, single/same source, conflicts, warnings/invalid evidence, missing fields, ranking, summaries, persistence, lifecycle, and failures.

## Implementation Notes
Ranking applies only within equivalent groups or review ordering and never overrides conflict status.

## Completion Record
Completed on 2026-08-18. The deterministic selection engine, immutable domain and
persistence models, processing-job lifecycle, configured safety limits, controlled
failures, and architecture documentation are implemented. Verification passed with
1,289 backend tests (11 skipped), 90.71% backend coverage, Ruff lint and formatting,
strict mypy, frontend test/lint/format/build, Docker Compose validation, and Git
whitespace checks. All 141 acceptance criteria were reviewed and satisfied.
