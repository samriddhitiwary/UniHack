# SPEC-032 — Product Publishing Readiness Application and Catalog Read API

## Status
Completed

## Objective
Expose immutable SPEC-031 catalog projections through read-only APIs and explicitly apply an
eligible projection to the Product lifecycle with optimistic concurrency.

## User Story
As a catalog operator, I need to inspect one explicit reviewed projection, understand whether it
is current and eligible, and safely mark its Product internally ready for a future publisher.

## Scope
Backend services, schemas, Product repository transition, three versioned API operations,
controlled errors, tests, and documentation for catalog reads and readiness application.

## Out of Scope
External publishing, marketplaces, feeds, exports, publication events, enrichment, SEO, AI,
scoring, search, frontend, authentication, authorization, S3, and deployment.

## Functional Requirements
Load explicit Products and projections, isolate cross-product reads, preserve projection data and
reasons, calculate current eligibility without mutation, and conditionally transition only a
current eligible REVIEW_REQUIRED Product to READY_TO_PUBLISH.

## Non-Functional Requirements
No scans or implicit latest lookup, no upstream pipeline loading, immutable projections, stable
camelCase contracts, bounded safe errors, request-ID propagation, structured logging, and atomic
Product mutation.

## Existing Dependencies
Product identity/status/version semantics from SPEC-002 and SPEC-005, request-ID/error conventions,
the Product DynamoDB repository, and immutable SPEC-031 projection domain and repository contracts.

## Readiness Application Input
POST requires an explicit UUID `projectionId` and strict positive expected Product `version`. The
projection must exist, belong to the path Product, and carry that Product's current version.

## Product Status Transition Rules
Only REVIEW_REQUIRED to READY_TO_PUBLISH is allowed. DRAFT, PROCESSING, FAILED, and
READY_TO_PUBLISH are rejected; already-ready state returns PRODUCT_ALREADY_READY_TO_PUBLISH.
READY_TO_PUBLISH remains an internal state and does not mean that publication occurred.

## Projection Version Safety
The projection Product ID and Product-version snapshot must exactly match the current Product.
Product identity/category changes therefore invalidate earlier projections automatically.

## Optimistic Concurrency
The request version must match the current Product before mutation. DynamoDB then conditionally
checks both expected version and REVIEW_REQUIRED status while atomically setting status,
`updatedAt`, and version plus one. Conditional conflicts are not retried.

## Catalog Projection Read API
GET `/api/v1/products/{product_id}/catalog-projections/{projection_id}` returns the immutable
identity snapshot, compact reviewed attributes, status/reasons, counts, schema and upstream lineage,
and timestamp. Cross-product access returns the same 404 as a missing projection.

## Publishing Readiness Read API
GET `/api/v1/products/{product_id}/catalog-projections/{projection_id}/readiness` returns persisted
reasons plus current Product version/status, `projectionCurrent`, and read-only
`eligibleForReadyToPublish`. BLOCKED and stale projections return 200 with eligibility false.

## Error Handling
Stable controlled errors cover missing Product/projection, cross-product application, BLOCKED
application, stale request/projection versions, already-ready and forbidden status transitions,
Product storage, projection storage, request validation, and unexpected failures.

## Logging Requirements
Log safe event names, Product/projection IDs, statuses, versions, and bounded reason counts. Never
log attributes, descriptions, raw evidence, request bodies, repository payloads, or secrets.

## Security Considerations
Require explicit IDs, exact ownership, two independent version checks, an atomic status condition,
resource-isolated reads, compact projection output, and no outbound calls or arbitrary transition.

## Edge Cases
READY_WITH_WARNINGS remains eligible and retains warnings; BLOCKED is descriptive on GET but a
conflict on POST; stale GET remains successful and ineligible; conditional races are mapped without
retry; already-ready Products never advance version through this operation.

## Acceptance Criteria
All 128 supplied criteria must pass, including API contracts, state/version safety, reason and
lineage preservation, atomic repository behavior, request-ID errors, regression gates, and scope.

## Test Plan
Cover readiness state, service ordering and immutability, READY and READY_WITH_WARNINGS success,
BLOCKED/stale/cross-product/status failures, conditional repository behavior, schema serialization,
all three APIs, safe errors, OpenAPI, and complete backend/frontend quality gates.

## Implementation Notes
SPEC-032 trusts persisted SPEC-031 readiness results and evaluates only ownership, currency, and
current Product lifecycle state. It adds no job type, table, projection mutation, or audit record.

## Completion Record
Implemented explicit catalog/readiness reads and optimistic readiness application with a dedicated
Product conditional transition, stable errors, safe logging, comprehensive service/repository/API
tests, and architecture/API documentation. No job or table was added.

Verification completed on 2026-08-18: 1,438 backend tests passed, 13 optional DynamoDB Local tests
were skipped, total coverage was 90.63%, and Ruff lint/format, strict mypy, unchanged frontend
tests/lint/format/build, Docker Compose, whitespace, checklist, and scope gates passed.
