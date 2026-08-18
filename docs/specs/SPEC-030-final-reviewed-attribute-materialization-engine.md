# SPEC-030 — Final Reviewed Attribute Materialization Engine

## Status
Completed

## Objective
Create one authoritative immutable reviewed-attribute artifact from a completed human review.

## User Story
As a downstream catalog process, I need the current approved values with exact review and evidence lineage.

## Scope
Backend domain, deterministic resolution, persistence, product-level job lifecycle, tests, and documentation.

## Out of Scope
Product-table attributes, publishing/readiness, APIs, exports, enrichment, frontend, auth, AI, S3, and deployment.

## Functional Requirements
Load an explicit completed review, resolve current decisions only, enforce required attributes, and persist before job completion.

## Non-Functional Requirements
Immutable output, strict lineage/idempotency, canonical strings, bounded records, safe logs, and no scans.

## Existing Dependencies
SPEC-022 schema, SPEC-024 normalization, SPEC-027 validation, SPEC-028 selection, SPEC-029 review, and processing jobs.

## Materialization Input
One explicit review ID on a REVIEWED_ATTRIBUTE_MATERIALIZATION product-level job.

## Review Completion Requirement
Only a coherent COMPLETED review may materialize; OPEN reviews fail before RUNNING.

## Effective Decision Resolution
CURRENT projections must reference the matching latest immutable decision; historical decisions are ignored as values.

## Approved Candidate Materialization
Use persisted approved value/unit and verify exact normalized candidate and validation lineage without reranking.

## Manual Override Materialization
Use persisted canonical and raw fields unchanged with HUMAN_OVERRIDE origin and no candidate lineage.

## Required Attribute Enforcement
Every required schema attribute must have a materializable current decision.

## Optional Attribute Handling
Unresolved optional attributes are absent and counted; no null placeholder is created.

## Final Attribute Model
Ordered immutable canonical value, origin, review decision, reviewer, candidate/source or manual lineage, and timestamp.

## Final Reviewed Product Model
Immutable MATERIALIZED aggregate with exact upstream lineage and coherent required/optional counts.

## Lineage and Auditability
Review, selection, validation, normalization, schema, candidate, decision, reviewer, and source identifiers are preserved.

## DynamoDB Persistence
`reviewed-attribute-results` stores META and ATTRIBUTE records plus transactional REVIEW uniqueness guard and sparse indexes.

## Processing Job Lifecycle
Prerequisites precede RUNNING; persistence precedes COMPLETED; technical failures attempt FAILED.

## Idempotency
One materialization per exact review is enforced transactionally; records are never overwritten.

## Safety Limits
100 attributes and 10,000-character canonical/manual values with a 390,000-byte item guard.

## Error Handling
Controlled failures cover job/review/schema/lineage/state/required/idempotency/limit/engine/storage conditions.

## Logging Requirements
Log safe IDs, category, origin, counts, and status; omit values, comments, and evidence content.

## Security Considerations
Exact completed state and lineage, fixed schema, bounded input, immutable persistence, no internet or dynamic rules.

## Edge Cases
Revisions, historical decisions, REJECT_ALL, optional absence, warning candidates, null units, and corrupt projections.

## Acceptance Criteria
All 142 supplied criteria must pass.

## Test Plan
Cover resolver integrity, origins/lineage, counts/order, persistence, idempotency, lifecycle, and controlled failures.

## Implementation Notes
The completed review is authoritative; SPEC-030 performs structural verification only, never selection or revalidation.

## Completion Record
Implemented as a product-level internal job with explicit completed-review lineage, deterministic
CURRENT-decision resolution, immutable candidate/manual-origin output, required-field enforcement,
conditional DynamoDB persistence, idempotency, lifecycle handling, tests, and documentation.

Repository-wide backend, frontend, formatting, static-analysis, build, Compose, and whitespace
verification completed successfully on 2026-08-18. Product mutation, publishing/readiness, API,
frontend, AI, S3, and deployment behavior remain out of scope.
