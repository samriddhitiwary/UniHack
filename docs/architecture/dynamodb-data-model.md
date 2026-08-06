# DynamoDB Data Model

SPEC-002 introduces one products table for foundational product records. Names remain configuration-derived as `{DYNAMODB_TABLE_PREFIX}-products`; no production table is provisioned by this repository.

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
| Delete by product ID | Conditional `DeleteItem`; item must exist |
| List newest products | Query `CreatedAtIndex` with `entityType = PRODUCT` |
| List newest products in a status | Query `StatusCreatedAtIndex` with the status enum value |

`CreatedAtIndex` uses `entityType` as its partition key and `createdAt` as its sort key. `StatusCreatedAtIndex` uses `status` and `createdAt`. Both project all product fields. These are the only indexes because they map directly to approved access patterns. Manufacturer, model, category, and free-text access are deferred.

Listings never scan the table, are bounded to 1–100 items, and request descending sort order. DynamoDB `LastEvaluatedKey` values are encoded as URL-safe base64 JSON cursors and validated before reuse; repository consumers never receive raw keys.

## Local creation

After starting DynamoDB Local, run:

```powershell
uv run --project apps/api python scripts/dynamodb/create_tables.py
```

or `make dynamodb-create-tables`. The script waits for the local service, creates both indexes, waits until the table exists, and exits successfully without altering data when the table is already present.

Future table specifications must continue to state access patterns, keys, indexes, conditional-write needs, pagination behavior, and item-size strategy before implementation.
