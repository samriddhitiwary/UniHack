# Catalog Projection and Publishing Readiness API

SPEC-032 adds three JSON operations under `/api/v1`. All UUIDs are explicit, responses use
camelCase, and errors use the standard request-ID envelope.

## Retrieve a projection

`GET /products/{product_id}/catalog-projections/{projection_id}` returns the immutable SPEC-031
projection, including Product identity/version, schema and upstream lineage, readiness status and
reasons, counts, ordered reviewed attributes, and `createdAt`. Attributes contain compact decision,
candidate, source, and validation lineage but no raw extraction evidence.

Missing and cross-product projections return 404 `CATALOG_PROJECTION_NOT_FOUND`.

## Inspect current readiness

`GET /products/{product_id}/catalog-projections/{projection_id}/readiness` compares the immutable
snapshot with the current Product and returns:

```json
{
  "productId": "22222222-2222-4222-8222-222222222222",
  "projectionId": "11111111-1111-4111-8111-111111111111",
  "projectionStatus": "READY_WITH_WARNINGS",
  "blockingReasonCodes": [],
  "warningReasonCodes": ["MANUFACTURER_MISSING"],
  "productVersionAtProjection": 7,
  "currentProductVersion": 7,
  "projectionCurrent": true,
  "eligibleForReadyToPublish": true,
  "currentProductStatus": "REVIEW_REQUIRED"
}
```

BLOCKED and stale projections return HTTP 200 but are ineligible. An already-ready or otherwise
forbidden current Product status is also ineligible. Persisted blocker/warning codes are returned
unchanged.

## Apply readiness

`POST /products/{product_id}/publishing-readiness/apply` requires:

```json
{
  "projectionId": "11111111-1111-4111-8111-111111111111",
  "version": 7
}
```

Only a current READY or READY_WITH_WARNINGS projection may transition a REVIEW_REQUIRED Product.
Success returns HTTP 200 with previous/new status and version, projection status/ID, `appliedAt`,
and preserved warning codes. The Product update is conditional on both version and current status.
No automatic retry occurs.

## Errors

| Status | Code | Meaning |
| --- | --- | --- |
| 404 | `PRODUCT_NOT_FOUND` | Path Product does not exist |
| 404 | `CATALOG_PROJECTION_NOT_FOUND` | Projection is absent or isolated from this Product |
| 409 | `PRODUCT_VERSION_CONFLICT` | Request version is stale |
| 409 | `PUBLISHING_READINESS_PRODUCT_CHANGED` | Projection Product snapshot is stale |
| 409 | `PUBLISHING_READINESS_BLOCKED` | Persisted projection has blockers |
| 409 | `PUBLISHING_READINESS_STATUS_TRANSITION_NOT_ALLOWED` | Product is not REVIEW_REQUIRED |
| 409 | `PRODUCT_ALREADY_READY_TO_PUBLISH` | Product is already internally ready |
| 422 | `PUBLISHING_READINESS_CROSS_PRODUCT_PROJECTION` | Apply projection belongs elsewhere |
| 422 | `REQUEST_VALIDATION_FAILED` | Invalid path or request body |
| 503 | `PRODUCT_STORAGE_UNAVAILABLE` | Product persistence unavailable |
| 503 | `CATALOG_PROJECTION_STORAGE_UNAVAILABLE` | Projection persistence unavailable |

READY_TO_PUBLISH does not mean that any external publishing occurred.
