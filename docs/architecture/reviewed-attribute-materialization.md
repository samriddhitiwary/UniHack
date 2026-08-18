# Reviewed Attribute Materialization

SPEC-030 converts exactly one completed product review into a separate, immutable authoritative
attribute artifact. It does not modify the Product record or make a publishing decision.

## Prerequisites and flow

`REVIEWED_ATTRIBUTE_MATERIALIZATION` is a product-level processing job with `sourceId = null` and
an explicit `reviewId`. Before the job enters `RUNNING`, the service verifies the PENDING job,
Product, review ownership, COMPLETED review state, exact selection/validation/normalization
lineage, and category schema version and fingerprint. There is no implicit latest-review lookup.

```text
PENDING job + completed review
  -> resolve CURRENT projections against immutable decision history
  -> verify exact schema and candidate lineage
  -> materialize required and resolved optional attributes in schema order
  -> conditionally persist immutable META + ATTRIBUTE records
  -> complete job with reviewed-attribute-results/{materializationId}
```

Setup failures leave the job PENDING. Materialization or persistence failures after start attempt a
transition to FAILED. The artifact is persisted before the completion transition; a completion
write failure is logged as a consistency risk and never causes the artifact to be deleted.

## Effective decisions

Each CURRENT projection must reference the matching latest immutable history record for the same
review, product, attribute, sequence, and decision type. Historical decisions remain audit history
but do not produce duplicate final attributes.

- `APPROVE_PROPOSED` must reference the persisted primary proposed candidate.
- `APPROVE_CANDIDATE` must reference one persisted review candidate.
- `MANUAL_OVERRIDE` preserves the approved canonical value/unit and raw human input, with no
  candidate, source, confidence, or validation lineage.
- `REJECT_ALL` and missing decisions are allowed only for optional fields.

Candidate-origin records preserve the review decision, reviewer, normalized/source candidate,
source, selection confidence, and validation status—including `VALID_WITH_WARNINGS`. The engine
does not rerank, reselect, resolve conflicts, or revalidate.

## Required, optional, and immutable output

Every required schema attribute must materialize exactly once or the operation fails without a
successful artifact. Resolved optional attributes materialize normally; unresolved optional
attributes have no placeholder record and contribute to `unresolvedOptionalCount`. Output follows
schema display order and all domain records are frozen.

The aggregate preserves review, selection, conflict, validation, completeness, normalization,
extraction, classification, category, schema version, and schema fingerprint lineage. Numeric
values remain canonical strings; floats are not introduced.

## Persistence and idempotency

`reviewed-attribute-results` uses `materializationId` plus `recordKey`. `META` stores lineage and
counts; ordered `ATTRIBUTE#000001` records store final values and audit lineage. Only META records
carry `jobId`, `reviewId`, and `createdAt`, keeping `JobIdIndex` and `ReviewIdIndex` sparse.

A conditional META write and `REVIEW#{reviewId}` uniqueness guard enforce one materialization per
review. Attribute writes are conditional and never overwrite. Retrieval by result, job, or review
uses queries only, reconstructs the full partition, and rejects incomplete partitions. Records are
bounded to 100 attributes, 10,000-character values, and 390,000 serialized bytes per item.

## Scope boundary

This artifact is authoritative reviewed data, not commerce content. SPEC-030 adds no API,
frontend, Product attribute mutation, `READY_TO_PUBLISH` state, publishing/export logic, AI, S3,
authentication, worker, or deployment behavior.
