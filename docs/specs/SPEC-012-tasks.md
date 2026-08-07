# SPEC-012 Task Checklist

## Planning

- [x] ✅ Inspect existing source update repository contract
- [x] ✅ Inspect SPEC-005 partial-update semantics
- [x] ✅ Define source update request schema
- [x] ✅ Finalize editable fields
- [x] ✅ Finalize immutable fields
- [x] ✅ Finalize explicit-null semantics
- [x] ✅ Finalize status-transition rules
- [x] ✅ Finalize stale-version behaviour
- [x] ✅ Finalize source-not-found and cross-product behaviour

## Implementation

- [x] ✅ Add or refine source update request schema
- [x] ✅ Add status-transition validation
- [x] ✅ Extend product-source service with one update method
- [x] ✅ Add parent-product validation
- [x] ✅ Add product-scoped source retrieval
- [x] ✅ Add partial merge behaviour
- [x] ✅ Add optimistic concurrency
- [x] ✅ Preserve immutable source fields
- [x] ✅ Add PATCH route
- [x] ✅ Register OpenAPI metadata
- [x] ✅ Add safe structured logging
- [x] ✅ Add required exception mapping if missing

## Testing

- [x] ✅ Add schema tests for valid partial updates
- [x] ✅ Add schema tests for required version
- [x] ✅ Add schema tests for invalid version
- [x] ✅ Add schema tests for immutable-field rejection
- [x] ✅ Add schema tests for explicit null
- [x] ✅ Add transition tests
- [x] ✅ Add service test for display-name update
- [x] ✅ Add service test for status update
- [x] ✅ Add service test for error-message update
- [x] ✅ Add service test for multiple-field update
- [x] ✅ Add service test for same-value update
- [x] ✅ Add service test for missing product
- [x] ✅ Add service test for missing source
- [x] ✅ Add service test for cross-product source
- [x] ✅ Add service test for stale version
- [x] ✅ Add service test for repository failure
- [x] ✅ Add API test for successful PATCH
- [x] ✅ Add API test for no-op request
- [x] ✅ Add API test for explicit null clearing
- [x] ✅ Add API test for invalid transition
- [x] ✅ Add API test for immutable fields
- [x] ✅ Add API test for invalid UUIDs
- [x] ✅ Add API test for stale version
- [x] ✅ Add API test for repository failures
- [x] ✅ Add API test for unexpected failure
- [x] ✅ Verify OpenAPI scope

## Documentation

- [x] ✅ Update product-source API documentation
- [x] ✅ Update system architecture documentation if required
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-012 completion record

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
