# Product Source API

The API exposes exactly six product-source operations:

```text
POST /api/v1/products/{product_id}/sources/text
POST /api/v1/products/{product_id}/sources/upload
GET /api/v1/products/{product_id}/sources
GET /api/v1/products/{product_id}/sources/{source_id}
PATCH /api/v1/products/{product_id}/sources/{source_id}
DELETE /api/v1/products/{product_id}/sources/{source_id}?version={version}
```

It creates source metadata and normalized plain text in DynamoDB, stores validated file uploads through configured object storage, provides product-scoped metadata listing/retrieval/update, and conditionally deletes one source plus any file object. It does not provide bulk deletion, restore, content/file replacement, download, parsing, or processing jobs.

## Create a text source

The path `product_id` must be a UUID for an existing product. The request accepts only:

```json
{
  "displayName": "Supplier-provided product details",
  "textContent": "Manufacturer: ABC Industries\nModel: PX-400\nMaximum pressure: 16 bar"
}
```

`textContent` is required, stripped at both ends, nonempty, and limited to 50,000 characters. Internal whitespace and newlines are retained. `displayName` is optional, stripped, limited to 200 characters, and becomes `null` when blank. Unknown fields and client-supplied identity, type, status, file/storage, checksum, timestamp, error, or version fields are rejected.

The service first retrieves the parent product by key. It returns `PRODUCT_NOT_FOUND` without calling the source repository when the product is absent.

Successful creation returns HTTP 201:

```json
{
  "sourceId": "f348db3c-4da2-47f8-8716-179b7dd9273c",
  "productId": "d8c8d2bc-3957-4a15-966f-a06da1fd9047",
  "sourceType": "TEXT",
  "status": "READY",
  "originalFilename": null,
  "storageKey": null,
  "mimeType": "text/plain",
  "fileSizeBytes": 67,
  "checksumSha256": "64-character-lowercase-sha256",
  "displayName": "Supplier-provided product details",
  "textContent": "Manufacturer: ABC Industries\nModel: PX-400\nMaximum pressure: 16 bar",
  "errorMessage": null,
  "createdAt": "2026-08-06T18:00:00Z",
  "updatedAt": "2026-08-06T18:00:00Z",
  "version": 1
}
```

`fileSizeBytes` is the UTF-8 byte length of the normalized text, which can differ from its character count. `checksumSha256` is calculated from those exact UTF-8 bytes. Text sources start at `READY` because their content is already persisted; no processing starts automatically. No filename, storage key, or object is created.

## Errors

| Status | Code | Meaning |
| --- | --- | --- |
| 404 | `PRODUCT_NOT_FOUND` | The parent product does not exist |
| 404 | `PRODUCT_SOURCE_NOT_FOUND` | The source does not exist under the requested product |
| 400 | `INVALID_PRODUCT_SOURCE_CURSOR` | The source cursor is malformed, wrong-scope, or belongs to another product |
| 409 | `PRODUCT_SOURCE_VERSION_CONFLICT` | The client version is stale |
| 409 | `PRODUCT_SOURCE_STATUS_TRANSITION_INVALID` | The requested direct status transition is not approved |
| 409 | `PRODUCT_SOURCE_ALREADY_EXISTS` | Conditional source creation found the generated identity already present |
| 422 | `REQUEST_VALIDATION_FAILED` | The UUID or request body is invalid |
| 503 | `PRODUCT_STORAGE_UNAVAILABLE` | Parent-product persistence is unavailable |
| 503 | `PRODUCT_SOURCE_STORAGE_UNAVAILABLE` | Product-source persistence is unavailable |
| 500 | `INTERNAL_SERVER_ERROR` | An unexpected server error occurred |

Errors use the repository-wide safe envelope and return the same generated request ID in the body and `X-Request-ID` header. They do not expose DynamoDB, table, request, or stack-trace details.

## Upload a file source

`POST /api/v1/products/{product_id}/sources/upload` accepts `multipart/form-data` with required binary `file` and optional `displayName`. It supports PDF, PNG, JPEG, WEBP, and CSV using approved extension/MIME pairs.

The service reduces fake paths to a basename, lowercases the extension, checks declared MIME and PDF/PNG/JPEG/WEBP signatures. CSV must be nonempty, null-free UTF-8 without binary control characters; it is not parsed. Default streamed limits are 10 MiB for PDF/images and 5 MiB for CSV.

Success returns HTTP 201 with `READY`, a secure generated object key, and size/SHA-256 returned by storage. Persistence failure triggers compensating object deletion while preserving the database error.

