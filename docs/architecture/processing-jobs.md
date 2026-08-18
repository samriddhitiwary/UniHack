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
