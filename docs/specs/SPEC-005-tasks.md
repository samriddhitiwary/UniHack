# SPEC-005 Task Checklist

## Planning

- [x] ✅ Inspect the existing ProductUpdate schema
- [x] ✅ Inspect domain immutability and update helpers
- [x] ✅ Inspect repository optimistic-concurrency behaviour
- [x] ✅ Define update service contract
- [x] ✅ Finalize PATCH request contract
- [x] ✅ Finalize stale-version error mapping
- [x] ✅ Finalize immutable-field protections

## Implementation

- [x] ✅ Add or refine update request schema
- [x] ✅ Add update-product service method
- [x] ✅ Add partial-update merge logic
- [x] ✅ Preserve immutable system fields
- [x] ✅ Add update-product route
- [x] ✅ Add optimistic version requirement
- [x] ✅ Register OpenAPI metadata
- [x] ✅ Add safe structured logging
- [x] ✅ Add any required exception mapping

## Testing

- [x] ✅ Add service tests for successful partial update
- [x] ✅ Add service tests for multiple-field update
- [x] ✅ Add service tests for no-op update
- [x] ✅ Add service tests for missing product
- [x] ✅ Add service tests for stale version
- [x] ✅ Add API tests for successful update
- [x] ✅ Add API tests for individual editable fields
- [x] ✅ Add API tests for multiple editable fields
- [x] ✅ Add API tests for immutable fields
- [x] ✅ Add API tests for missing version
- [x] ✅ Add API tests for invalid version
- [x] ✅ Add API tests for stale version
- [x] ✅ Add API tests for missing product
- [x] ✅ Add API tests for request validation
- [x] ✅ Add repository-failure tests
- [x] ✅ Verify exact OpenAPI operations

## Documentation

- [x] ✅ Update product API documentation
- [x] ✅ Update README endpoint section
- [x] ✅ Update architecture documentation if required
- [x] ✅ Complete the SPEC-005 completion record

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
- [x] ✅ Run Git whitespace check
- [x] ✅ Confirm no unrelated features were implemented
