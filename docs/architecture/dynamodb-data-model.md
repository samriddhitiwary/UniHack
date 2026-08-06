# DynamoDB Data Model

The local model contains configuration-derived `{DYNAMODB_TABLE_PREFIX}-products` and `{DYNAMODB_TABLE_PREFIX}-sources` tables. No production table is provisioned by this repository.

## Item shape

```json
{
  "productId": "d8c8d2bc-3957-4a15-966f-a06da1fd9047",
  "entityType": "PRODUCT",
  "name": "PX-400 Centrifugal Pump",
  "manufacturer": "ABC Industries",
  "modelNumber": "PX-400",
  "category": "CENTRIFUGAL_PUMP",
  "status": "DRAFT",
  "description": null,
  "sourceCount": 0,
  "version": 1,
  "createdAt": "2026-08-06T11:30:00.000000Z",
  "updatedAt": "2026-08-06T11:30:00.000000Z"
}
```

The table partition key is `productId` (String). Product identity and `createdAt` are immutable. Updates condition on the stored `version`, then increment it and refresh `updatedAt`.

## Access patterns and indexes

| Access pattern | Operation |
| --- | --- |
| Create by product ID | Conditional `PutItem`; `attribute_not_exists(productId)` |
| Retrieve by product ID | Consistent `GetItem` |
| Update by expected version | Conditional `UpdateItem`; stored version must match |
| Delete by product ID | Conditional `DeleteItem`; item and expected version must match |
| List newest products | Query `CreatedAtIndex` with `entityType = PRODUCT` |
| List newest products in a status | Query `StatusCreatedAtIndex` with the status enum value |

`CreatedAtIndex` uses `entityType` as its partition key and `createdAt` as its sort key. `StatusCreatedAtIndex` uses `status` and `createdAt`. Both project all product fields. These are the only indexes because they map directly to approved access patterns. Manufacturer, model, category, and free-text access are deferred.

Listings never scan the table, are bounded to 1–100 items, and request descending sort order. DynamoDB `LastEvaluatedKey` values are encoded as URL-safe base64 JSON cursors and validated before reuse; repository consumers never receive raw keys.

## Product sources table

The sources table stores metadata only. Its partition key is `productId` (String) and sort key is `sourceId` (String), grouping source metadata by owning product without implementing a relational foreign key.

```json
{
  "productId": "d8c8d2bc-3957-4a15-966f-a06da1fd9047",
  "sourceId": "f348db3c-4da2-47f8-8716-179b7dd9273c",
  "sourceType": "PDF",
  "status": "PENDING",
  "originalFilename": "pump-datasheet.pdf",
  "storageKey": null,
  "mimeType": "application/pdf",
  "fileSizeBytes": 102400,
  "checksumSha256": null,
  "displayName": "Pump Datasheet",
  "textContent": null,
  "errorMessage": null,
  "version": 1,
  "createdAt": "2026-08-06T16:00:00.000000Z",
  "updatedAt": "2026-08-06T16:00:00.000000Z"
}
```

Source types are exactly `PDF`, `IMAGE`, `CSV`, and `TEXT`. Statuses are `PENDING`, `READY`, `PROCESSING`, `COMPLETED`, and `FAILED`.

| Source access pattern | Operation |
| --- | --- |
| Create for a product | Conditional `PutItem` on the composite key |
| Retrieve one source | Consistent `GetItem` by `productId` and `sourceId` |
| List a product’s sources newest first | Descending query on `ProductCreatedAtIndex` |
| Update metadata/status | Conditional `UpdateItem` using expected version |
| Delete metadata | Conditional `DeleteItem` using expected version |

`ProductCreatedAtIndex` uses `productId` as partition key and `createdAt` as sort key and projects all metadata. This is the only source index. Listings are bounded to 1–100, never scan, and use a URL-safe cursor envelope scoped to `product_sources` and the owning product ID. Product-list and cross-product cursors are rejected.

The table contains no file bytes, base64 content, extracted PDF/CSV/image content, prompts, AI results, evidence, or storage credentials. Source update/delete operations use optimistic concurrency and distinguish missing records from stale versions after conditional failures.

## Local creation

After starting DynamoDB Local, run:

```powershell
uv run --project apps/api python scripts/dynamodb/create_tables.py
```

or `make dynamodb-create-tables`. The script creates the products table with its two indexes and the sources table with `ProductCreatedAtIndex`, waits until both exist, and exits successfully without altering data when either table is already present.

Future table specifications must continue to state access patterns, keys, indexes, conditional-write needs, pagination behavior, and item-size strategy before implementation.
