# Product Review API

SPEC-029 exposes five backend review operations:

```text
POST /api/v1/products/{productId}/reviews
GET  /api/v1/products/{productId}/reviews/{reviewId}
GET  /api/v1/products/{productId}/reviews/{reviewId}/decisions?limit=50&cursor=...
POST /api/v1/products/{productId}/reviews/{reviewId}/attributes/{attributeName}/decisions
POST /api/v1/products/{productId}/reviews/{reviewId}/complete
```

All external fields use camelCase. Errors use the existing envelope and `X-Request-ID` response
header. Reviewer identity is a bounded caller-supplied field because authentication is out of scope.

## Create and retrieve

Create requires an explicit selection—there is no latest-result lookup:

```json
{"selectionId":"00000000-0000-0000-0000-000000000000"}
```

A successful create returns HTTP 201 with OPEN status, version 1, zero decisions, full immutable
lineage, resolution counts, and `completionReady`. Only one review may exist per selection. Get
returns the same bounded aggregate metadata without embedding decision history.

## Submit a decision

Every decision requires positive `version`, safe nonempty `reviewerId`, and one decision type.

```json
{
  "version": 2,
  "decisionType": "APPROVE_CANDIDATE",
  "candidateId": "normalized-candidate-000002",
  "reviewerId": "reviewer-local-001",
  "comment": "Confirmed against nameplate"
}
```

APPROVE_PROPOSED and REJECT_ALL accept no candidate/manual fields. MANUAL_OVERRIDE requires
`manualValue`, permits a schema-compatible `manualUnit`, and preserves both raw fields after
deterministic normalization and validation. Success returns HTTP 201 with the immutable decision
and resulting review version.

Decision history is chronological. `limit` defaults to 50 and is capped at 100; `cursor` is opaque
and bound to the review identity. Storage uses partition queries only.

## Complete

```json
{"version":7,"reviewerId":"reviewer-local-001"}
```

Completion succeeds with HTTP 200 only after all required attributes have effective resolving
decisions. Optional unresolved attributes do not block it. REJECT_ALL remains unresolved for a
required attribute. Completed reviews are immutable and cannot be reopened.

Stable review errors include ATTRIBUTE_SELECTION_NOT_FOUND, REVIEW_NOT_FOUND,
ATTRIBUTE_NOT_IN_SELECTION, REVIEW_CANDIDATE_NOT_FOUND, REVIEW_ALREADY_EXISTS_FOR_SELECTION,
REVIEW_VERSION_CONFLICT, REVIEW_ALREADY_COMPLETED, REVIEW_REQUIRED_ATTRIBUTES_UNRESOLVED,
REVIEW_SELECTION_LINEAGE_INVALID, REVIEW_DECISION_NOT_ALLOWED, REVIEW_CANDIDATE_NOT_APPROVABLE,
REVIEW_MANUAL_OVERRIDE_INVALID, and REVIEW_STORAGE_UNAVAILABLE.
