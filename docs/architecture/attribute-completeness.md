# Attribute Completeness

SPEC-026 consumes one explicit immutable SPEC-025 result and its exact SPEC-022 schema. Every
schema attribute is evaluated in display order as `PRESENT`, `PRESENT_WITH_TOLERANCE`,
`PRESENT_SINGLE_SOURCE`, `CONFLICTED`, `INDETERMINATE`, `INVALID_ONLY`, or `MISSING`.

Available evidence includes present, conflicted, and indeterminate states. Resolved evidence is
present (including single-source); verified evidence is corroborated exact or tolerance agreement.
Invalid evidence remains distinct from absent evidence. Required, optional, and total counts are
stored separately, with integer basis-point percentages. A zero denominator yields 10000.

Overall precedence is no usable attributes, required conflict, required missing/invalid, required
indeterminate, complete with single-source, then complete. Optional deficiencies never downgrade
required completeness. The engine neither selects nor generates a value and performs no business
validation.

Results use composite `completenessId`/`recordKey` storage with META and ordered ATTRIBUTE records,
a sparse `JobIdIndex`, conditional writes, consistent paginated reads, complete reconstruction,
configured limits, and a 390000-byte guard. The result persists before the internal product-level
`ATTRIBUTE_COMPLETENESS` job completes.
