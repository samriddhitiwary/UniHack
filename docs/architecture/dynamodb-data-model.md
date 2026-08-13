# DynamoDB Data Model

The local model contains configuration-derived products, sources, processing-jobs, extraction-results, table-extraction-results, csv-processing-results, image-analysis-results, image-ocr-results, product-classification-results, category-attribute-schemas, structured-attribute-extraction-results, and attribute-normalization-results tables. No production table is provisioned by this repository.

The attribute-normalization-results table uses `normalizationId` and `recordKey`
(`META` or ordered `CANDIDATE#000001`). Its sparse `JobIdIndex` uses `jobId` and
`createdAt`. Metadata stores exact extraction/classification/category/schema
lineage and outcome counts. Candidate records preserve raw and canonical values,
conversion metadata, evidence provenance, and separate extraction/normalization
confidence. Conditional writes, 390 KB guards, complete pagination, and
consistent ID reads follow the structured-extraction result pattern.

The structured-attribute-extraction-results table uses `extractionId` and `recordKey` (`META` or ordered `CANDIDATE#000001`). Its sparse `JobIdIndex` uses `jobId` and `createdAt`. Metadata stores product, classification, category, schema-version/fingerprint, status, counts, warnings, and engine lineage; candidate records store raw values, raw units, confidence, parse/match state, and complete source evidence provenance. Writes are conditional, records are bounded below 390 KB, and complete ID reconstruction paginates with consistent reads.

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

Job types are `SOURCE_PROCESSING`, `PDF_TEXT_EXTRACTION`, `PDF_TABLE_EXTRACTION`, `IMAGE_ANALYSIS`, `IMAGE_OCR`, and `CSV_PROCESSING`. Statuses are `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED`. Approved transitions are PENDING to RUNNING/CANCELLED and RUNNING to COMPLETED/FAILED/CANCELLED; terminal states do not transition.

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

## PDF table extraction results table

The table-extraction-results table uses partition key `extractionId` and sort key `recordKey`.

| Record | Contents |
| --- | --- |
| `META` | Job/product/source IDs, parser/version, page/table/row/cell counts, quality, warnings, creation time |
| `TABLE#000001#000001` | Page/table numbers, dimensions, and nested ordered row/cell evidence |

One table per item avoids one aggregate payload. Each serialized record is rejected above a conservative 390,000-byte ceiling. Only META contains `jobId` and `createdAt`, so `JobIdIndex` is sparse. Creation is conditional, partition reads paginate and validate complete reconstruction, and job lookup uses the index followed by the partition query. No scan or global list exists.

## CSV processing results table

The csv-processing-results table uses partition key `processingId` and sort key `recordKey`.

| Record | Contents |
| --- | --- |
| `META` | Job/product/source IDs, encoding, delimiter, indexed header, aggregate counts, quality, warnings, creation time |
| `ROW#000000001` | Row number, canonical cells, overflow cells, original/normalized widths, malformed flag, warnings |

One row per item preserves source order without one unbounded aggregate. Every serialized item is rejected above 390,000 bytes. META alone carries `jobId` and `createdAt`, so `JobIdIndex` is sparse. Conditional creation protects identity; paginated consistent partition queries reconstruct and validate all expected rows; job lookup uses the index and then the partition. No scan or global list exists.

## Image analysis results table

The image-analysis-results table uses partition key `analysisId` and sort key `recordKey`.

| Record | Contents |
| --- | --- |
| `META` | Job/product/source IDs, parser/version, bounded image metadata, candidate status/score, counts, warning codes, creation time |
| `REGION#000001` | Ordered region type, bounded pixel box, basis-point coordinates, and heuristic score |

One record per deterministic region keeps geometry evidence separate from aggregate metadata. Every serialized item is rejected above 390,000 bytes. META alone carries `jobId` and `createdAt`, making `JobIdIndex` sparse. Conditional creation protects the result identity; paginated consistent partition queries reconstruct and validate all expected regions; job lookup uses the index followed by the partition query. No image bytes, crops, OCR output, scan, global list, update, delete, or public result API exists.

| Image-analysis access pattern | Operation |
| --- | --- |
| Create result | Conditional META `PutItem`, followed by bounded REGION records |
| Retrieve by analysis ID | Paginated consistent partition query |
| Retrieve by job ID | `JobIdIndex` query followed by analysis partition query |

## Image OCR results table

The image-ocr-results table uses partition key `ocrId` and sort key `recordKey`.

