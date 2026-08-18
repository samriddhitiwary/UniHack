# SPEC-033 Task Checklist

## Planning

- [x] ✅ Inspect SPEC-031 catalog projection model
- [x] ✅ Inspect SPEC-032 readiness semantics
- [x] ✅ Inspect SPEC-008 object-storage abstraction
- [x] ✅ Define export processing-job semantics
- [x] ✅ Define canonical JSON format
- [x] ✅ Define flat CSV format
- [x] ✅ Define manifest format
- [x] ✅ Define checksum strategy
- [x] ✅ Define artifact naming
- [x] ✅ Define idempotency
- [x] ✅ Define persistence model
- [x] ✅ Define controlled failures

## Implementation

- [x] ✅ Add catalog-export processing job type
- [x] ✅ Add export domain models
- [x] ✅ Add export enums
- [x] ✅ Add canonical JSON serializer
- [x] ✅ Add catalog CSV serializer
- [x] ✅ Add publication manifest serializer
- [x] ✅ Add checksum helper
- [x] ✅ Add export package builder
- [x] ✅ Add result repository protocol
- [x] ✅ Add DynamoDB export repository
- [x] ✅ Add orchestration service
- [x] ✅ Add local object-storage persistence
- [x] ✅ Add rollback/compensation handling
- [x] ✅ Add job RUNNING transition
- [x] ✅ Add job COMPLETED transition
- [x] ✅ Add job FAILED transition
- [x] ✅ Add resultReference
- [x] ✅ Extend DynamoDB Local table creation
- [x] ✅ Add controlled exceptions
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add READY projection export test
- [x] ✅ Add READY_WITH_WARNINGS export test
- [x] ✅ Add BLOCKED projection rejection test
- [x] ✅ Add stale Product/projection policy test
- [x] ✅ Add canonical JSON determinism test
- [x] ✅ Add CSV determinism test
- [x] ✅ Add manifest determinism test
- [x] ✅ Add checksum test
- [x] ✅ Add special-character CSV test
- [x] ✅ Add nullable identity field test
- [x] ✅ Add unitless attribute test
- [x] ✅ Add human override export test
- [x] ✅ Add validation-warning preservation test
- [x] ✅ Add idempotency test
- [x] ✅ Add object-storage failure test
- [x] ✅ Add persistence failure compensation test
- [x] ✅ Add repository tests
- [x] ✅ Add lifecycle tests
- [x] ✅ Add optional DynamoDB Local contract test

## Documentation

- [x] ✅ Add catalog-export architecture documentation
- [x] ✅ Update DynamoDB data model
- [x] ✅ Update processing-job docs
- [x] ✅ Update system overview
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-033 completion record

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
