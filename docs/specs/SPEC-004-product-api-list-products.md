# SPEC-004 — Product API: List Products

## Status

Completed

## Objective

Expose the existing product repository query access patterns through one paginated, read-only API endpoint.

## User Story

As an API consumer, I want to list products newest first, optionally filtered by status, so that I can traverse the catalogue safely without retrieving the full dataset.

## Scope

Implement only `GET /api/v1/products` with validated `limit`, opaque `cursor`, and optional `status` query parameters. Preserve the existing create and retrieve operations.

## Out of Scope

Product update or deletion; search; category, manufacturer, or model-number filters; alternative sorting; totals; frontend product workflows; dashboards; uploads; file processing; AI; authentication; authorization; deployment; and new DynamoDB indexes are excluded.

## Functional Requirements

- Return products ordered by `createdAt` descending.
- Use a default limit of 20 and permit limits from 1 through 100.
- Continue a listing with an opaque repository-owned cursor.
- Use the unfiltered repository query when `status` is absent and the status-index query when it is present.
- Return HTTP 200 with `items: []` and `nextCursor: null` when no results exist.
- Preserve the existing create and retrieve behavior.

## Non-Functional Requirements

The route remains thin, the service remains independent of FastAPI and Boto3, queries remain bounded, no scan or total-count operation is introduced, and failures use stable safe envelopes.

## Existing Dependencies

SPEC-004 reuses `Product`, `ProductStatus`, `ProductPage`, `ProductRecord`, `ProductListResult`, `ProductRepository`, `DynamoDBProductRepository`, the cursor codec, dependency providers, request-ID middleware, and global exception handling from SPEC-001 through SPEC-003. No new dependency is required.

## Service-Layer Design

`ProductService.list_products(*, limit, cursor=None, status=None) -> ProductListResult` selects exactly one repository method. It calls `ProductRepository.list_products` without a status or `ProductRepository.list_by_status` with one, converts domain products to existing public records, and preserves controlled cursor and repository errors.

## API Contract

`GET /api/v1/products` returns HTTP 200 with exactly `items` and `nextCursor`. Every item uses `ProductRecord` and camelCase serialization. Existing `POST /api/v1/products` and `GET /api/v1/products/{product_id}` remain unchanged.

## Query Parameters

- `limit`: optional integer, default 20, minimum 1, maximum 100.
- `cursor`: optional non-empty opaque string, maximum 4,096 characters.
- `status`: optional `ProductStatus` enum value.

No other listing filters or client-controlled persistence expressions are supported.

## Pagination Contract

The DynamoDB repository owns cursor validation and decoding so logic is not duplicated. It queries `CreatedAtIndex` or `StatusCreatedAtIndex` with `ScanIndexForward=False` and the validated limit. Clients receive only the opaque encoded next cursor; raw DynamoDB keys, totals, pages, index metadata, and consumed capacity are never returned.

## Error Handling

- Invalid `limit`, empty cursor syntax, or unsupported status: HTTP 422, `REQUEST_VALIDATION_FAILED`.
- Malformed or listing-incompatible opaque cursor: HTTP 400, `INVALID_PRODUCT_CURSOR`.
- Repository failure: HTTP 503, `PRODUCT_STORAGE_UNAVAILABLE`.
- Unexpected failure: HTTP 500, `INTERNAL_SERVER_ERROR`.

## Validation Rules

FastAPI validates query types, the inclusive limit bounds, the cursor string bounds, and the status enum before service invocation. The existing repository validates opaque cursor encoding, structure, and index compatibility before issuing its query.

## Security Considerations

The maximum page size is enforced. Cursor contents, decoded keys, infrastructure identifiers, persistence responses, and internal exceptions are not exposed or logged. Clients cannot choose indexes, filter expressions, projections, or table names. Existing CORS behavior is unchanged.

## Logging Requirements

Emit safe structured request and completion events containing only limit, optional status, result count, and boolean cursor-presence fields. Repository failures continue through the existing safe persistence-failure event. Never log cursor values, decoded keys, product bodies or descriptions, table names, raw AWS responses, or credentials.

## Edge Cases

- An empty table, a status with no matches, and a final empty page all return HTTP 200 with an empty result.
- Boundary limits 1 and 100 are valid; 0, negative values, values above 100, and non-integers are rejected.
- A cursor valid for one listing access pattern but incompatible with another is rejected as an invalid product cursor.
- The collection route and UUID member route remain distinct.

## Acceptance Criteria

All 44 acceptance criteria from the approved SPEC-004 request must pass: required spec records, one service method, correct repository selection, exact route and validation contract, opaque pagination, empty and ordered results, query-only repository behavior, public response schema, safe layering and errors, focused tests, exact OpenAPI operations, all backend and frontend quality gates, accurate documentation, completed checklist, and a clean out-of-scope scan.

## Test Plan

Add service unit tests for unfiltered and filtered selection, argument forwarding, empty and paginated results, exception preservation, dependency boundaries, and single-method dispatch. Add API integration tests for defaults, custom and boundary limits, every status, valid and malformed cursors, empty pages, safe persistence errors, route safety, and the exact OpenAPI contract. Run the complete backend suite with coverage, Ruff lint and formatting, strict mypy, unchanged frontend tests, ESLint, Prettier, the Vite production build, and Docker Compose validation.

## Implementation Notes

`ProductListResult` already exists and requires no replacement. Repository query ordering, index selection, maximum page size, cursor encoding, and cursor compatibility checks already satisfy the persistence contract. SPEC-004 only connects these foundations through the service and route and adds the specific invalid-cursor HTTP mapping.

## Completion Record

Completed on 2026-08-06. Added the single approved list route, service-level repository selection, bounded query validation, stable paginated response, safe cursor error mapping, structured list logging, focused service/API/OpenAPI coverage, and accurate API, README, and architecture documentation. The existing repository and cursor foundations required no changes.

Verification passed: 93 backend tests with 1 optional DynamoDB Local test skipped and 93.30% coverage; Ruff lint and formatting; strict mypy across 36 source files; 1 unchanged frontend test; ESLint; Prettier; Vite production build; Docker Compose configuration; and Git whitespace/scope inspection. All 44 acceptance criteria passed, and no out-of-scope feature was implemented.
