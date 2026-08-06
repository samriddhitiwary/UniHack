# SPEC-002: Product Domain Model and DynamoDB Access Patterns

## Status

Completed

## Objective

Create the backend domain and persistence foundation for storing industrial products in DynamoDB without exposing product API routes or frontend product functionality.

## User Story

As a future CatalogIQ application service, I need a validated product model and repository abstraction so I can create, retrieve, update, list, and explicitly delete foundational product records without depending on Boto3 or raw DynamoDB data.

## Scope

- Foundational product enums, entity, and Pydantic schemas.
- Centralized DynamoDB serialization and opaque pagination cursors.
- A mockable product repository protocol and DynamoDB implementation.
- One local products table with the two indexes required by approved access patterns.
- Automated domain, schema, serialization, cursor, and repository tests.
- DynamoDB architecture and local-development documentation.

## Out of Scope

Product HTTP routes, frontend pages, uploads, PDF/image/AI extraction, technical attributes, validation workflows, human review, generated commerce content, Product Intelligence Score, search, dashboards, authentication, S3, real AWS tables, and deployment pipelines.

## Functional Requirements

1. Create product entities with application-generated UUIDs, UTC timestamps, `DRAFT` status, zero sources, and version 1.
2. Validate and normalize the approved foundational fields only.
3. Store products under `{DYNAMODB_TABLE_PREFIX}-products` using camelCase item attributes.
4. Prevent duplicate creation through a conditional write.
5. Retrieve a product by ID, returning `None` when it does not exist.
6. Update with optimistic concurrency, incrementing the stored version and refreshing `updated_at`.
7. List all products newest first through `CreatedAtIndex` and list a status newest first through `StatusCreatedAtIndex`.
8. Bound list sizes and return opaque cursors rather than DynamoDB keys.
9. Delete only through an explicit repository call.
10. Create the local table and both indexes idempotently without deleting existing data.

## Non-Functional Requirements

- Python 3.12, strict mypy, Ruff, pytest, and existing SPEC-001 configuration conventions.
- No table scans for approved listing workflows.
- No Python floats in serialized DynamoDB values.
- Repository consumers never receive raw DynamoDB items or Boto3 exceptions.
- Timestamps are timezone-aware UTC and serialized consistently.
- Cursors use safe JSON encoding and never unsafe object deserialization.

## Domain Model

`Product` is an immutable dataclass with:

| Field | Type | Rules |
| --- | --- | --- |
| `product_id` | UUID | Required, application-generated, immutable |
| `name` | string | Trimmed, 2–200 characters |
| `manufacturer` | optional string | Trimmed, blank becomes `None`, max 200 |
| `model_number` | optional string | Case-preserving, trimmed, blank becomes `None`, max 120 |
| `category` | `ProductCategory` | `UNCLASSIFIED`, `CENTRIFUGAL_PUMP`, or `INDUCTION_MOTOR` |
| `status` | `ProductStatus` | `DRAFT`, `PROCESSING`, `REVIEW_REQUIRED`, `READY_TO_PUBLISH`, or `FAILED` |
| `description` | optional string | Plain text, trimmed, blank becomes `None`, max 4,000 |
| `source_count` | integer | Non-negative; default 0 |
| `created_at` | datetime | Aware UTC; immutable |
| `updated_at` | datetime | Aware UTC |
| `version` | integer | Positive; starts at 1 |

`ProductCreate`, `ProductUpdate`, `ProductRecord`, and `ProductListResult` provide input and persistence-boundary validation. Schemas reject unknown fields.

## DynamoDB Access Patterns

1. Create a product by `productId` using `attribute_not_exists(productId)`.
2. Retrieve one product by `productId` with a consistent read.
3. Replace one product when `version` equals the expected version.
4. List products newest first by querying `CreatedAtIndex` for `entityType = PRODUCT`.
5. List products newest first for one status by querying `StatusCreatedAtIndex`.
6. Delete one product by `productId` only when it exists.
7. Continue either listing query with an opaque cursor containing its `LastEvaluatedKey`.

Manufacturer, model-number, category, search, and scan-based access patterns are intentionally unsupported.

## Table Design

Table: `{DYNAMODB_TABLE_PREFIX}-products`

- Partition key: `productId` (String)
- `CreatedAtIndex`: partition key `entityType` (String), sort key `createdAt` (String), projection `ALL`. This serves the approved global creation-time listing without a scan.
- `StatusCreatedAtIndex`: partition key `status` (String), sort key `createdAt` (String), projection `ALL`. This serves status listings without filtering or scanning.
- Every item includes `entityType = PRODUCT`.
- The local script uses on-demand billing semantics; production capacity is deferred to SPEC-063.

## Data Validation Rules

