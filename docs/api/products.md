# Product API

SPEC-004 exposes exactly three product operations. DynamoDB Local and the products table must be available before using the real API:

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

## Errors

| Status | Code | Meaning |
| --- | --- | --- |
| 400 | `INVALID_PRODUCT_CURSOR` | The opaque listing cursor is malformed or incompatible |
| 404 | `PRODUCT_NOT_FOUND` | No product exists for the requested UUID |
| 409 | `PRODUCT_ALREADY_EXISTS` | Conditional creation found an existing ID |
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

The generated OpenAPI document at `/openapi.json` is the authoritative schema. Product update and deletion are not implemented.
