# SPEC-023 — Structured Attribute Extraction Engine

## Status
Completed

## Objective
Convert bounded existing product evidence into traceable, unnormalized structured attribute candidates using the exact classified category and immutable schema lineage.

## User Story
As a catalog reviewer, I need every deterministic attribute candidate preserved with its raw value, raw unit, confidence, and source location without prematurely selecting or normalizing a value.

## Scope
Product-level ATTRIBUTE_EXTRACTION jobs with explicit classification lineage; multi-source evidence aggregation; schema alias matching; conservative typed raw parsing; confidence and duplicate handling; composite persistence; lifecycle orchestration; tests; local table support; and documentation.

## Out of Scope
Unit normalization/conversion, canonical numeric values, winning-value selection, conflicts, missing fields, actual-value validation, Product mutation, AI/LLM, APIs, workers/retries, frontend, S3, authentication, authorization, and deployment.

## Functional Requirements
Validate product/job/explicit classified result/active matching schema before RUNNING; aggregate available direct text and processed PDF/table/CSV/OCR evidence; emit multiple deterministic candidates with raw values/units and provenance; persist before completion; complete valid no-candidate/warning outcomes.

## Non-Functional Requirements
Backend-only, deterministic integer arithmetic, immutable bounded data, repository abstractions, no raw file access/network/floats/content logging, exact lineage, no mutation, and no semantic/fuzzy inference.

## Existing Dependencies
SPEC-021 classification results, SPEC-022 schemas and alias normalization, ProductSource/extraction repositories, processing lifecycle, composite DynamoDB conventions, configuration, exceptions, and logging.

## Extraction Inputs
Direct TEXT lines, PDF page lines, adjacent PDF table cells/rows, safe single-row CSV header/value pairs, and OCR block lines. No raw files, pixels, filenames, or internet.

## Classification Dependency
Each ATTRIBUTE_EXTRACTION job explicitly stores `classification_id`. It must reference a CLASSIFIED supported-category result owned by the same product. This avoids ambiguous latest-result selection and global scans.

## Category Schema Dependency
Resolve the current ACTIVE schema for the classified category before RUNNING and require its immutable category. Persist its version and fingerprint with the extraction result.

## Evidence Aggregation
Page sources and completed source jobs deterministically, convert heterogeneous output to bounded evidence with raw/normalized text, location, source quality, and optional structural label/value hints. Multi-row CSV without product-row identity is skipped with a warning.

## Attribute Label Matching
Reuse SPEC-022 canonical/display/alias metadata and normalization. Support exact case-insensitive and normalized label-first matches plus contextual adjacent-cell matches. No fuzzy synonyms or embeddings.

## Raw Value Extraction
NUMBER uses signed dot-decimal strings; INTEGER uses signed integers; TEXT/ENUM preserve trimmed text; BOOLEAN accepts only exact yes/no/true/false. Unsafe/absent values produce warnings rather than invented candidates.

## Raw Unit Extraction
Use allowed units as case/separator/superscript-comparison hints and preserve the exact raw spelling found. Missing units remain null. No normalization or conversion.

## Candidate Model
Immutable stable candidate ID, canonical/display/type, raw value/unit, source/evidence/location/excerpt, matched label/type, confidence/source quality, parse status, and UTC creation time.

## Confidence Model
Integer basis points: `labelQuality × sourceQuality × parseQuality // 10000²`, clamped 0–10000. Label quality EXACT 9000, NORMALIZED 8000, CONTEXTUAL 8500; source baselines table/CSV 9500, direct 9000, PDF text 8500, OCR confidence; parse quality numeric+recognized unit 10000, numeric without expected unit 8500, text/enum/boolean 9000.

## Evidence Provenance
Preserve source ID and bounded exact excerpt with direct source, PDF page/line, table page/table/row/column, CSV row/column/header, or OCR region/block locations.

## Duplicate Candidate Handling
Suppress only identical attribute/raw value/raw unit from the same source, evidence type, and location; count suppression. Preserve identical or conflicting values from independent locations/sources. Sort by schema order, confidence descending, evidence order, stable ID.

## Result Model
Immutable extraction/job/product/classification/category/schema lineage, outcome, candidate/evidence/distinct-attribute/duplicate counts, ordered candidates, warnings, stable engine/version, and UTC creation time.

## DynamoDB Persistence
Use `{prefix}-structured-attribute-extraction-results` with extractionId/recordKey, META and ordered CANDIDATE records, sparse JobIdIndex, conditional creation, paginated complete reconstruction, no scans, and 390,000-byte item guards.

## Processing Job Lifecycle
ATTRIBUTE_EXTRACTION is product-level with no source and requires classification ID. Validate setup before PENDING→RUNNING; collect/extract/persist; RUNNING→COMPLETED at 100 with `structured-attribute-extraction-results/{extractionId}`. Post-start technical failures attempt FAILED.

## Safety Limits
Defaults: 10,000 evidence items, 1,000,000 total evidence characters, 10,000 per item, 5,000 candidates, 100 candidates per attribute, and 1,000 excerpt characters. All are positive and fail rather than truncate.

## Error Handling
Controlled setup errors cover invalid jobs, missing products, missing/uncertain/mismatched classification, and unavailable schema. Controlled runtime failures cover evidence/candidate limits, engine, item size, serialization/storage, and completion consistency risk.

## Logging Requirements
Log IDs, lineage, category/schema, counts, outcome, engine/version, and safe codes. Never log evidence pages, OCR/CSV/source contents, candidate excerpts, or raw repository items.

## Security Considerations
Classified supported categories only, exact explicit lineage, bounded evidence/candidates/excerpts, no executable schema rules, no file/network/LLM access, no floats, no content logging, and immutable inputs/results.

## Edge Cases
No evidence/candidates, label-only lines, missing units, unitless fields, punctuation/case, signed decimals, unsafe booleans, table adjacency, multi-row CSV ambiguity, low OCR confidence, duplicate parser paths, independent equal/conflicting candidates, pagination, partial persistence, and final completion failure.

## Acceptance Criteria
All 133 controlling criteria must pass, coverage remain at least 90%, documentation and scope audit complete, and all existing behavior remain green.

## Test Plan
Evidence types/bounds/order/provenance; aliases and no fuzzy guesses; typed raw parsing/units; motor/pump engines; confidence/duplicates/multiple conflicts; immutable domain; schemas/serialization/repository completeness; lifecycle/setup/runtime failures; optional DynamoDB Local; full repository verification.

## Implementation Notes
Explicit `classification_id` on the product-level job is the input lineage. CSV v1 extracts header/value candidates only when exactly one row exists; otherwise it emits `MULTI_ROW_CSV_SKIPPED`. Patterns remain conservative and label-first.

## Completion Record
Pending implementation and verification.
