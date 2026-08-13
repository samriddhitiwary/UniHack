# Candidate Agreement and Conflict Detection

SPEC-025 adds a deterministic product-level stage that consumes one explicit immutable SPEC-024
normalization result. Candidates are grouped only by `attribute_name`; candidate and source IDs
remain intact. The stage reports whether evidence agrees, conflicts, or cannot safely be compared.
It never selects a winning or final value.

## Comparison policy

- `NORMALIZED`, `NORMALIZED_WITH_CONVERSION`, and `RAW_TEXT_PRESERVED` candidates are directly
  comparable. `UNSUPPORTED_UNIT` and `INVALID_VALUE` candidates are excluded and warned.
- Numeric values use `Decimal`, equal canonical units, a global 50-basis-point relative tolerance,
  and `0.000001` absolute tolerance. Integers remain exact-only.
- A unit-missing candidate mixed with unit-bearing evidence is `INDETERMINATE`; no unit is guessed.
- Text, Boolean, and enum values use collapsed whitespace and case-insensitive exact comparison.
  There is no fuzzy or semantic matching.
- `415, 415, 440` remains a conflict. Agreement groups explain the clusters but never rank them.

The result statuses are `NO_CONFLICTS`, `CONFLICTS_FOUND`, `COMPLETED_WITH_WARNINGS`, and
`NO_COMPARABLE_ATTRIBUTES`. All are successful technical outcomes. Confidence is an integer basis
point assessment of agreement/conflict detection, not confidence that a particular value is true.

## Lifecycle and storage

`ATTRIBUTE_CONFLICT_DETECTION` is an internal product-level job with no source ID and one required
`attribute_normalization_id`. Validation occurs before RUNNING. The immutable result is persisted
before COMPLETED; post-start technical errors transition to FAILED. If completion persistence fails,
the result remains available and a consistency-risk event is logged.

The composite DynamoDB table uses `conflictDetectionId`/`recordKey`, with `META`, ordered
`ATTRIBUTE#...`, and `GROUP#...` records. Sparse `JobIdIndex` lookup, consistent paginated partition
reads, conditional writes, a 390,000-byte item guard, and configured attribute/candidate/group limits
avoid scans and silent truncation. No public API, product mutation, missing-field detection, business
validation, LLM, frontend feature, or deployment behavior is included.