Names must remain meaningful after trimming. Optional strings normalize blank input to `None`. Counts cannot be negative, versions must be positive, enum values must be approved strings, and timestamps must be timezone-aware. Domain validation is enforced independently of Pydantic so repository-returned entities preserve the same invariants.

## Serialization Rules

- Python uses snake_case; DynamoDB uses the documented camelCase item shape.
- UUID and enums become strings.
- UTC datetimes use fixed microsecond ISO-8601 text ending in `Z`.
- Integers remain integers; floats are rejected recursively; `Decimal` values are supported.
- Optional fields remain explicit DynamoDB `NULL` values.
- Invalid or incomplete items raise `ProductSerializationError`.

## Error Handling

- Duplicate create: `ProductAlreadyExistsError`.
- Explicit update/delete of a missing product: `ProductNotFoundError`.
- Stale update: `ProductVersionConflictError`.
- Malformed cursor: `InvalidProductCursorError`.
- Invalid item conversion: `ProductSerializationError`.
- Other DynamoDB failures: `ProductRepositoryError`, chained from the original exception.

`get_by_id` alone uses `None` as its documented missing-record contract.

## Security Considerations

Cursors contain only pagination keys, are encoded with URL-safe base64 JSON, and contain no secrets. Decoding never uses pickle or executable formats. Errors do not expose credentials or table contents. Table names come from validated configuration, and repository methods use expression attribute values rather than string interpolation for user-controlled data.

## Edge Cases

- Blank optional text and surrounding whitespace.
- Naive timestamps and invalid enum values.
- Duplicate IDs, missing records, stale versions, and concurrent deletion.
- Limits outside the allowed 1–100 range.
- Empty, truncated, non-base64, non-JSON, and structurally invalid cursors.
- Empty result pages and final pages without cursors.
- Multiple records with close or identical creation timestamps.

## Acceptance Criteria

1. The specification and derived task checklist exist.
2. Product enums, immutable entity, and four schemas implement the approved model.
3. Central serialization handles UUID, datetime, enums, Decimal, optional/nested values and rejects floats.
4. The repository protocol is mockable and returns domain objects.
5. DynamoDB create is conditional and duplicate-safe.
6. Update enforces expected version, increments version, and refreshes UTC `updated_at`.
7. Listings query only the two approved indexes with bounded limits and opaque cursors.
8. Explicit deletion and documented missing-record behavior work.
9. The idempotent local script creates exactly the products table and two GSIs.
10. Required tests and all backend quality checks pass.
11. Architecture and development documentation are current.
12. No API routes, frontend product UI, or unrelated future features are implemented.

## Test Plan

- Unit-test entity defaults, generation, normalization, enums, invalid values, and UTC rules.
- Unit-test schema field boundaries, extra-field rejection, partial updates, and normalization.
- Unit-test item serialization, type conversion, timestamp format, float rejection, and invalid items.
- Unit-test cursor round trips, missing cursors, malformed values, and structural validation.
- Test the DynamoDB repository with Botocore Stubber responses for every method, conditional conflicts, pagination, index selection, and wrapped failures.
- Run the local table-creation script twice against DynamoDB Local and confirm the exact key/index schema.
- Run pytest with coverage, Ruff lint/format, and strict mypy.

## Implementation Notes

Listings are newest first (`ScanIndexForward=False`). Limits are constrained to 1–100. The repository uses the existing low-level Boto3 client and centralized TypeSerializer/TypeDeserializer helpers. Conditional `UpdateItem` changes only mutable attributes, preserves the stored identity and creation time, and owns the next version and update timestamp.

## Completion Record

Completed on 2026-08-06.

- Implemented the immutable product entity, approved string enums, strict Pydantic schemas, centralized item serialization, and opaque cursor handling.
- Implemented the repository protocol and DynamoDB repository with conditional creation, consistent reads, optimistic `UpdateItem`, newest-first GSI queries, pagination, and explicit conditional deletion.
- Implemented and executed the idempotent local products-table script. The first execution created `catalogiq-dev-products`; the second reported it already present. DynamoDB confirmed the `productId` key and exactly `CreatedAtIndex` and `StatusCreatedAtIndex`.
- Added stubbed repository request-contract tests and a gated real DynamoDB Local integration contract test.
- Final backend suite: 54 passed with 91.22% coverage.
- Ruff lint passed; Ruff formatting confirmed 47 files formatted; strict mypy passed all 30 source files.
- Existing frontend test, lint, formatting, and production build checks passed unchanged.
- Scope scan confirmed no product routes, product frontend modules, uploads, extraction, dashboard, authentication, S3, review workflow, or TypeScript artifacts.
- All 25 acceptance criteria passed. No SPEC-003 work was started.
