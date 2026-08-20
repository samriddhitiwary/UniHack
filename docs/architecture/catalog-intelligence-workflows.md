# Catalog Intelligence workflows

SPEC-037 provides one fixed, synchronous `CATALOG_INTELLIGENCE` workflow. It coordinates the
existing source processors, classification and attribute engines, mandatory Product review,
materialization, catalog projection/readiness, export, grounded enrichment, and Product Intelligence
Score. It does not duplicate those algorithms and is not a generic DAG engine.

## Fixed stage map

```text
SOURCE_PROCESSING -> PRODUCT_CLASSIFICATION -> ATTRIBUTE_EXTRACTION
-> ATTRIBUTE_NORMALIZATION -> CONFLICT_DETECTION -> COMPLETENESS
-> ATTRIBUTE_VALIDATION -> ATTRIBUTE_SELECTION -> HUMAN_REVIEW [mandatory pause while OPEN]
-> REVIEWED_ATTRIBUTE_MATERIALIZATION -> CATALOG_PROJECTION -> PUBLISHING_READINESS
-> CATALOG_EXPORT [optional] -> AI_ENRICHMENT [optional]
-> PRODUCT_INTELLIGENCE_SCORE [optional]
```

TEXT sources need no child job. PDF uses embedded-text and table extraction. CSV uses CSV
processing. IMAGE uses image analysis followed by OCR. Mixed source sets are bounded to 50 sources
and 200 child jobs. A completed source job is reused only when Product, source, job type, completion
state, and its stored result all match.

## State and review

Workflow states are `PENDING`, `RUNNING`, `WAITING_FOR_REVIEW`, `FAILED`, `COMPLETED`, and
`COMPLETED_WITH_WARNINGS`. Stage states are `NOT_STARTED`, `RUNNING`, `COMPLETED`, `SKIPPED`,
`WAITING`, and `FAILED`. Each persisted transition increments the optimistic workflow version once.

Every workflow creates or reuses the review session for the exact selection. An OPEN session sets
the Product to `REVIEW_REQUIRED`, records its resulting version, and pauses. Review decisions remain
owned by the SPEC-029 API. Resume requires the current workflow version, unchanged observed Product
and source identity, and the exact stored review in `COMPLETED`; there is no auto-approval or bypass.
Completed stages are never rerun. FAILED workflows are terminal in v1.

Sources have individual versions but no aggregate source-set version. The workflow therefore stores
the observed source identities/types and rejects additions/removals at resume, while execution uses
the source state observed as each stage runs. It does not introduce a source-set version subsystem.

## Readiness and optional stages

READY and READY_WITH_WARNINGS projections may use the existing readiness application when enabled.
BLOCKED skips readiness, export, and enrichment; scoring can still run. READY_WITH_WARNINGS and
BLOCKED lead to `COMPLETED_WITH_WARNINGS`. Export, enrichment, and score failures continue when
`failOnOptionalStageError=false`; scoring receives no enrichment ID when enrichment is absent or
failed. Strict optional errors fail the workflow.

## Persistence and concurrency

`catalog-intelligence-workflows` uses `workflowId`/`recordKey`. `META` stores configuration, compact
lineage references, source snapshot, state, Product/workflow versions, progress, and timestamps.
Fifteen `STAGE#...` records store stage/job references and safe error metadata. Sparse
`ProductCreatedAtIndex` provides newest-first history without scans. A transactional
`ACTIVE_PRODUCT#{productId}` guard permits only one non-terminal workflow per Product and is removed
on terminal transition. Records are guarded at 390,000 bytes and never duplicate raw stage results.

Progress is the integer percentage of fixed stages in COMPLETED or SKIPPED. WAITING and FAILED do
not count; a successfully terminal workflow is forced to 100%. Logs contain identifiers, states,
versions, counts, and safe codes only.

## Runtime limitation

Orchestration runs synchronously in v1, so OCR or LLM workflows can make the API request long. A
future production deployment may move coordination to Step Functions/SQS, but neither is part of
SPEC-037. Only review-waiting workflows have explicit resume semantics.
