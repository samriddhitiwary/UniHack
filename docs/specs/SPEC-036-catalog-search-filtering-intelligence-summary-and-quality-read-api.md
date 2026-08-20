# SPEC-036 — Catalog Search, Filtering, Intelligence Summary, and Quality Read API

## Status
Completed

## Objective
Expose compact catalog search, per-Product quality summaries, and explicit Product Intelligence
Score detail/history through read-only APIs backed only by deliberate DynamoDB queries.

## User Story
As a catalog operator, I need pageable Product summaries and quality details so a dashboard can show
current and historical catalog intelligence without triggering or mutating the pipeline.

## Scope
Indexed Product-native search, bounded latest-artifact summary fan-out, explicit score reads, score
history, opaque scoped cursors, response schemas, read-only routes, tests, and documentation.

## Out of Scope
Workflow execution, writes, fuzzy/full-text/semantic/vector search, OpenSearch/Elasticsearch, Redis,
frontend, authentication, authorization, S3, downloads, external publishing, and deployment.

## Functional Requirements
Add the four specified GET routes; support only indexed Product-native search plans; return compact
search items, a richer single-Product summary, explicit score detail, and newest-first score history.

## Non-Functional Requirements
No scans, page limit at most 100, deterministic normalization, cursor plan/filter isolation, bounded
fan-out, safe logging/errors, camelCase output, request IDs, and at least 90% backend coverage.

## Existing Dependencies
Product storage and lifecycle, catalog projections/readiness, catalog exports, catalog enrichment,
Product Intelligence Score results/history, existing request context, and error envelopes.

## Search Access Patterns
CREATED_AT uses CreatedAtIndex; STATUS uses StatusCreatedAtIndex; CATEGORY uses
CategoryCreatedAtIndex; CATEGORY_STATUS uses CategoryStatusCreatedAtIndex; MANUFACTURER uses
ManufacturerCreatedAtIndex; MODEL_NUMBER uses ModelNumberCreatedAtIndex; NAME_PREFIX uses
NameSearchIndex with `begins_with`. Every access path is a DynamoDB query.

## Supported Filters
Supported: none, status, category, category+status, exact normalized manufacturer, exact normalized
modelNumber, and normalized namePrefix. Readiness, grade, score ranges, and all other combinations
are rejected with `CATALOG_SEARCH_FILTER_COMBINATION_UNSUPPORTED`.

## Product Search Semantics
Equality and prefix matching normalize with trim, lowercase, and collapsed whitespace while stored
display values remain unchanged. No substring, fuzzy, arbitrary query, or arbitrary sorting exists.

## Intelligence Summary
Each Product page item is enriched through bounded latest projection/score queries and boolean
enrichment/export existence checks. Missing artifacts are represented as null/false.

## Product Intelligence Read API
An explicit Product+score ID route returns all six components and metrics. Product score history is
newest first, compact, and cursor paginated using ProductCreatedAtIndex.

## Catalog Summary Read API
The single-Product summary returns identity, latest projection/readiness, latest intelligence,
staleness indicators, and enrichment/export availability without embedding generated content.

## Latest vs Explicit Artifact Semantics
Summary “latest” means first result by descending `createdAt` on a Product or Projection index.
Detailed score retrieval always uses the explicit score ID; no latest identifiers are written back.

## Pagination
Default 20, minimum 1, maximum 100. Search cursors bind version, access pattern, filter fingerprint,
and DynamoDB last key. Score-history cursors remain opaque and Product-scoped.

## DynamoDB Indexes
Products add CategoryCreatedAtIndex, CategoryStatusCreatedAtIndex, ManufacturerCreatedAtIndex,
ModelNumberCreatedAtIndex, and NameSearchIndex. Catalog projections add ProductCreatedAtIndex.
Existing status, score Product history, enrichment Projection, and export Projection indexes remain.

## Error Handling
Malformed/scope-mismatched search cursors return `INVALID_CURSOR`/400; unsupported filters return
422; missing Product/score returns 404 without cross-Product leakage; storage failures return safe
503 envelopes.

## Logging Requirements
Log safe plans, limits, result counts, Product IDs, and score IDs only; never content, attributes,
evidence, descriptions, secrets, or cursor payloads.

## Security Considerations
All routes are read-only and bounded. Ownership isolation, opaque cursors, fixed query planning, no
scans, no raw evidence, no arbitrary expressions, and no network calls are enforced.

## Edge Cases
Empty results, missing artifacts, stale projection/score, duplicate normalized keys, null sparse
search fields, malformed/wrong-scope cursor, unsupported combinations, and cross-Product score IDs.

## Acceptance Criteria
All 156 supplied acceptance criteria must pass within SPEC-036 scope.

## Test Plan
Cover every query plan/index, normalization, write-key maintenance, pagination/scope, no-scan
behavior, summaries, missing/stale artifacts, score detail/history, API envelopes, and regressions.

## Implementation Notes
Product summary fan-out is bounded by the validated maximum page size of 100. A future denormalized
dashboard projection or dedicated search service may replace fan-out limitations at larger scale.

## Completion Record
Completed on 2026-08-20. Implemented the four read-only routes, seven deliberate Product search
plans, plan/filter-scoped pagination, latest projection/score aggregation, persisted intelligence
history/detail reads, ownership isolation, staleness flags, local DynamoDB indexes, safe errors/logs,
tests, and documentation. Backend verification completed with 1,588 passing tests, 16 environment-
dependent skips, and 90.41% coverage; Ruff, formatting, strict mypy, unchanged frontend checks/build,
Docker Compose validation, and Git whitespace validation passed.