| Record | Contents |
| --- | --- |
| `META` | Job/product/source/analysis IDs, local engine/version, oriented dimensions, counts, quality, nameplate-text status/score, warnings, creation time |
| `BLOCK#000001` | Region ID, per-region reading order, normalized OCR text, confidence basis points, oriented pixel box, relative basis-point box |

Blocks remain separate from META so evidence growth is bounded per item. Every serialized record is rejected above 390,000 bytes. META alone carries `jobId` and `createdAt`, making `JobIdIndex` sparse. Creation is conditional; consistent partition reads paginate and validate contiguous block records; job lookup uses the index and then the partition. No image bytes, raw engine response, scans, global list, update, delete, or public result API exists.

| Image-OCR access pattern | Operation |
| --- | --- |
| Create result | Conditional META `PutItem`, followed by bounded BLOCK records |
| Retrieve by OCR ID | Paginated consistent partition query |
| Retrieve by job ID | `JobIdIndex` query followed by OCR partition query |

## Product classification results table

The product-classification-results table uses partition key `classificationId` and sort key
`recordKey`. META contains job/product identity, decision, integer confidence/scores, evidence and
conflict counts, engine/version, warnings, match count, and creation time. Ordered
`MATCH#000001` records contain bounded matched-signal provenance and excerpts. Only META contains
`jobId` and `createdAt`, making `JobIdIndex` sparse. Conditional writes, paginated consistent reads,
complete reconstruction validation, and the 390,000-byte item guard apply. No scans are used.

| Classification access pattern | Operation |
| --- | --- |
| Create result | Conditional META and ordered MATCH `PutItem` operations |
| Retrieve by classification ID | Paginated consistent partition query |
| Retrieve by job ID | `JobIdIndex` query followed by classification partition query |

## Category attribute schemas table

The category-attribute-schemas table uses string partition key `category` and numeric sort key
`version`. One item stores the deterministic schema ID, ACTIVE/INACTIVE status, bounded nested
attribute/unit/alias/example/validation metadata, SHA-256 fingerprint, and timestamps. Conditional
creation makes category/version immutable. Direct consistent `GetItem` retrieves a version; a
descending category query limited to 100 records locates ACTIVE without scans or a GSI. Items above
390,000 serialized bytes are rejected.

| Category-schema access pattern | Operation |
| --- | --- |
| Create immutable version | Conditional `PutItem` on category/version |
| Retrieve category/version | Consistent composite-key `GetItem` |
| Retrieve active version | Bounded descending category partition query |

Built-in local seeding preflights both version 1 fingerprints, creates missing pump/motor records,
skips identical records, and rejects drift or conflicting active content without overwrite.

## Attribute conflict detection results table

The attribute-conflict-detection-results table uses partition key `conflictDetectionId` and sort
key `recordKey`. `META` preserves job/product and normalization/extraction/classification/schema
lineage plus aggregate status/counts. Ordered `ATTRIBUTE#000001` records preserve per-attribute
candidate IDs, comparison counts, status, conflict type, warnings, and assessment confidence.
Ordered `GROUP#000001#000001` records preserve each distinct canonical value/unit cluster and its
candidate/source IDs. There is no selected value, winner, average, or rank.

Only META carries `jobId` and `createdAt`, making `JobIdIndex` sparse. Conditional writes,
paginated consistent partition reads, complete reconstruction validation, configured bounds, and
the 390,000-byte item guard apply. Retrieval by ID and job uses queries only; no scan is used.

## Attribute completeness results table

The attribute-completeness-results table uses partition key `completenessId` and sort key
`recordKey`. META stores exact upstream/schema lineage, status, required/optional/total counts,
integer basis-point percentages, warnings, engine/version, and creation time. Ordered ATTRIBUTE
records store schema identity/order, completeness state, consensus metadata, booleans, candidate
IDs, and warnings. META alone carries `jobId`/`createdAt` for sparse `JobIdIndex`. Conditional
writes, consistent paginated reads, complete reconstruction, configured bounds, and the
390,000-byte guard apply. No scan or selected value exists.

## Local creation

After starting DynamoDB Local, run:

```powershell
uv run --project apps/api python scripts/dynamodb/create_tables.py
```

or `make dynamodb-create-tables`. The script creates products, sources, processing-jobs,
extraction-results, table-extraction-results, csv-processing-results, image-analysis-results,
image-ocr-results, product-classification-results, category-attribute-schemas,
attribute-normalization-results, attribute-conflict-detection-results, and
attribute-completeness-results tables with their documented indexes. It waits for each table and
exits successfully without altering data when a table is already present.

Future table specifications must continue to state access patterns, keys, indexes, conditional-write needs, pagination behavior, and item-size strategy before implementation.
