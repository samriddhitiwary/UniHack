# SPEC-004 Task Checklist

## Planning

- [x] ✅ Inspect existing repository pagination behaviour
- [x] ✅ Inspect existing cursor utilities
- [x] ✅ Define list-products service contract
- [x] ✅ Finalize query parameter validation
- [x] ✅ Finalize paginated API response contract
- [x] ✅ Finalize error mappings

## Implementation

- [x] ✅ Add list-products service method
- [x] ✅ Add optional status filtering
- [x] ✅ Add bounded limit handling
- [x] ✅ Add cursor handling
- [x] ✅ Add paginated response schema if required
- [x] ✅ Add list-products route
- [x] ✅ Register OpenAPI metadata
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add service tests for unfiltered listing
- [x] ✅ Add service tests for status-filtered listing
- [x] ✅ Add service tests for pagination
- [x] ✅ Add API tests for default listing
- [x] ✅ Add API tests for custom limit
- [x] ✅ Add API tests for status filtering
- [x] ✅ Add API tests for valid cursor pagination
- [x] ✅ Add API tests for malformed cursor
- [x] ✅ Add API tests for invalid limit
- [x] ✅ Add API tests for invalid status
- [x] ✅ Add repository-failure tests
- [x] ✅ Verify exact OpenAPI operations

## Documentation

- [x] ✅ Update product API documentation
- [x] ✅ Update README endpoint section
- [x] ✅ Update architecture documentation if required
- [x] ✅ Complete the SPEC-004 completion record

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
- [x] ✅ Confirm no unrelated features were implemented
