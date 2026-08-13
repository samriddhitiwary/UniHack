# Structured Attribute Extraction

SPEC-023 adds a deterministic, product-level candidate extraction pipeline. An
`ATTRIBUTE_EXTRACTION` processing job has no source ID and carries the exact
classification ID it consumes. Before the job starts, the service verifies the
product, a same-product `CLASSIFIED` result, and the active schema for that
classification category.

## Evidence and candidates

The aggregator reads only persisted source and extraction results. Direct text
and PDF text are line-oriented; adjacent PDF table cells and a safe single CSV
data row provide label/value context; OCR lines preserve block confidence. Raw
objects are never opened by this feature. Multi-row CSV is skipped with a
warning because row-to-product identity is ambiguous in v1.

Labels use the immutable schema's canonical name, display name, and aliases.
Matching is exact, normalized, or structural/contextual—never fuzzy. Parsing is
deliberately conservative: signed decimal strings, integer strings, exact
boolean tokens, and raw text are retained without unit conversion, canonical
normalization, range validation, candidate selection, or conflict resolution.
Every candidate retains source, evidence, location, excerpt, label, match type,
parse status, source quality, and integer basis-point confidence.

## Limits and persistence

Evidence is bounded at 10,000 items, 1,000,000 total characters, and 10,000
characters per item. Results allow 5,000 candidates, 100 per attribute, and
1,000-character excerpts. Exact same-source/location/value duplicates are
suppressed; conflicting or independently located candidates remain visible.

`structured-attribute-extraction-results` uses `extractionId` plus `recordKey`.
`META` stores lineage and counts; ordered `CANDIDATE#000001` records store
candidates. The sparse `JobIdIndex` uses `jobId` and `createdAt`. Reads paginate
to completion and ID reads are strongly consistent. A result is persisted
before its job is completed; a completion-write failure is logged as a
consistency risk without deleting the persisted result.

No-candidate extraction is successful and completes with `NO_CANDIDATES`.
