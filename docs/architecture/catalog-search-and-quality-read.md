# Catalog Search and Quality Read Architecture

SPEC-036 adds read-only catalog discovery and quality views over artifacts already persisted by
SPEC-031 through SPEC-035. Reads never create jobs, recompute projections or scores, invoke AI, or
mutate Product state.

## Indexed Product search

`GET /api/v1/catalog/products` selects exactly one documented access plan. Supported plans are
unfiltered newest-first, status, category, category plus status, normalized manufacturer equality,
normalized model-number equality, and normalized name prefix. Any quality filter or unindexed
combination returns `422 CATALOG_SEARCH_FILTER_COMBINATION_UNSUPPORTED`; there is no fallback scan.

Manufacturer, model number, and name values are trimmed, lowercased, and whitespace-collapsed when
Product records are created or updated. Derived index fields are maintained in the same write as
their source values. Name matching is prefix-only through `begins_with`, not substring or fuzzy.

Each item uses bounded latest-artifact queries: at most one projection, one score, one enrichment
existence check, and one export lookup. Page size is 1-100, default 20. Cursor envelopes are scoped
to the access pattern and a SHA-256 filter fingerprint, preventing reuse with another filter.

## Summary and staleness

`GET /api/v1/products/{product_id}/catalog-summary` returns Product identity plus latest projection
and score summaries. A projection is current only when its `productVersion` equals the current
Product version. A score is current only when it refers to that latest projection and the projection
is current. Missing artifacts are represented as `null`/`false`, not errors.

Enrichment and export availability are checked only for the latest projection. Readiness is the
persisted deterministic status: `READY`, `READY_WITH_WARNINGS`, or `BLOCKED`.

## Intelligence reads

Score history queries `ProductCreatedAtIndex` newest first with a product-bound opaque cursor. Score
detail verifies explicit Product ownership; cross-product lookups return the same 404 as absence.
Detail returns persisted components and metrics, while list/search payloads remain compact. No score
is recalculated.

Storage failures use safe 503 envelopes. Logs contain identifiers, access plans, and counts but no
prompts, generated content, evidence payloads, credentials, or raw DynamoDB records.
