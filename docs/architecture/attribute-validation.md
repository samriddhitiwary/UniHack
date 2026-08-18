# Attribute validation

SPEC-027 validates every candidate from one explicitly referenced SPEC-024 normalization result
against the exact SPEC-022 schema version and fingerprint. It never selects a winner, resolves an
upstream conflict, recalculates completeness, or mutates input data.

NUMBER and INTEGER values use Decimal parsing; integers must be exact. Configured minimum and
maximum boundaries are inclusive. Allowed values require exact canonical equality, and bounded
trusted schema patterns use full-match semantics. Canonical normalized units must be compatible
with the schema. Missing units produce warnings without inference; unsupported units produce
errors. An upstream `INVALID_VALUE` produces `NOT_VALIDATABLE` without downstream range checks.

Every immutable assessment retains normalized/source candidate IDs, source ID, attribute metadata,
normalized value/unit, safe issue codes and counts, evidence type/location, and UTC creation time.
Attribute summaries aggregate statuses without selecting values. Result status is deterministic:
all-not-validatable (including zero candidates), any invalid/not-validatable, any warning, then all
valid.

The `attribute-validation-results` table stores one META record, ordered ASSESSMENT records with
bounded embedded issues, and ordered SUMMARY records under `validationId`/`recordKey`. META alone
feeds sparse `JobIdIndex`. Conditional creation, paginated consistent retrieval, complete partition
validation, configured limits, and a 390,000-byte item guard apply.

The internal product-level service validates all prerequisites before `PENDING → RUNNING`, persists
before `RUNNING → COMPLETED`, and sets a logical result reference. Candidate invalidity is a
successful business outcome. Technical rule, lineage, limit, engine, or persistence failures attempt
`FAILED`; a completion update failure preserves the result and logs a consistency-risk event.
