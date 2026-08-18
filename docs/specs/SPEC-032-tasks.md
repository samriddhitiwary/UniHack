# SPEC-032 Task Checklist

## Planning

- [x] ✅ Inspect Product status/version semantics
- [x] ✅ Inspect SPEC-031 projection contract
- [x] ✅ Define readiness-application rules
- [x] ✅ Define projection Product-version safety
- [x] ✅ Define optimistic concurrency behavior
- [x] ✅ Define catalog read API
- [x] ✅ Define readiness read API
- [x] ✅ Define controlled failures

## Implementation

- [x] ✅ Add readiness application service
- [x] ✅ Add readiness application request schema
- [x] ✅ Add catalog projection response schemas
- [x] ✅ Add readiness response schemas
- [x] ✅ Add catalog/readiness routes
- [x] ✅ Add apply-readiness endpoint
- [x] ✅ Add catalog projection endpoint
- [x] ✅ Add readiness endpoint
- [x] ✅ Add Product conditional status update
- [x] ✅ Add controlled exceptions
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add READY application test
- [x] ✅ Add READY_WITH_WARNINGS application test
- [x] ✅ Add BLOCKED rejection test
- [x] ✅ Add stale Product version test
- [x] ✅ Add stale projection Product snapshot test
- [x] ✅ Add wrong-product projection test
- [x] ✅ Add already-ready Product test
- [x] ✅ Add terminal/invalid Product status test
- [x] ✅ Add catalog read API test
- [x] ✅ Add readiness read API test
- [x] ✅ Add missing projection test
- [x] ✅ Add request-ID/error-envelope tests
- [x] ✅ Add serialization tests
- [x] ✅ Add repository/service tests

## Documentation

- [x] ✅ Add publishing-readiness application architecture docs
- [x] ✅ Update Product lifecycle docs
- [x] ✅ Update API docs
- [x] ✅ Update system overview
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-032 completion record

## Verification

- [x] ✅ Run backend tests
- [x] ✅ Run backend coverage
- [x] ✅ Run Ruff lint
- [x] ✅ Run Ruff formatting check
- [x] ✅ Run strict mypy
- [x] ✅ Run frontend tests unchanged
- [x] ✅ Run frontend lint
- [x] ✅ Run frontend formatting check
- [x] ✅ Run frontend build
- [x] ✅ Run Docker Compose validation
- [x] ✅ Run Git whitespace check
- [x] ✅ Confirm no unrelated feature was implemented
