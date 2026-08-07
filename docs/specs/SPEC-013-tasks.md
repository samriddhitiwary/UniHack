# SPEC-013 Task Checklist

## Planning

- [x] ✅ Inspect source conditional-delete repository behaviour
- [x] ✅ Inspect ObjectStorage delete behaviour
- [x] ✅ Define delete service contract
- [x] ✅ Define required version query contract
- [x] ✅ Finalize file-backed versus text-source behaviour
- [x] ✅ Finalize delete ordering strategy
- [x] ✅ Finalize failure consistency behaviour
- [x] ✅ Finalize stable error mappings

## Implementation

- [x] ✅ Extend source service with one delete method
- [x] ✅ Add parent-product validation
- [x] ✅ Add product-scoped source retrieval
- [x] ✅ Add optimistic version requirement
- [x] ✅ Add file-backed object deletion
- [x] ✅ Skip storage for text sources
- [x] ✅ Add source metadata conditional deletion
- [x] ✅ Add safe failure handling
- [x] ✅ Add DELETE route
- [x] ✅ Register OpenAPI metadata
- [x] ✅ Add safe structured logging
- [x] ✅ Add or refine exception mappings if required

## Testing

- [x] ✅ Add service test for deleting text source
- [x] ✅ Add service test for deleting PDF source
- [x] ✅ Add service test for deleting image source
- [x] ✅ Add service test for deleting CSV source
- [x] ✅ Add service test for missing product
- [x] ✅ Add service test for missing source
- [x] ✅ Add service test for cross-product source
- [x] ✅ Add service test for stale version
- [x] ✅ Add service test for storage delete failure
- [x] ✅ Add service test for source repository failure
- [x] ✅ Add service test for unexpected failure
- [x] ✅ Add API test for successful 204
- [x] ✅ Add API test for empty response body
- [x] ✅ Add API test for missing version
- [x] ✅ Add API test for invalid version
- [x] ✅ Add API test for invalid product UUID
- [x] ✅ Add API test for invalid source UUID
- [x] ✅ Add API test for missing product
- [x] ✅ Add API test for missing source
- [x] ✅ Add API test for stale version
- [x] ✅ Add API test for storage failure
- [x] ✅ Add API test for repository failure
- [x] ✅ Add local-storage integration test
- [x] ✅ Verify exact OpenAPI operations
- [x] ✅ Verify no bulk-delete or restore endpoints exist

## Documentation

- [x] ✅ Update product-source API documentation
- [x] ✅ Update object-storage documentation if required
- [x] ✅ Update system architecture documentation if required
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-013 completion record

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
