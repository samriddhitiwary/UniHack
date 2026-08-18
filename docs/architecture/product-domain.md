# Product Domain and Lifecycle

The Product is an immutable application entity persisted as one versioned DynamoDB record. Identity
fields are `productId`, name, manufacturer, model number, category, and description; operational
fields include status, source count, timestamps, and positive version.

Generic SPEC-005 PATCH updates use optimistic version comparison and preserve unspecified fields.
SPEC-032 adds a narrower lifecycle operation for reviewed catalog readiness:

```text
REVIEW_REQUIRED --apply current READY or READY_WITH_WARNINGS projection--> READY_TO_PUBLISH
```

The dedicated repository update condition requires both the caller's current version and the
REVIEW_REQUIRED source status. It atomically sets READY_TO_PUBLISH, advances version exactly once,
and refreshes `updatedAt`; no identity field changes. DRAFT, PROCESSING, FAILED, and already
READY_TO_PUBLISH Products are rejected by the readiness service.

READY_TO_PUBLISH means internally reviewed and eligible for a future publication workflow. It does
not record or imply external publication. Product changes advance version, so projections created
from an older Product identity become stale and must be regenerated before readiness can be applied.
