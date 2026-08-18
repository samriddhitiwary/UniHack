# Product Review Architecture

SPEC-029 turns an explicit SPEC-028 review-preparation result into an independently persisted
human-review aggregate. A system proposal is never treated as human approval, and approved values
remain inside the review domain rather than Product records.

## Aggregate and lineage

Each `ProductReviewSession` references one exact selection and preserves its conflict, validation,
completeness, normalization, extraction, classification, category, schema version, and schema
fingerprint lineage. Creation verifies the Product and every referenced immutable result. A
transactional `SELECTION#{selectionId}` guard enforces one review per selection without a scan.

Sessions begin `OPEN` at version 1 with no decisions. `COMPLETED` is terminal in v1. Every decision
or completion request supplies the exact current version, and its atomic write advances the version.

## Decisions and current state

`APPROVE_CANDIDATE` accepts an exact attribute candidate whose SPEC-027 status is `VALID` or
`VALID_WITH_WARNINGS`. `APPROVE_PROPOSED` accepts only the primary proposal of an `AUTO_SELECTED`
attribute. `REJECT_ALL` rejects known candidates but does not resolve a required attribute.
`MANUAL_OVERRIDE` preserves caller input and stores a separately normalized, schema-validated
canonical value and unit.

Every accepted decision is an immutable `DECISION#000001` record. Revisions append another record.
A transaction replaces only `CURRENT#{attributeName}`, which references the newest immutable
decision. The same transaction conditionally checks OPEN status/version and advances META version,
sequence/count, resolution counts, and update time. History is chronological, paginated, and never
replayed destructively.

## Completion and safety

Completion requires an effective APPROVE_CANDIDATE, APPROVE_PROPOSED, or MANUAL_OVERRIDE decision
for every required schema attribute. Optional attributes may have no decision or REJECT_ALL.
Completion atomically sets the terminal status/timestamp and increments the version; later writes
return a stable conflict.

Reviewer identity is caller-supplied until authentication exists. IDs, comments, values, attributes,
decision counts, records, and cursors are bounded. Logs omit comments, values, and source evidence.
There is no Product mutation, publishing transition, authentication, frontend, AI, S3, or deployment
behavior in this feature.
