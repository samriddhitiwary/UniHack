# DynamoDB Data Model

The local model contains configuration-derived products, sources, processing-jobs, and extraction-results tables. No production table is provisioned by this repository.

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

## Processing jobs table

The processing-jobs table stores safe tracking metadata for future attempts and uses string partition key `jobId`. It does not enforce product/source foreign keys and stores no extracted content, prompts, responses, binaries, or stack traces.

```json
{
  "jobId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "productId": "d8c8d2bc-3957-4a15-966f-a06da1fd9047",
  "sourceId": "f348db3c-4da2-47f8-8716-179b7dd9273c",
  "sourceScope": "d8c8d2bc-3957-4a15-966f-a06da1fd9047#f348db3c-4da2-47f8-8716-179b7dd9273c",
  "jobType": "SOURCE_PROCESSING",
  "status": "PENDING",
  "attempt": 1,
  "progressPercent": 0,
  "errorCode": null,
  "errorMessage": null,
  "resultReference": null,
  "version": 1,
  "createdAt": "2026-08-07T06:00:00.000000Z",
  "startedAt": null,
  "completedAt": null,
  "updatedAt": "2026-08-07T06:00:00.000000Z"
}
```

Job types are `SOURCE_PROCESSING`, `PDF_TEXT_EXTRACTION`, `PDF_TABLE_EXTRACTION`, `IMAGE_ANALYSIS`, and `CSV_PROCESSING`. Statuses are `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED`. Approved transitions are PENDING to RUNNING/CANCELLED and RUNNING to COMPLETED/FAILED/CANCELLED; terminal states do not transition.

| Job access pattern | Operation |
| --- | --- |
| Create by job ID | Conditional `PutItem`; job ID must not exist |
| Retrieve by job ID | Consistent `GetItem` |
| List newest jobs for a product | Descending query on `ProductCreatedAtIndex` |
| List newest jobs for a product/source | Descending query on `SourceCreatedAtIndex` using `sourceScope` |
| Update state | Conditional `UpdateItem` using expected version |

`ProductCreatedAtIndex` uses `productId`/`createdAt`. `SourceCreatedAtIndex` uses server-generated `sourceScope = productId#sourceId`/`createdAt`, preventing global source enumeration. The two list paths use separate opaque cursor scopes bound to their complete query identity. Limits are 1–100; no scan, total count, global list, status dashboard, worker claim, retry queue, or delete operation exists. Updates increment version once and refresh `updatedAt`.

## PDF extraction results table

The extraction-results table separates page evidence from source and job records. Its
partition key is `extractionId` and sort key is `recordKey`.

| Record | Contents |
| --- | --- |
| `META` | Job/product/source IDs, parser/version, counts, quality, warnings, creation time |
| `PAGE#000001` | Page number, normalized text, character count, and has-text flag |

One page per item avoids unsafe single-item growth for moderate PDFs. Configured page text
is limited to 100,000 characters, safely below DynamoDB's per-item limit. META records
alone contain `jobId` and `createdAt`, so `JobIdIndex` (`jobId`/`createdAt`) is sparse.

| Extraction access pattern | Operation |
| --- | --- |
| Create result | Conditional META `PutItem`, followed by bounded page records |
| Retrieve by extraction ID | Paginated consistent partition query |
| Retrieve by job ID | `JobIdIndex` query followed by extraction partition query |

There is no scan, list API, result API, update, or delete contract. Missing/inconsistent
page records are controlled serialization errors and cannot produce a completed job.

## Local creation

After starting DynamoDB Local, run:

```powershell
uv run --project apps/api python scripts/dynamodb/create_tables.py
```

or `make dynamodb-create-tables`. The script creates products, sources, processing-jobs,
and extraction-results tables with their documented indexes. It waits for each table and
exits successfully without altering data when a table is already present.

Future table specifications must continue to state access patterns, keys, indexes, conditional-write needs, pagination behavior, and item-size strategy before implementation.
