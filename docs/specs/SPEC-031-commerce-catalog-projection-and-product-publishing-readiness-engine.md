# SPEC-031 — Commerce Catalog Projection and Product Publishing Readiness Engine

## Status
Completed

## Objective
Create an immutable commerce-oriented snapshot from one Product and one explicit SPEC-030 reviewed
attribute materialization, then determine internal downstream publishing readiness without
publishing anything.

## User Story
As a downstream catalog process, I need a stable Product identity and reviewed-attribute projection
with deterministic blockers and warnings so that later publishing work can make an explicit choice.

## Scope
Backend domain models, deterministic identity and reviewed-attribute projection, readiness
evaluation, immutable DynamoDB persistence, product-level processing-job orchestration, tests, and
documentation.

## Out of Scope
Product mutation, READY_TO_PUBLISH transitions, external publishing, exports, marketplace clients,
feeds, content or SEO generation, product scoring, search indexing, public APIs, frontend,
authentication, authorization, AI, S3, workers, and deployment.

## Functional Requirements
Load one explicit materialization and its Product, validate product/category/materialization
coherence, snapshot existing identity fields and Product version, project only reviewed attributes,
evaluate stable readiness reasons, persist the projection, and complete the job.

## Non-Functional Requirements
Deterministic output, immutable snapshots, exact lineage, stable ordering, conditional idempotency,
bounded text/attributes/reasons/items, safe logging, no scans, and no external effects.

## Existing Dependencies
SPEC-002 Product identity/status, SPEC-022 category/schema metadata, SPEC-026 completeness semantics,
SPEC-029 review lineage, SPEC-030 final reviewed attributes, and existing processing-job conventions.

## Projection Input
One product-level CATALOG_PROJECTION job containing an explicit reviewed attribute materialization
ID. No latest-result lookup is permitted.

## Product Identity Projection
Snapshot Product ID, version, name, manufacturer, model number, category, and description exactly as
stored. Never infer or generate identity fields.

## Reviewed Attribute Projection
Transform only SPEC-030 final reviewed attributes, retaining canonical value/unit, schema order,
origin, decision ID, candidate/source references, and validation status. Do not copy raw evidence.

## Category and Schema Lineage
Preserve review, selection, validation, completeness, conflict, normalization, extraction,
classification, category, schema version, and schema fingerprint. Product and materialization
categories must match.

## Commerce Field Model
CommerceCatalogAttribute is an immutable bounded record containing schema identity/order,
canonical value/unit, origin, and compact review/candidate/source validation lineage.

## Publishing Readiness Rules
BLOCKED takes precedence over READY_WITH_WARNINGS, which takes precedence over READY. Business
identity blockers produce a successful projection; corrupt or incoherent upstream lineage fails the
job.

## Blocking Reasons
Stable domain codes include PRODUCT_NAME_MISSING, PRODUCT_CATEGORY_UNCLASSIFIED,
PRODUCT_CATEGORY_MISMATCH, REVIEWED_ATTRIBUTES_MISSING, REVIEWED_ATTRIBUTE_LINEAGE_INVALID,
REQUIRED_ATTRIBUTE_MISSING, and REQUIRED_ATTRIBUTE_INVALID. Category mismatch and malformed
reviewed artifacts are handled as technical failures rather than normal BLOCKED projections.

## Warning Reasons
Stable warnings cover missing manufacturer, model number, or description; unresolved optional
attributes; preserved validation warnings; and human overrides. Warnings never become blockers.

## Projection Status
READY has no reasons, READY_WITH_WARNINGS has warnings but no blockers, and BLOCKED has at least one
business blocker.

## Catalog Projection Model
Immutable Product snapshot, full upstream identifiers/schema lineage, readiness status and reasons,
coherent counts, ordered commerce attributes, engine/version, and UTC timestamp.

## DynamoDB Persistence
catalog-projection-results stores META and ordered ATTRIBUTE records under projectionId/recordKey,
with sparse JobIdIndex and MaterializationIdIndex plus a conditional materialization uniqueness
guard. Retrieval uses queries only and rejects incomplete partitions.

## Processing Job Lifecycle
All setup validation occurs before PENDING to RUNNING. The result persists before RUNNING to
COMPLETED and sets catalog-projection-results/{projectionId}. Technical failures after start attempt
FAILED; a BLOCKED projection still completes successfully.

## Idempotency
Exactly one projection may be created per exact SPEC-030 materialization. Neither the projection nor
its Product snapshot is overwritten.

## Safety Limits
At most 100 attributes, 10,000 characters per value, 50 reason codes, 50,000 total Product identity
characters, and 390,000 serialized bytes per DynamoDB item, with stricter Product domain limits
remaining authoritative.

## Error Handling
Controlled failures cover invalid jobs, missing/cross-product materialization, category or lineage
mismatch, malformed required counts, duplicate projection, limits, engine, repository, storage, and
completion consistency risks.

## Logging Requirements
Log safe IDs, Product version, category, projection status, and counts. Do not log attribute values,
descriptions, evidence, or other unnecessary content.

## Security Considerations
Explicit immutable lineage, bounded inputs, no dynamic execution, no internet, no AI, no raw
evidence duplication, conditional writes, and no Product mutation.

## Edge Cases
Optional identity omissions, multiple deterministic warnings, human overrides, validation warnings,
unresolved optional fields, UNCLASSIFIED readiness evaluation, category mismatch, shuffled input,
partial persistence, duplicate materialization, and job completion failure.

## Acceptance Criteria
All 143 supplied acceptance criteria must pass without introducing any out-of-scope behavior.

## Test Plan
Cover ready motor/pump projections, identity blockers/warnings, reviewed warnings/origins, ordering,
lineage/integrity, immutability, serialization, idempotency, repository access patterns, partial
persistence, lifecycle, consistency risk, and unchanged repository-wide behavior.

## Implementation Notes
Readiness is an internal deterministic assessment only. SPEC-031 does not revalidate, rereview,
enrich, publish, or transition Product status.

## Completion Record
Implemented the product-level CATALOG_PROJECTION job, immutable Product identity/version snapshot,
compact SPEC-030 reviewed-attribute projection, deterministic READY/READY_WITH_WARNINGS/BLOCKED
evaluation, conditional DynamoDB persistence, idempotency, controlled lifecycle failures, tests,
and architecture documentation.

Repository-wide backend, frontend, lint, formatting, strict typing, build, Compose, and whitespace
verification completed successfully on 2026-08-18. Product status mutation, external publishing,
exports, enrichment, APIs, frontend, AI, S3, and deployment remain out of scope.
