# SPEC-036 Task Checklist

## Planning

- [x] Inspect Product, projection, and score access patterns
- [x] Define supported search/filter matrix and explicit latest-artifact semantics
- [x] Define summary, pagination, indexes, and controlled failures

## Implementation

- [x] Add search domain/query and response schemas
- [x] Add Product Intelligence detail/history schemas
- [x] Add Product-native normalized fields and focused query methods
- [x] Add projection latest-by-Product and enrichment-existence queries
- [x] Add scoped catalog and score-history cursor handling
- [x] Add bounded summary, search, and intelligence-read services
- [x] Add all four read-only routes and dependencies
- [x] Add controlled exceptions, handlers, and safe structured logging
- [x] Extend DynamoDB Local table definitions with deliberate indexes

## Testing

- [x] Cover supported and unsupported filter plans and normalization
- [x] Cover category/status and name-prefix repository queries without scans
- [x] Cover plan/filter cursor isolation and malformed score cursors
- [x] Cover current, stale, and missing summary artifacts
- [x] Cover explicit score ownership and history
- [x] Cover API validation, compact/rich responses, request IDs, and safe errors
- [x] Cover Product derived-field maintenance and local table definitions

## Documentation

- [x] Add catalog-search and quality-read architecture documentation
- [x] Add catalog-search and Product Intelligence API documentation
- [x] Update DynamoDB data model, system overview, and README
- [x] Complete the SPEC-036 completion record

## Verification

- [x] Backend: 1,588 passed, 16 skipped; coverage 90.41%
- [x] Ruff lint and formatting check
- [x] Strict mypy
- [x] Frontend tests, lint, formatting check, and build unchanged
- [x] Docker Compose validation
- [x] Git whitespace check
- [x] Confirm no out-of-scope feature was implemented
