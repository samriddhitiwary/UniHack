# SPEC-015 Task Checklist

## Planning

- [x] ✅ Inspect processing-job repository contracts
- [x] ✅ Define create-job service contract
- [x] ✅ Define retrieve-job service contract
- [x] ✅ Define product-list service contract
- [x] ✅ Define source-list service contract
- [x] ✅ Finalize supported job-type rules
- [x] ✅ Finalize parent product/source validation
- [x] ✅ Finalize pagination contracts
- [x] ✅ Finalize stable error mappings

## Implementation

- [x] ✅ Add create-job request schema if required
- [x] ✅ Add processing-job application service
- [x] ✅ Add repository dependency provider
- [x] ✅ Add service dependency provider
- [x] ✅ Add product validation
- [x] ✅ Add product-scoped source validation
- [x] ✅ Add create-job workflow
- [x] ✅ Add retrieve-job workflow
- [x] ✅ Add product-list workflow
- [x] ✅ Add source-list workflow
- [x] ✅ Add create route
- [x] ✅ Add retrieve route
- [x] ✅ Add product-list route
- [x] ✅ Add source-list route
- [x] ✅ Register OpenAPI metadata
- [x] ✅ Add safe structured logging
- [x] ✅ Add required exception mappings

## Testing

- [x] ✅ Add service test for successful create
- [x] ✅ Add service test for missing product
- [x] ✅ Add service test for missing source
- [x] ✅ Add service test for cross-product source
- [x] ✅ Add service test for unsupported job type
- [x] ✅ Add service test for duplicate create
- [x] ✅ Add service test for successful retrieve
- [x] ✅ Add service test for missing job
- [x] ✅ Add service test for successful product list
- [x] ✅ Add service test for successful source list
- [x] ✅ Add service test for pagination
- [x] ✅ Add API test for successful create
- [x] ✅ Add API test for invalid UUIDs
- [x] ✅ Add API test for missing product/source
- [x] ✅ Add API test for unsupported job type
- [x] ✅ Add API test for successful retrieve
- [x] ✅ Add API test for missing job
- [x] ✅ Add API test for product-list pagination
- [x] ✅ Add API test for source-list pagination
- [x] ✅ Add API test for malformed cursors
- [x] ✅ Add API test for repository failures
- [x] ✅ Add API test for unexpected failures
- [x] ✅ Verify exact OpenAPI operations
- [x] ✅ Verify no update/start/cancel endpoints exist

## Documentation

- [x] ✅ Add processing-job API documentation
- [x] ✅ Update system architecture documentation
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-015 completion record

## Verification

- [x] ✅ Run backend tests
- [x] ✅ Run backend coverage
- [x] ✅ Run Ruff lint
- [x] ✅ Run Ruff formatting check
- [x] ✅ Run strict mypy
- [x] ✅ Run frontend tests unchanged
- [x] ✅ Run frontend lint
- [x] ✅ Run frontend formatting check
- [x] ✅ Run frontend production build
- [x] ✅ Run Docker Compose validation
- [x] ✅ Run Git whitespace check
- [x] ✅ Confirm no unrelated feature was implemented
