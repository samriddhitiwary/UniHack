# Attribute selection and review preparation

SPEC-028 combines one explicit SPEC-024 normalization result, SPEC-025 conflict result, SPEC-026
completeness result, and SPEC-027 validation result from the same product and exact pipeline
lineage. It produces a separate immutable review-preparation artifact and never changes Product or
upstream records.

Only warning-free VALID candidates are eligible for automatic selection. Exact agreement requires
at least two independent sources and 9000 confidence basis points; it receives 10000. Tolerance
agreement uses the same eligibility and source requirements, receives 9000, selects the highest
ranked original normalized candidate, and never averages. Any warning, single candidate,
same-source repetition, conflict, indeterminate comparison, or insufficient confidence requires
review. Genuine conflicts always retain every candidate ID and are never resolved by ranking.

Equivalent candidates rank deterministically by validation status, extraction confidence,
normalization confidence, and stable candidate ID. An auto-selected attribute retains its proposed
normalized value/unit, primary candidate, and every supporting candidate. Review-required
attributes contain no proposal and retain all review candidate IDs. Required missing or invalid-only
attributes require review and yield insufficient data; optional unresolved fields do not downgrade
the required-field overall status.

Overall precedence is `INSUFFICIENT_DATA`, then `REVIEW_REQUIRED`, then
`READY_FOR_AUTO_APPROVAL`. This status is preparation metadata, not publication approval.

The `attribute-selection-results` table stores one META and ordered ATTRIBUTE records under
`selectionId`/`recordKey`. META alone feeds sparse `JobIdIndex`. Conditional creation, paginated
consistent reads, complete partition validation, configured array limits, and the 390,000-byte item
guard apply.

The internal job service verifies every upstream reference before RUNNING, persists before
COMPLETED, and attempts FAILED only for technical errors. A completion update failure preserves the
selection result and logs a consistency-risk event. No API, reviewer decision, publication,
materialization, AI, or frontend behavior is included.
