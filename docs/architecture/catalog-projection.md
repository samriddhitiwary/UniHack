# Commerce Catalog Projection and Publishing Readiness

SPEC-031 creates one immutable, commerce-oriented snapshot from an existing Product and one
explicit SPEC-030 reviewed-attribute materialization. Readiness is an internal assessment only: no
data is published, exported, enriched, or written back to Product.

## Input and coherence

`CATALOG_PROJECTION` is a product-level processing job with `sourceId = null` and an explicit
`reviewedAttributeMaterializationId`. Before RUNNING, orchestration requires a PENDING job, the
Product, the exact MATERIALIZED artifact, matching ownership/category, coherent reviewed counts
and schema fingerprint, and no prior projection for that materialization. There is no latest-result
lookup and no schema upgrade.

The projection preserves materialization, review, selection, validation, completeness, conflict,
normalization, extraction, classification, category, schema-version, and fingerprint lineage.
Category mismatch is a technical failure because it signals inconsistent lineage.

## Product identity snapshot

The engine snapshots Product ID/version, name, manufacturer, model number, category, and
description exactly as stored. It does not infer missing values or copy persistence metadata.
Manufacturer, model number, and description are optional and produce warnings when absent. The
snapshot remains unchanged if Product is later updated.

## Reviewed attribute projection

Only final SPEC-030 attributes are projected. Each compact record retains canonical name/display
name, type, required flag, display order, value/unit, origin, review-decision ID, candidate/source
references, and validation status. Output is deterministically ordered by display order. OCR text,
PDF content, CSV rows, excerpts, raw review values, and other evidence payloads are not duplicated.

Human overrides produce `HUMAN_OVERRIDE_PRESENT`; candidate validation warnings produce
`VALIDATION_WARNING_PRESENT`; unresolved optional fields produce
`OPTIONAL_ATTRIBUTES_UNRESOLVED`. These warnings do not trigger revalidation or block readiness.

## Readiness model

Precedence is deterministic:

1. `BLOCKED` when any business blocker exists.
2. `READY_WITH_WARNINGS` when there are no blockers and at least one warning.
3. `READY` when neither blockers nor warnings exist.

`PRODUCT_NAME_MISSING` and coherent `PRODUCT_CATEGORY_UNCLASSIFIED` are business blockers. Missing
manufacturer/model/description, optional unresolved attributes, validation warnings, and human
overrides are warnings. Cross-product lineage, category mismatch, malformed reviewed counts, and
missing upstream artifacts are technical failures and do not create normal BLOCKED projections.

## Persistence and lifecycle

`catalog-projection-results` stores META and ordered ATTRIBUTE records under
`projectionId`/`recordKey`. META alone carries `jobId`, `materializationId`, and `createdAt`, making
`JobIdIndex` and `MaterializationIdIndex` sparse. A conditional
`MATERIALIZATION#{materializationId}` guard enforces one projection per materialization; writes do
not overwrite and reads never scan. Complete partition reconstruction detects partial writes.

Setup precedes PENDING to RUNNING. Persistence precedes COMPLETED and produces
`catalog-projection-results/{projectionId}`. Technical failures after start attempt FAILED. A
business BLOCKED projection completes successfully. If completion fails after persistence, the
artifact is retained and a `catalog_projection.completion_consistency_risk` event is logged.

## Scope boundary

SPEC-031 does not transition Product to READY_TO_PUBLISH, publish or export anything, call a
marketplace, create feeds, generate descriptions/SEO/marketing content, calculate product scores,
index search, expose an API or frontend, use AI, access S3, or add deployment behavior.
