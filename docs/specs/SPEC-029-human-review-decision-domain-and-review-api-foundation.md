# SPEC-029 — Human Review Decision Domain and Review API Foundation

## Status
Completed

## Objective
Capture explicit human attribute-review decisions without materializing Product attributes.

## User Story
As a catalog reviewer, I can resolve prepared attribute choices with a durable audit trail.

## Scope
Backend review sessions, decisions, manual overrides, persistence, concurrency, APIs, tests, and documentation.

## Out of Scope
Product materialization or publication, review reopening/deletion, authentication, authorization, frontend, AI, S3, and deployment.

## Functional Requirements
Create one review for an explicit selection, append decisions, retrieve history, and complete only when required attributes resolve.

## Non-Functional Requirements
Deterministic validation, immutable history, atomic optimistic concurrency, bounded input, safe errors/logging, and no scans.

## Existing Dependencies
SPEC-024 normalization, SPEC-025 conflicts, SPEC-026 completeness, SPEC-027 validation, SPEC-028 selection, Product storage, and API error conventions.

## Review Input
An explicit SPEC-028 selection with coherent Product and full upstream lineage.

## Review Session Model
An OPEN or COMPLETED versioned aggregate with lineage, decision counts, readiness counts, and timestamps.

## Attribute Review Decision Model
An immutable decision records attribute, approved/manual values, reviewer, comment, resulting review version, sequence, and timestamp.

## Decision Types
APPROVE_CANDIDATE, APPROVE_PROPOSED, REJECT_ALL, and MANUAL_OVERRIDE.

## Candidate Approval
Candidates must belong to the attribute and exact pipeline; VALID and VALID_WITH_WARNINGS are approvable.

## Candidate Rejection
REJECT_ALL supersedes current state but leaves required attributes unresolved.

## Manual Override
Preserve bounded raw input and persist deterministic canonical value/unit only after exact schema validation.

## Review Completion
All required attributes need an effective resolving decision; optional unresolved attributes do not block completion.

## Audit History
DECISION records are append-only and monotonic; CURRENT projections point to the latest decision without deleting history.

## Optimistic Concurrency
Every decision/completion requires an exact positive version and atomically increments it; stale writes fail with 409.

## API Contracts
Create/get review, list decisions, submit an attribute decision, and complete review under `/api/v1/products/{productId}/reviews`.

## DynamoDB Persistence
`product-reviews` uses `reviewId`/`recordKey`, META, DECISION, CURRENT, and conditional selection-uniqueness records.

## Error Handling
Stable safe 404, 409, 422, and 503 review errors use the existing request-ID envelope.

## Logging Requirements
Log safe IDs, type, version, and sequence only; omit manual values, comments, and evidence.

## Security Considerations
Caller-supplied reviewer identity is bounded; candidate/schema lineage is exact; inputs are inert and bounded.

## Edge Cases
Revisions, warning candidates, reject-all, missing/optional attributes, invalid overrides, stale writes, and completed immutability.

## Acceptance Criteria
All 152 supplied criteria must pass.

## Test Plan
Cover domain invariants, normalization/validation, repository transactions, service lineage, API contracts, history, concurrency, and completion.

## Implementation Notes
Decision sequence equals the new decision count; decision review version equals the atomically advanced aggregate version.

## Completion Record
Completed on 2026-08-18. Review sessions, four attribute decision types, deterministic manual
override normalization/validation, immutable audit history, current projections, strict selection
uniqueness, transactional optimistic concurrency, terminal completion, five API operations, stable
errors, tests, and documentation are implemented. Verification passed with 1,331 backend tests
(11 skipped), 90.36% backend coverage, Ruff lint/format, strict mypy, unchanged frontend
test/lint/format/build, Docker Compose validation, and Git whitespace checks. All 152 supplied
acceptance criteria were reviewed and satisfied.
