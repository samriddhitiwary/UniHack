# SPEC-006 Task Checklist

## Planning

- [x] ✅ Inspect existing repository delete behaviour
- [x] ✅ Inspect current product service and route conventions
- [x] ✅ Define delete-product service contract
- [x] ✅ Finalize DELETE request contract
- [x] ✅ Finalize stale-version error behaviour
- [x] ✅ Finalize missing-product behaviour

## Implementation

- [x] ✅ Add delete request schema if required
- [x] ✅ Add delete-product service method
- [x] ✅ Add current-product existence check
- [x] ✅ Add optimistic version requirement
- [x] ✅ Add delete-product route
- [x] ✅ Register OpenAPI metadata
- [x] ✅ Add safe structured logging
- [x] ✅ Add or refine exception mappings if required

## Testing

- [x] ✅ Add service test for successful deletion
- [x] ✅ Add service test for missing product
- [x] ✅ Add service test for stale version
- [x] ✅ Add service test for repository failure
- [x] ✅ Add API test for successful deletion
- [x] ✅ Add API test for missing version
- [x] ✅ Add API test for invalid version
- [x] ✅ Add API test for missing product
- [x] ✅ Add API test for stale version
- [x] ✅ Add API test for repository failure
- [x] ✅ Add API test for unexpected failure
- [x] ✅ Verify 204 response has no body
- [x] ✅ Verify deleted product cannot be retrieved
- [x] ✅ Verify existing endpoints still work
- [x] ✅ Verify exact OpenAPI operations

## Documentation

- [x] ✅ Update product API documentation
- [x] ✅ Update README endpoint section
- [x] ✅ Update architecture documentation if required
- [x] ✅ Complete the SPEC-006 completion record

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
