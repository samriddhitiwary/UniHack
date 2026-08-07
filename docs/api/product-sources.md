# Product Source API

SPEC-009 exposes exactly one product-source operation:

```text
POST /api/v1/products/{product_id}/sources/text
```

It creates source metadata and normalized plain text in DynamoDB. It does not upload a file, call local object storage, process content, or provide source listing/retrieval/update/deletion.

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
| 409 | `PRODUCT_SOURCE_ALREADY_EXISTS` | Conditional source creation found the generated identity already present |
| 422 | `REQUEST_VALIDATION_FAILED` | The UUID or request body is invalid |
| 503 | `PRODUCT_STORAGE_UNAVAILABLE` | Parent-product persistence is unavailable |
| 503 | `PRODUCT_SOURCE_STORAGE_UNAVAILABLE` | Product-source persistence is unavailable |
| 500 | `INTERNAL_SERVER_ERROR` | An unexpected server error occurred |

Errors use the repository-wide safe envelope and return the same generated request ID in the body and `X-Request-ID` header. They do not expose DynamoDB, table, request, or stack-trace details.

The OpenAPI document contains no source GET, PATCH, DELETE, collection-create, or upload operation.
