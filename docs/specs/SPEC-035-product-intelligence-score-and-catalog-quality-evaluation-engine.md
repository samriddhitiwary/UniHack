# SPEC-035 — Product Intelligence Score and Catalog Quality Evaluation Engine

## Status
Completed

## Objective
Produce a deterministic, explainable score of catalog information quality from one explicit
projection and its exact persisted pipeline lineage.

## User Story
As a catalog operator, I need component scores and prioritized improvement codes so I can understand
catalog data quality without confusing it with physical product quality or publishing readiness.

## Scope
Product-level scoring jobs, six deterministic component scorers, normalized integer weights, grades,
explanations, immutable persistence/history, tests, and documentation.

## Out of Scope
LLM scoring, Product or upstream mutation, publishing, public APIs, frontend, external services,
authentication, authorization, S3, and deployment.

## Functional Requirements
Use an explicit projection as the root, derive and load its exact completeness, validation, conflict,
selection, review, and materialization artifacts, optionally load an explicit compatible enrichment,
score coherent inputs, persist the result, and complete the job.

## Non-Functional Requirements
Integer-only bounded deterministic arithmetic, immutable outputs, exact lineage, no scans, safe logs,
conditional idempotency, >=90% coverage, and no network/provider calls.

## Existing Dependencies
SPEC-025 conflict evidence, SPEC-026 completeness, SPEC-027 validation, SPEC-028 selection, SPEC-029
review, SPEC-030 materialization, SPEC-031 projection/readiness, and optional SPEC-034 enrichment.

## Evaluation Input
Required explicit `catalog_projection_id`; optional explicit `enrichment_id`. All core identifiers are
derived from projection lineage. No latest-result lookups or mixed pipelines.

## Scoring Philosophy
The score measures completeness, validation, independent evidence, conflict history, automation/
review intervention, and optional AI grounding of catalog data—not physical product quality.

## Score Components
COMPLETENESS, VALIDATION_QUALITY, SOURCE_CORROBORATION, CONFLICT_HEALTH, REVIEW_QUALITY, and optional
AI_GROUNDING_QUALITY, each with status, raw score, weights, contribution, reasons, and metrics.

## Completeness Score
85% required resolved and 15% optional resolved; when no optional attributes exist, required receives
the full component. Required missing/conflicted/invalid/indeterminate metrics remain distinct.

## Validation Quality Score
Required attributes have importance two and optional one. VALID=10000, VALID_WITH_WARNINGS=8000,
validated HUMAN_OVERRIDE=8500. Invalid final candidate lineage is a technical failure.

## Source Corroboration Score
Distinct sources only: >=3=10000, 2=9000, 1=6000, human override/no source=5000. Required attributes
have importance two. Repeated evidence from one source is never counted independently.

## Conflict Health Score
AGREEMENT=10000, tolerance agreement=9500, single candidate=8000, conflict resolved by candidate=7000,
conflict resolved by override=6000, and indeterminate resolved by review=6500.

## Review Quality Score
APPROVED_PROPOSED=10000, APPROVED_CANDIDATE=8500, HUMAN_OVERRIDE=7000. This measures automation
intervention and never labels human-reviewed data invalid.

## AI Grounding Quality Score
When compatible enrichment is supplied: 80% grounding score plus 20% fact coverage. When absent it is
NOT_EVALUATED with zero normalized weight and no quality penalty.

## Overall Product Intelligence Score
Evaluated base weights are normalized to exactly 10000 in stable component order, contributions use
integer division, and overall is their bounded sum. No hidden/global deduction layer exists.

## Grade Model
EXCELLENT >=9000, GOOD >=8000, FAIR >=6500, POOR >=5000, otherwise CRITICAL. Display percent is
nearest integer `(scoreBp + 50) // 100`.

## Strengths
Stable component and overall codes identify complete, validated, corroborated, low-conflict,
minimally manual, and grounded catalog information.

