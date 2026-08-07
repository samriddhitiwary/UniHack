# SPEC-009 Task Checklist

## Planning

- [x] ✅ Inspect existing product repository and service patterns
- [x] ✅ Inspect product-source domain and repository contracts
- [x] ✅ Define text-source service contract
- [x] ✅ Finalize request and response schemas
- [x] ✅ Finalize product-not-found behaviour
- [x] ✅ Finalize duplicate-source behaviour
- [x] ✅ Finalize source status rule

## Implementation

- [x] ✅ Add text-source request schema if required
- [x] ✅ Add product-source application service
- [x] ✅ Add product-source repository dependency provider
- [x] ✅ Add product-source service dependency provider
- [x] ✅ Add product existence validation
- [x] ✅ Add text-source creation logic
- [x] ✅ Add create-text-source route
- [x] ✅ Register product-source router
- [x] ✅ Add safe structured logging
- [x] ✅ Add required exception mappings

## Testing

- [x] ✅ Add service test for successful creation
- [x] ✅ Add service test for product existence check
- [x] ✅ Add service test for missing product
- [x] ✅ Add service test for normalized text input
- [x] ✅ Add service test for repository duplicate error
- [x] ✅ Add service test for repository failure
- [x] ✅ Add API test for successful creation
- [x] ✅ Add API test for missing product
- [x] ✅ Add API test for blank text
- [x] ✅ Add API test for oversized text
- [x] ✅ Add API test for invalid product UUID
- [x] ✅ Add API test for unknown fields
- [x] ✅ Add API test for client-supplied system fields
- [x] ✅ Add API test for persistence failure
- [x] ✅ Add API test for unexpected failure
- [x] ✅ Verify exact OpenAPI operations
- [x] ✅ Verify no file-upload routes exist

## Documentation

- [x] ✅ Add product-source API documentation
- [x] ✅ Update root README
- [x] ✅ Update system architecture documentation if required
- [x] ✅ Complete the SPEC-009 completion record

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
