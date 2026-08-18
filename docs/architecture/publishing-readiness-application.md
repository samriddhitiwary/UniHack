# Publishing Readiness Application

SPEC-032 exposes immutable SPEC-031 catalog projections and applies one explicit eligible
projection to the Product lifecycle. `READY_TO_PUBLISH` is an internal state only; this component
does not publish, export, enrich, or contact another system.

## Components

```text
Catalog routes
    -> PublishingReadinessApplicationService
         |-> ProductRepository
         |-> CommerceCatalogProjectionRepository
         `-> pure publishing-readiness state evaluator
```

The service is independent of FastAPI and Boto3. Reads use the existing explicit projection-ID
query. There is no latest projection lookup, scan, new job, new table, or upstream review/evidence
load.

## Read behavior

The catalog endpoint returns the immutable Product identity snapshot, schema and upstream lineage,
ordered reviewed attributes, counts, persisted status/reasons, and creation time. Compact candidate,
source, review-decision, and validation references remain available; raw OCR/PDF/CSV/extraction
evidence does not.

Both GET operations first require the Product. A projection whose `productId` differs from the path
returns `CATALOG_PROJECTION_NOT_FOUND`, matching an absent projection and preventing ownership
disclosure. The readiness GET additionally compares the projection Product version with the current
Product version. Stale and BLOCKED projections remain valid descriptive resources and return 200
with `eligibleForReadyToPublish=false`.

## Application behavior

The POST command requires `projectionId` and the caller's expected Product `version`. Validation is
performed without mutation in this order: Product and projection existence, ownership, persisted
projection status, caller version, projection snapshot version, and Product source status.

`READY` and `READY_WITH_WARNINGS` are eligible; warning codes remain unchanged in the response.
`BLOCKED` returns `PUBLISHING_READINESS_BLOCKED` with bounded blocker codes. SPEC-032 does not
re-evaluate any SPEC-031 readiness rule.

Only `REVIEW_REQUIRED -> READY_TO_PUBLISH` is supported. DRAFT, PROCESSING, and FAILED return
`PUBLISHING_READINESS_STATUS_TRANSITION_NOT_ALLOWED`. READY_TO_PUBLISH returns
`PRODUCT_ALREADY_READY_TO_PUBLISH`; without Product-side projection lineage, same-application
idempotency cannot be proven and the version is not advanced.

## Concurrency and mutation boundary

The repository uses one DynamoDB update with a condition requiring record existence, the expected
version, and REVIEW_REQUIRED status. Success changes only status, `updatedAt`, and version plus one,
then returns the stored Product. A failed condition is classified by a consistent follow-up read as
missing, stale version, or changed status. It is never retried automatically.

Product identity/category/source count/creation time remain unchanged. The projection, reviewed
materialization, and review remain immutable and receive no applied flag.

## Safe errors and logging

Product and projection repositories map to separate 503 codes. Controlled readiness failures use
the standard request-ID envelope. Logs contain only IDs, statuses, versions, eligibility, and reason
counts; attribute values, descriptions, evidence, bodies, and persistence payloads are excluded.

## Scope boundary

There is no external publishing, marketplace client, feed, export, event table, AI, enrichment,
SEO, scoring, search indexing, frontend, authentication, authorization, S3, or deployment work.
