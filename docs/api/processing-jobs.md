# Processing Job API

SPEC-015 exposes exactly four metadata operations:

```text
POST /api/v1/products/{product_id}/sources/{source_id}/jobs
GET  /api/v1/processing-jobs/{job_id}
GET  /api/v1/products/{product_id}/processing-jobs?limit=20&cursor=...
GET  /api/v1/products/{product_id}/sources/{source_id}/jobs?limit=20&cursor=...
```

These endpoints store and read job tracking records. They do not start jobs or execute
processing.

## Create a job

The create request accepts only camel-case `jobType`:

```json
{
  "jobType": "PDF_TEXT_EXTRACTION"
}
```

The service verifies the product first, retrieves the source under that product, checks
compatibility, and creates exactly one immutable job. The client cannot provide job,
product, or source IDs, attempt, status, progress, errors, result reference, timestamps,
or version.

| Source type | Supported job types |
| --- | --- |
| `TEXT` | `SOURCE_PROCESSING` |
| `PDF` | `SOURCE_PROCESSING`, `PDF_TEXT_EXTRACTION`, `PDF_TABLE_EXTRACTION` |
| `IMAGE` | `SOURCE_PROCESSING`, `IMAGE_ANALYSIS`, `IMAGE_OCR` |
| `CSV` | `SOURCE_PROCESSING`, `CSV_PROCESSING` |

Incompatible pairs return HTTP 422 with
`PROCESSING_JOB_TYPE_NOT_SUPPORTED`. A successful request returns HTTP 201 and starts
with `PENDING`, attempt 1, progress 0, version 1, no errors or result reference, and no
started/completed timestamp. No source status changes and no processing starts.

`PRODUCT_CLASSIFICATION` is an internal product-level job type whose record has `sourceId: null`.
It is deliberately unsupported by this source-scoped create endpoint and returns the same HTTP 422
compatibility error. SPEC-021 adds no classification execution or result endpoint.

`ATTRIBUTE_CONFLICT_DETECTION` is likewise internal and product-level. Its record has
`sourceId: null` and one explicit `attributeNormalizationId`; this public endpoint rejects it.

## Retrieve a job

`GET /api/v1/processing-jobs/{job_id}` returns the camel-case safe record with HTTP 200.
A missing UUID returns `PROCESSING_JOB_NOT_FOUND` with HTTP 404. The internal
`sourceScope` index key is never returned.

## List product jobs

`GET /api/v1/products/{product_id}/processing-jobs` verifies the product before querying
`ProductCreatedAtIndex`. Results retain repository newest-first order. `limit` defaults
to 20 and accepts 1 through 100.

## List source jobs

`GET /api/v1/products/{product_id}/sources/{source_id}/jobs` verifies the product and
retrieves the source by both IDs before querying `SourceCreatedAtIndex`. A source owned
by another product produces the same `PRODUCT_SOURCE_NOT_FOUND` response as an absent
source.

Both lists accept an optional opaque cursor. Product cursors bind the product; source
cursors bind product and source, and scopes cannot be mixed. Invalid cursors return
HTTP 400 `INVALID_PROCESSING_JOB_CURSOR`. Empty results are:

```json
{
  "items": [],
  "nextCursor": null
}
```

No total count or raw DynamoDB pagination key is exposed.

## Errors

| Status | Code | Meaning |
| --- | --- | --- |
| 400 | `INVALID_PROCESSING_JOB_CURSOR` | Cursor is malformed, wrong-scope, or wrong-identity |
| 404 | `PRODUCT_NOT_FOUND` | Required parent product is absent |
| 404 | `PRODUCT_SOURCE_NOT_FOUND` | Product-scoped source is absent |
| 404 | `PROCESSING_JOB_NOT_FOUND` | Requested job is absent |
| 409 | `PROCESSING_JOB_ALREADY_EXISTS` | Conditional creation found an ID collision |
| 422 | `PROCESSING_JOB_TYPE_NOT_SUPPORTED` | Job type is incompatible with the source type |
| 422 | `REQUEST_VALIDATION_FAILED` | UUID, query, or strict request body is invalid |
| 503 | `PRODUCT_STORAGE_UNAVAILABLE` | Product repository is unavailable |
| 503 | `PRODUCT_SOURCE_STORAGE_UNAVAILABLE` | Source repository is unavailable |
| 503 | `PROCESSING_JOB_STORAGE_UNAVAILABLE` | Job repository is unavailable |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected safe server failure |

The OpenAPI document contains no job update, delete, start, cancel, retry, or global-list
operation. `IMAGE_OCR` is metadata creation only; it does not execute OCR through the API.
Workers, queues, schedulers, hosted OCR/AI, S3, and frontend job UI remain absent.
