# SPEC-037 — End-to-End Catalog Intelligence Workflow Orchestration API

## Status
Completed

## Objective
Coordinate the existing CatalogIQ processing services as one synchronous, resumable, Product-scoped workflow.

## User Story
As a catalog operator, I can start one workflow, complete the authoritative human review when asked,
resume it, and inspect durable progress without manually constructing every processing job.

## Scope
One fixed CATALOG_INTELLIGENCE pipeline, source-aware child-job planning, durable state/stages,
mandatory review pause, resume, optional outputs, progress, history, concurrency, APIs, and tests.

## Out of Scope
Frontend, generic DAGs, automatic review decisions, failed-stage retry, background workers, queues,
WebSockets, authentication, S3, deployment, publishing, and new extraction/AI algorithms.

## Existing Dependencies
SPEC-001 through SPEC-036 Product/source repositories, processing jobs, all stage services, review,
materialization, projection/readiness, export, enrichment, scoring, request IDs, and safe errors.

## Workflow Model
Immutable current-state `CatalogIntelligenceWorkflow` with fixed configuration, source snapshot,
ordered stages, typed result references, timestamps, safe failure metadata, and optimistic version.

## Workflow States
PENDING, RUNNING, WAITING_FOR_REVIEW, FAILED, COMPLETED, COMPLETED_WITH_WARNINGS.

## Workflow Stages
SOURCE_PROCESSING, PRODUCT_CLASSIFICATION, ATTRIBUTE_EXTRACTION, ATTRIBUTE_NORMALIZATION,
CONFLICT_DETECTION, COMPLETENESS, ATTRIBUTE_VALIDATION, ATTRIBUTE_SELECTION, HUMAN_REVIEW,
REVIEWED_ATTRIBUTE_MATERIALIZATION, CATALOG_PROJECTION, PUBLISHING_READINESS, CATALOG_EXPORT,
AI_ENRICHMENT, PRODUCT_INTELLIGENCE_SCORE.

## Stage Dependencies
The order is fixed. Every downstream job receives exact identifiers persisted by its predecessor;
no arbitrary latest artifact is selected.

## Source Processing Strategy
TEXT needs no child job. PDF uses text and table extraction; CSV uses CSV processing; IMAGE uses
analysis then OCR. Multiple bounded sources are supported and completed compatible source jobs are reused.

## Automatic Stages
All non-review stages execute synchronously through existing services until review, failure, or completion.

## Human Review Checkpoint
Every workflow creates or reuses the review for its exact selection. OPEN review pauses; COMPLETED
review continues. There is no bypass or automatic decision path.

## Resume Semantics
Only WAITING_FOR_REVIEW resumes, using the supplied workflow version and exact stored review ID.
Completed stages and the immutable source snapshot are retained.

## Optional Stages
Export, AI enrichment, and intelligence scoring are configurable. Scoring can run without enrichment.

## Failure Semantics
Core errors fail the workflow. Non-strict optional errors are recorded and produce
COMPLETED_WITH_WARNINGS; strict optional errors fail. BLOCKED projections are business warnings.

## Retry Semantics
FAILED is terminal in v1. A caller starts a new workflow; resume exists only for review.

## Idempotency
One active workflow per Product is enforced transactionally. Persisted completed stages never rerun.
Existing source-result and export/enrichment/score uniqueness/reuse rules are preserved.

## Workflow Persistence
The workflow table uses workflowId/recordKey with META and fixed STAGE records. Sparse
ProductCreatedAtIndex supports history. A separate ACTIVE_PRODUCT guard prevents concurrent starts.

## API Design
Product-scoped start, get, newest-first list, and resume routes; no mutation or arbitrary-stage API.

## Progress Reporting
Integer terminal-stage count over all fixed stages; COMPLETED/SKIPPED count, WAITING does not.

## Result References
Only IDs/logical references and child job IDs are stored; upstream result payloads are not duplicated.

## Concurrency
Every state save conditions on version and increments once. Terminal saves release the active guard.

## Safety Limits
At most 50 sources, 20 stages, 200 child jobs, 100 history items, and 390,000 bytes per record.

## Logging
Safe workflow/Product/stage/job identifiers, status, version, and progress only.

## Security Considerations
Product ownership isolation, fixed configuration/stage order, bounded queries, no scans, no raw
source/catalog/provider content, no dynamic URLs, and no direct workflow filesystem access.

## Edge Cases
No sources, unresolved classification, open/already-completed review, stale workflow/Product,
cross-Product access, BLOCKED projection, disabled/failed optional stages, and sources added while paused.

## Acceptance Criteria
All 217 supplied acceptance criteria must pass within SPEC-037 scope.

## Test Plan
Domain/state/planner/repository/API tests plus source-type, mixed-source, exact lineage, review
pause/resume, concurrency, idempotency, optional-stage, readiness, failure, and full regression gates.

## Implementation Notes
Execution is synchronous in v1. Long OCR/LLM requests are accepted for the demo architecture. A future
production design may move coordination to Step Functions/SQS, but neither is implemented here.

## Completion Record
Completed on 2026-08-20. Implemented the fixed synchronous workflow, source-aware existing-service
adapters, mandatory review pause/resume, optional-stage policy, deterministic progress, compact
DynamoDB persistence, active-Product concurrency guard, optimistic transitions, four API routes,
safe errors/logging, and documentation. Verification: 1,612 backend tests passed, 16 environment-
gated tests skipped, coverage 90.01%, Ruff lint/format passed, strict mypy passed, frontend Vitest,
ESLint, Prettier, and Vite build passed, Docker Compose configuration passed, and Git whitespace
passed. All 217 acceptance criteria were reviewed and pass within the documented synchronous-v1 and
source-snapshot limitations.