Additional upload errors are `PRODUCT_SOURCE_FILE_TOO_LARGE` (413), `UNSUPPORTED_PRODUCT_SOURCE_FILE_TYPE`, `PRODUCT_SOURCE_MIME_TYPE_MISMATCH`, and `INVALID_PRODUCT_SOURCE_FILE_CONTENT` (422), plus `OBJECT_STORAGE_UNAVAILABLE` (503).

## List product sources

`GET /api/v1/products/{product_id}/sources` verifies that the UUID parent exists and returns its source metadata newest first:

```json
{
  "items": [],
  "nextCursor": null
}
```

`limit` is optional, defaults to 20, and accepts values from 1 through 100. `cursor` is an optional opaque continuation token. The cursor is scoped to product-source listing and bound to the product UUID; malformed, wrong-scope, and cross-product cursors return the same safe `400 INVALID_PRODUCT_SOURCE_CURSOR` response. Raw DynamoDB keys and total counts are never returned.

An existing product with no sources returns HTTP 200 with an empty `items` array and `nextCursor: null`. No status or source-type filters are supported because SPEC-011 adds no scans, indexes, or incomplete in-memory filtering.

## Retrieve a product source

`GET /api/v1/products/{product_id}/sources/{source_id}` validates both identifiers as UUIDs, verifies the parent product, and retrieves through the product/source composite key. Success returns HTTP 200 with the existing camel-case `ProductSourceRecord` metadata.

If the source is absent under that product, the API returns `404 PRODUCT_SOURCE_NOT_FOUND`. A source owned by another product produces the identical response and its ownership is not disclosed. Retrieval does not open object storage, read file bytes, expose a local filesystem path, or create a download URL.

## Update source metadata and status

`PATCH /api/v1/products/{product_id}/sources/{source_id}` accepts a strict partial request:

```json
{
  "version": 3,
  "displayName": "Updated supplier datasheet",
  "status": "PROCESSING",
  "errorMessage": null
}
```

`version` is required, must be a strict positive integer, and represents the version last retrieved by the client. At least one of `displayName`, `status`, or `errorMessage` must be explicitly supplied. Unknown fields and immutable identity, type, filename, storage, MIME, size, checksum, text, timestamp, or record-version fields are rejected with `422 REQUEST_VALIDATION_FAILED`.

Omitted editable fields remain unchanged. Explicit null or blank `displayName` clears the display name; explicit null or blank `errorMessage` clears the error. Status cannot be null. A same-value update is accepted and advances the version.

Approved transitions are:

| Current | Approved next status |
| --- | --- |
| `PENDING` | `READY`, `FAILED` |
| `READY` | `PROCESSING`, `FAILED` |
| `PROCESSING` | `COMPLETED`, `FAILED` |
| `FAILED` | `READY` |
| `COMPLETED` | None |

Every status may also remain unchanged. Invalid direct transitions return `409 PRODUCT_SOURCE_STATUS_TRANSITION_INVALID`; no intermediate transition is inferred. Recovery from `FAILED` to `READY` and completion from `PROCESSING` to `COMPLETED` clear stale `errorMessage` deterministically.

The service verifies the parent and retrieves the source using the product/source composite key. Missing and cross-product sources return the same safe 404. DynamoDB conditionally requires the requested version, increments it once, and refreshes `updatedAt`; stale writes return `409 PRODUCT_SOURCE_VERSION_CONFLICT` and are not retried.

## Delete a product source

`DELETE /api/v1/products/{product_id}/sources/{source_id}?version={version}` requires the positive integer version last retrieved by the client. Missing, zero, negative, empty, or non-integer versions return `422 REQUEST_VALIDATION_FAILED`. Version is a query parameter, not a request body.

The service verifies the parent, retrieves the source using both IDs, and compares the current version before destructive work. A stale pre-check returns `409 PRODUCT_SOURCE_VERSION_CONFLICT` without calling storage or repository deletion. DynamoDB still conditionally requires the version during final deletion to protect the race after the pre-check.

TEXT sources skip object storage. PDF, IMAGE, and CSV sources require a server-owned logical storage key and call `ObjectStorage.delete` exactly once before conditional metadata deletion. A missing key is a safe internal consistency error. A missing object returns `503 OBJECT_STORAGE_UNAVAILABLE` and retains metadata because storage contradicts the source record.

Success returns HTTP 204 with an empty body and no deleted record. If object deletion succeeds but final metadata deletion fails or detects a race, the repository error remains primary, a consistency-risk event is logged without the key, and success is not returned. The object cannot be recreated because local storage and DynamoDB do not share a transaction.

The OpenAPI document contains two source POST, two GET, one PATCH, and one DELETE operation only. It contains no source PUT, collection DELETE, bulk-delete, restore, download, replace-file, process, retry, parsing, or AI operation.