## Improvement Reasons
Deterministic action codes are deduplicated. Up to five top improvements prioritize required gaps,
invalid/indeterminate data, conflicts, weak required corroboration, warnings, overrides, optional
coverage, then AI coverage.

## Penalties
All quality effects are embedded in documented component formulas. There are no arbitrary point
subtractions and no extra overall penalty layer.

## Required vs Optional Attributes
Required data dominates completeness and carries double per-attribute influence for validation and
corroboration. Optional gaps remain visible but have smaller influence.

## Missing AI Enrichment Behaviour
AI_GROUNDING_QUALITY is NOT_EVALUATED; its base weight is redistributed across core components and
AI_ENRICHMENT_NOT_EVALUATED is informational.

## Score Explainability
Every component stores bounded integer metrics and stable strength/improvement codes; no LLM prose or
free-form formula expression is used.

## Result Model
Immutable score, component, and metric models preserve full projection/upstream/enrichment lineage,
projection status, overall score/grade, reasons, policy, engine, and UTC creation time.

## DynamoDB Persistence
`product-intelligence-score-results` stores META and six COMPONENT records, sparse JobIdIndex,
ProductCreatedAtIndex, ProjectionIdIndex, an exact-input guard, conditional writes, query-only access,
complete reconstruction, and 390000-byte item limits.

## Processing Job Lifecycle
All deterministic setup occurs before PENDING→RUNNING. Result persistence precedes COMPLETED with
`product-intelligence-score-results/{scoreId}`. Technical failures after RUNNING attempt FAILED;
completion failure retains the valid score.

## Idempotency
One result per projection ID, enrichment ID-or-NONE, and policy version using a SHA-256 transactional
guard. Future policy or input revisions may create new history.

## Safety Limits
Six components, 100 reason codes, five top improvements, 100 metric entries, and 390000 serialized
bytes per DynamoDB record.

## Error Handling
Controlled errors cover missing/cross-product/mismatched lineage, absent required artifacts,
enrichment mismatch, invalid components/weights, limits, duplicates, serialization/storage, and
engine failures.

## Logging Requirements
Log only safe IDs, status, component scores/weights, grade, reason counts, policy, and lifecycle. Do
not log product content, reviewed values, evidence, or secrets.

## Security Considerations
Explicit immutable lineage, bounded integer formulas, no arbitrary expressions, no AI/network calls,
no raw evidence duplication, immutable writes, and no mutation of authoritative records.

## Edge Cases
Zero optional attributes, missing AI, BLOCKED projections, tolerance agreement, same-source repeats,
resolved conflicts, human overrides, integer remainders, grade boundaries, duplicates, corrupt
lineage, incomplete partitions, and completion consistency risk.

## Acceptance Criteria
All 205 supplied criteria pass within SPEC-035 scope.

## Test Plan
Cover every formula, missing AI redistribution, perfect/boundary scores, explanations, lineage,
immutability, persistence/history/idempotency, lifecycle/failure, repository-wide regression gates,
and optional DynamoDB Local.

## Implementation Notes
Policy `product-intelligence-score-v1`; engine `deterministic-product-intelligence-scorer-v1`.
Projection readiness is preserved and remains orthogonal to score and grade.

## Completion Record
Completed on 2026-08-20. Implemented six deterministic integer component scorers, stable
explanations, exact weight normalization, grades, full immutable lineage, optional enrichment,
transactional idempotency, query-only DynamoDB persistence/history, internal job orchestration,
controlled failures, safe logging, configuration limits, local table creation, schemas, tests, and
architecture documentation. No public API, frontend feature, LLM scoring, network call, Product or
upstream mutation, S3, authentication, publishing, or deployment behavior was added.

Verification: 1,557 backend tests passed and 16 optional integrations skipped; backend coverage
90.13%; Ruff lint and formatting clean; strict mypy clean across 281 source files; frontend test,
lint, formatting, and build clean; Docker Compose config and Git whitespace clean.
