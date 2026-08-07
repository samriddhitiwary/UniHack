# SPEC-011 Task Checklist

## Planning

- [x] ✅ Inspect product-source repository list and retrieve contracts
- [x] ✅ Inspect scoped cursor implementation
- [x] ✅ Define list service contract
- [x] ✅ Define retrieve service contract
- [x] ✅ Finalize parent-product validation behaviour
- [x] ✅ Finalize product-scoped missing-source behaviour
- [x] ✅ Finalize pagination request and response contract
- [x] ✅ Decide whether filters are allowed without scans or new indexes
- [x] ✅ Finalize stable error mappings

## Implementation

- [x] ✅ Extend product-source service with list method
- [x] ✅ Extend product-source service with retrieve method
- [x] ✅ Add parent-product existence validation
- [x] ✅ Add product-scoped source retrieval
- [x] ✅ Add source-list request validation
- [x] ✅ Add source-list response handling
- [x] ✅ Add list route
- [x] ✅ Add retrieve route
- [x] ✅ Register OpenAPI metadata
- [x] ✅ Add safe structured logging
- [x] ✅ Add or refine exception mappings if required

## Testing

- [x] ✅ Add service test for successful listing
- [x] ✅ Add service test for newest-first repository result
- [x] ✅ Add service test for next cursor
- [x] ✅ Add service test for missing product during listing
- [x] ✅ Add service test for product repository failure during listing
- [x] ✅ Add service test for source repository failure during listing
- [x] ✅ Add service test for successful retrieval
- [x] ✅ Add service test for missing source
- [x] ✅ Add service test for wrong-product source isolation
- [x] ✅ Add service test for missing product during retrieval
- [x] ✅ Add API test for successful list
- [x] ✅ Add API test for empty list
- [x] ✅ Add API test for list pagination
- [x] ✅ Add API test for invalid list limit
- [x] ✅ Add API test for malformed cursor
- [x] ✅ Add API test for cursor/product mismatch
- [x] ✅ Add API test for successful retrieve
- [x] ✅ Add API test for missing source
- [x] ✅ Add API test for invalid product UUID
- [x] ✅ Add API test for invalid source UUID
- [x] ✅ Add API test for missing product
- [x] ✅ Add API test for repository failures
- [x] ✅ Add API test for unexpected failures
- [x] ✅ Verify exact OpenAPI operations
- [x] ✅ Verify no download or mutation routes exist

## Documentation

- [x] ✅ Update product-source API documentation
- [x] ✅ Update system architecture documentation if required
- [x] ✅ Update root README
- [x] ✅ Complete the SPEC-011 completion record

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
- [x] ✅ Confirm no unrelated features were implemented
