# Product API

SPEC-006 exposes exactly five product operations. DynamoDB Local and the products table must be available before using the real API:

```powershell
docker compose up -d dynamodb-local
uv run --project apps/api python scripts/dynamodb/create_tables.py
uv run --project apps/api uvicorn app.main:app --app-dir apps/api --reload
```

## Create a product

`POST /api/v1/products` returns HTTP 201.

```json
{
  "name": "PX-400 Centrifugal Pump",
  "manufacturer": "ABC Industries",
  "modelNumber": "PX-400",
  "category": "CENTRIFUGAL_PUMP",
  "description": "Industrial centrifugal pump"
}
```

The application generates `productId`, `status`, `sourceCount`, `version`, `createdAt`, and `updatedAt`. System fields and unknown fields are rejected.

Example response:

```json
{
  "productId": "d8c8d2bc-3957-4a15-966f-a06da1fd9047",
  "name": "PX-400 Centrifugal Pump",
  "manufacturer": "ABC Industries",
  "modelNumber": "PX-400",
  "category": "CENTRIFUGAL_PUMP",
  "status": "DRAFT",
  "description": "Industrial centrifugal pump",
  "sourceCount": 0,
  "createdAt": "2026-08-06T12:00:00Z",
  "updatedAt": "2026-08-06T12:00:00Z",
  "version": 1
}
```

## Retrieve a product

`GET /api/v1/products/{product_id}` validates `product_id` as a UUID and returns HTTP 200 with the same product response contract.

## List products

`GET /api/v1/products` returns products newest first by `createdAt`. It supports only these optional query parameters:

| Parameter | Contract |
| --- | --- |
| `limit` | Integer from 1 through 100; defaults to 20 |
| `cursor` | Opaque continuation value returned by a previous page |
| `status` | `DRAFT`, `PROCESSING`, `REVIEW_REQUIRED`, `READY_TO_PUBLISH`, or `FAILED` |

Example request:

```text
GET /api/v1/products?limit=20&status=DRAFT
```

Example empty or final-page response:

```json
{
  "items": [],
  "nextCursor": null
}
```

Each item uses the create/retrieve product response shown above. When another page exists, `nextCursor` contains an opaque value that may be passed unchanged in the next request. It must not be decoded or modified by clients. Raw DynamoDB pagination keys and total counts are never exposed.

## Update a product

`PATCH /api/v1/products/{product_id}` partially updates an existing product and returns HTTP 200 with the complete product record. The request must include the positive `version` last retrieved by the client and at least one editable field.

```http
PATCH /api/v1/products/550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json
```

```json
{
  "version": 1,
  "status": "PROCESSING",
  "description": "Processing has started."
}
```

Editable fields are `name`, `manufacturer`, `modelNumber`, `category`, `status`, and `description`. Missing fields remain unchanged. Explicit `null` clears `manufacturer`, `modelNumber`, or `description`; `name`, `category`, and `status` cannot be null. A body containing only `version` is rejected, while an explicitly supplied same-value field is accepted.

`productId`, `createdAt`, `updatedAt`, `sourceCount`, and `entityType` are immutable and rejected if supplied. After a successful conditional write, the repository increments the version by exactly one and refreshes `updatedAt`; `productId`, `createdAt`, and `sourceCount` remain unchanged.

## Delete a product

`DELETE /api/v1/products/{product_id}?version={version}` permanently deletes an existing product only when the required positive query `version` matches the stored version.

```http
DELETE /api/v1/products/550e8400-e29b-41d4-a716-446655440000?version=3
```

A successful delete returns `HTTP/1.1 204 No Content` with an empty response body. The service first confirms the product exists, and the repository still performs an atomic version-conditioned delete to protect against concurrent changes. An absent product returns 404, while a stale version returns 409 and leaves the newer product untouched.

Deletion is not soft deletion and does not cascade to sources, files, or external storage. Restore, bulk deletion, and frontend deletion are not available.

## Errors

| Status | Code | Meaning |
| --- | --- | --- |
| 400 | `INVALID_PRODUCT_CURSOR` | The opaque listing cursor is malformed or incompatible |
| 404 | `PRODUCT_NOT_FOUND` | No product exists for the requested UUID |
| 409 | `PRODUCT_ALREADY_EXISTS` | Conditional creation found an existing ID |
| 409 | `PRODUCT_VERSION_CONFLICT` | The expected version is stale; retrieve and retry with the latest record |
| 422 | `REQUEST_VALIDATION_FAILED` | Body, path, or query validation failed |
| 503 | `PRODUCT_STORAGE_UNAVAILABLE` | Persistence is temporarily unavailable |
| 500 | `INTERNAL_SERVER_ERROR` | An unexpected server failure occurred |

Errors use this stable envelope and include the same generated ID in the `X-Request-ID` response header:

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "The requested product does not exist.",
    "details": {
      "productId": "d8c8d2bc-3957-4a15-966f-a06da1fd9047"
    }
  },
  "requestId": "request-uuid"
}
```

The generated OpenAPI document at `/openapi.json` is the authoritative schema. Soft deletion, restore, bulk deletion, and PUT replacement are not implemented.
