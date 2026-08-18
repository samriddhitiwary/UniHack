# Processing Job Architecture

Processing jobs provide optimistic, immutable-state lifecycle records for source-scoped and
product-level internal work. A job transitions `PENDING -> RUNNING -> COMPLETED` or
`PENDING -> RUNNING -> FAILED`; terminal jobs cannot restart. Result data is persisted before a
COMPLETED transition and linked through a safe logical `resultReference`.

## Reviewed attribute materialization

SPEC-030 adds product-level `REVIEWED_ATTRIBUTE_MATERIALIZATION`. It requires an explicit
`reviewId`, requires `sourceId` to be null, and is intentionally rejected by the public
source-oriented job creation route. The direct orchestration service performs every Product,
review, completed-state, schema, lineage, and idempotency setup check before RUNNING.

Successful jobs reference `reviewed-attribute-results/{materializationId}`. A technical failure
after RUNNING records a stable safe error code/message and transitions to FAILED where possible.
If the final job update fails after result persistence, the immutable artifact remains available
and a completion-consistency-risk event is logged.

No execution endpoint, worker, retry operation, or scheduling behavior is introduced by SPEC-030.

## Catalog projection

SPEC-031 adds product-level `CATALOG_PROJECTION`. It requires an explicit
`reviewedAttributeMaterializationId`, requires `sourceId` to be null, and is rejected by the public
source-oriented creation route. Product, materialization, ownership/category, reviewed integrity,
and idempotency checks all occur before RUNNING.

Successful READY, READY_WITH_WARNINGS, and business BLOCKED results all complete the job with
`catalog-projection-results/{projectionId}`. Technical failures after RUNNING attempt FAILED. The
projection is retained and a consistency-risk event is logged if the terminal job update fails.
SPEC-031 adds no executor endpoint, scheduling, retry, publishing, or Product-status transition.

## Catalog export

SPEC-033 adds product-level `CATALOG_EXPORT`. It requires `sourceId` to be null and an explicit
`projectionId`, and the public source-oriented job creation route rejects it. Product, projection,
ownership/category, eligibility, structural integrity, and one-export-per-projection checks occur
before RUNNING. READY and READY_WITH_WARNINGS projections can produce packages; BLOCKED is rejected.

Objects are saved before immutable result metadata, and successful jobs reference
`catalog-export-results/{exportId}`. Failures after RUNNING attempt FAILED and compensate partial
objects. A completion failure retains a valid package/result and logs a consistency risk. No
execution endpoint, retry, scheduling, external publication, or Product mutation is introduced.
