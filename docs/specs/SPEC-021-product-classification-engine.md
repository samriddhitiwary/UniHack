# SPEC-021 — Product Classification Engine

## Status
Complete

## Objective
Classify a product as a centrifugal pump, induction motor, or unclassified using bounded extracted evidence and deterministic explainable rules.

## User Story
As a later catalog workflow, I need a reviewable category prediction with scores, confidence, provenance, and conflicts without automatically changing the product.

## Scope
Product-level classification jobs, bounded aggregation of direct text/PDF text/PDF tables/CSV/image OCR evidence, phrase-aware rules, integer scoring/confidence, ambiguity/conflict outcomes, composite persistence, lifecycle orchestration, tests, and documentation.

## Out of Scope
Structured attributes, category schemas, numeric/unit normalization, validation, source-value conflict resolution, category auto-apply, LLM/AI enrichment, APIs, workers, frontend, S3, authentication, authorization, and deployment.

## Functional Requirements
Process only PENDING product-level `PRODUCT_CLASSIFICATION` jobs with no source ID. Validate the product, aggregate available processed evidence through repositories, classify deterministically, persist explainable matches, and complete all valid uncertainty outcomes.

## Non-Functional Requirements
Backend-only, immutable bounded evidence/results, repository abstractions, no raw file reads, no network/LLM, no float persistence, safe logging, deterministic ordering and scoring, and no Product/ProductSource mutation.

## Existing Dependencies
ProductCategory, Product/ProductSource repositories, extraction/OCR result repositories, processing-job lifecycle and product index, composite DynamoDB conventions, configuration, exceptions, and logging.

## Classification Input Evidence
Direct TEXT source content; PDF extraction pages; PDF table cells; CSV headers and nonempty cells; and image OCR blocks with OCR confidence. Missing optional extraction outputs are ignored.

## Supported Categories
Exactly `CENTRIFUGAL_PUMP`, `INDUCTION_MOTOR`, and `UNCLASSIFIED`.

## Evidence Aggregation
Page product sources deterministically, then page source job history and retrieve the newest available result for each supported result type. Emit bounded provenance-bearing evidence items in source order with type, location, original text, and integer weight.

## Classification Rules
Use curated pump and motor phrases with STRONG=10, MEDIUM=4, WEAK=1. Match phrases using case-insensitive token/word boundaries. Weight direct/PDF text 100, PDF table cells and CSV headers 110, CSV cells 90, and image OCR by confidence from base weight 100.

## Score and Confidence Model
Category score is the integer sum of signal strength × evidence weight. Classification requires a score of at least 1,000 and a margin of at least 300. Confidence basis points are `min(10000, margin * 10000 // max(winner, minimumScore))`; this is deterministic score separation, not an ML probability.

## Conflict and Ambiguity Handling
Both categories below threshold is INSUFFICIENT_EVIDENCE. Both categories supported strongly by distinct sources is CONFLICTING_EVIDENCE. Scores within the configured margin are AMBIGUOUS. All produce UNCLASSIFIED and complete successfully.

## Classification Result Model
Immutable result identities, ProductCategory, classification status, basis-point confidence, pump/motor scores, evidence/match/conflict counts, bounded ordered matches, warnings, stable engine/version, and UTC creation time.

## DynamoDB Persistence
Use `{prefix}-product-classification-results`, `classificationId`/`recordKey`, META and `MATCH#{index:06d}`, sparse JobIdIndex, conditional creation, paginated reconstruction, completeness validation, and a 390,000-byte item guard.

## Processing Job Lifecycle
Add product-level `PRODUCT_CLASSIFICATION` with `sourceId=None`. Existing source job APIs remain source-specific and reject this type. Validate before start; transition PENDING→RUNNING, aggregate/classify/persist, then RUNNING→COMPLETED at progress 100 with `product-classification-results/{classificationId}`. Technical failures attempt FAILED.

## Error Handling
Controlled errors cover invalid jobs, missing products, evidence/match limits, engine failures, oversized items, duplicate/serialization/repository failures, and completion consistency risk. Uncertainty is not an error.

## Logging Requirements
Log safe IDs, category/status, confidence, integer scores, counts, source count, engine/version, and controlled codes. Never log evidence, excerpts, OCR/direct/CSV/PDF contents, raw records, or raw errors.

## Security Considerations
Bound evidence and matches, use repository protocols only, avoid raw files/network/LLM, persist no floats/full documents, keep excerpts bounded, and preserve explainable deterministic rules.

## Edge Cases
No sources, unprocessed sources, empty records, repeated phrases, punctuation/case/newlines/hyphens/Unicode units, substring traps, balanced scores, strong cross-source conflict, pagination, partial persistence, and final update failure.

## Acceptance Criteria
All 108 criteria in the controlling amendment must pass with coverage at least 90%, complete verification, accurate documentation, and scope audit.

## Test Plan
Test every evidence type and provenance/location; all bounds; pump/motor/boundary/ambiguous/conflict/insufficient rules; confidence monotonicity; immutable domain/serialization/repository/lifecycle/failure behavior; optional DynamoDB Local; and the full repository matrix.

## Implementation Notes
Product-level jobs use nullable source identity only for `PRODUCT_CLASSIFICATION`; all existing source job types require a source. SourceScope remains sparse for product-level jobs, so source queries cannot include them while product queries can. Product.category remains unchanged.

## Completion Record
Completed on 2026-08-13. Implemented product-level classification jobs; bounded aggregation for
all six evidence types; deterministic pump/motor scoring, confidence, ambiguity, insufficiency,
and cross-source conflict decisions; immutable traceable results; composite DynamoDB persistence;
controlled lifecycle failures; local table creation; tests; and architecture/API documentation.
The full backend suite passed 1,066 tests with 90.83% coverage and 10 opt-in skips. Ruff, formatting,
strict mypy, frontend test/lint/format/build, Docker Compose validation, and Git whitespace checks
passed. Product.category remains unchanged, and no classification API, LLM, attribute extraction,
frontend feature, S3, worker, or deployment behavior was added.
