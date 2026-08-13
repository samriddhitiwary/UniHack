# SPEC-024 — Attribute and Unit Normalization Engine

## Status
Completed

## Objective
Normalize each SPEC-023 raw candidate into deterministic canonical values and units while preserving raw data and complete lineage.

## User Story
As a catalog reviewer, I need comparable canonical candidate values without losing the evidence needed to audit them.

## Scope
Backend-only Decimal parsing, conservative scalar normalization, schema-compatible unit recognition/conversion, immutable results, product-level job orchestration, composite DynamoDB persistence, tests, and documentation.

## Out of Scope
Final selection, agreement scoring, conflict resolution, missing-field detection, business validation, Product mutation, APIs, AI, frontend, object storage, authentication, and deployment.

## Functional Requirements
Normalize candidates independently; retain equivalent and conflicting candidates; classify candidate outcomes; persist a result before completing its job; and retrieve results by normalization or job ID.

## Non-Functional Requirements
Deterministic output, Decimal-only arithmetic, integer confidence basis points, bounded strings/counts/items, no scans, safe errors, immutable lineage, and no evidence logging.

## Existing Dependencies
SPEC-023 extraction results and candidates, SPEC-022 exact category schema versions, existing processing-job transitions, repository conventions, and DynamoDB serialization primitives.

## Normalization Input
An explicit extraction ID on an `ATTRIBUTE_NORMALIZATION` product-level job. The referenced extraction must exist and belong to that product.

## Schema Dependency
Load the extraction's exact category/version and reject missing schemas or fingerprint mismatch. Never silently use the active or latest schema.

## Candidate Lineage
Each candidate retains source candidate/extraction IDs, classification, category, schema version/fingerprint, source ID, evidence type/location/excerpt, raw value/unit, and extraction confidence.

## Numeric Normalization
Parse only signed base-10 integer/decimal strings with `Decimal`; reject prose, scientific notation, multiple dots, and decimal commas. Persist plain strings with no leading plus, trailing zeroes, scientific notation, or negative zero.

## Integer Normalization
Require an exact integral Decimal before and after conversion; never round an integer candidate into validity.

## Text Normalization
Normalize line endings, trim outer space, collapse horizontal whitespace, and preserve case except exact `ipRating`, `insulationClass`, and `duty` canonicalizations.

## Boolean Normalization
Map exact normalized true/yes/y/1 and false/no/n/0 tokens to lowercase `true`/`false`; other values are invalid.

## Enum Normalization
Match schema allowed values case-insensitively after whitespace normalization. Unknown enum text is preserved with `RAW_TEXT_PRESERVED`.

## Unit Recognition
Recognize only the fixed aliases needed by the motor and pump schemas and verify the matched dimension against the attribute's allowed units and attribute-specific canonical-unit policy.

## Canonical Units
Power kW; voltage V; current A; frequency Hz; speed rpm; percentage %; flow m3/h; head/NPSH m; connection/diameter mm; pressure bar.

## Unit Conversion
W×0.001 and mechanical hp×0.745699872 to kW; L/min×0.06 and US gpm×0.22712470704 to m3/h; ft×0.3048 to m; in×25.4 to mm; psi×0.0689475729 to bar.

## Precision and Decimal Policy
Retain exact Decimal results up to configurable six decimal places. Quantize only excess fractional precision using `ROUND_HALF_UP`.

## Normalization Status
Candidate: `NORMALIZED`, `NORMALIZED_WITH_CONVERSION`, `UNIT_MISSING`, `UNSUPPORTED_UNIT`, `INVALID_VALUE`, or `RAW_TEXT_PRESERVED`. Result: `NORMALIZED`, `NORMALIZED_WITH_WARNINGS`, or `NO_CANDIDATES`.

## Normalized Candidate Model
Immutable raw/canonical values, conversion metadata, provenance, separate extraction/normalization confidence, and UTC timestamp.

## Result Model
Immutable normalization/job/product/extraction/classification/schema lineage, candidate/outcome counts, ordered candidates, warnings, engine/version, and UTC timestamp.

## DynamoDB Persistence
`attribute-normalization-results` uses `normalizationId`/`recordKey`, with `META`, ordered `CANDIDATE#` records, conditional creation, 390 KB guards, full pagination, consistent ID reads, and sparse `JobIdIndex` on metadata.

## Processing Job Lifecycle
Product-level `ATTRIBUTE_NORMALIZATION` jobs require an explicit extraction ID. Validate all prerequisites before PENDING→RUNNING, persist before RUNNING→COMPLETED at 100%, and attempt FAILED after technical post-start errors.

## Safety Limits
Maximum 5,000 candidates and 10,000 normalized-value characters; item maximum 390,000 bytes; maximum decimal places defaults to six.

## Error Handling
Controlled errors cover invalid jobs, missing/cross-product extraction, unavailable/mismatched schema, candidate limits, engine failures, oversized items, and storage. Candidate data problems remain successful warning outcomes.

## Logging Requirements
Log safe lifecycle and aggregate outcome metadata only. Never log raw values, excerpts, or full evidence.

## Security Considerations
No dynamic expressions, float conversions, internet, LLM, filesystem, source-object reads, or mutable lineage.

## Edge Cases
Zero and negative zero, excess precision, missing/unsupported units, unitless numbers, malformed decimals, fractional integers, unknown enums, empty extraction, equivalent canonical values, and conflicting values.

## Acceptance Criteria
All 133 criteria in the supplied SPEC-024 contract must pass, including repository-wide quality gates and scope exclusions.

## Test Plan
Unit-test Decimal formatting, all required conversions and aliases, scalar types, precision, warnings, preservation, lineage, domain invariants, repository behavior, lifecycle/failures, and unchanged prior features.

## Implementation Notes
The unit registry is fixed code mapped to existing schema attribute names/dimensions. Horsepower means mechanical horsepower and gpm means US gallons per minute. Decimal comma is not inferred.

## Completion Record
Completed with deterministic Decimal normalization, fixed schema-compatible unit conversion, immutable lineage, composite persistence, lifecycle orchestration, documentation, and all repository verification gates passing.
