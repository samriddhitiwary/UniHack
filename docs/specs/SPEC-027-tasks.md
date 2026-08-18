# SPEC-027 Task Checklist

## Planning

- [x] ✅ Inspect SPEC-022 validation-rule metadata
- [x] ✅ Inspect SPEC-024 normalized-candidate contract
- [x] ✅ Define validation job semantics
- [x] ✅ Define candidate eligibility rules
- [x] ✅ Define validation issue types
- [x] ✅ Define severity model
- [x] ✅ Define numeric range rules
- [x] ✅ Define allowed-value rules
- [x] ✅ Define regex/pattern safety rules
- [x] ✅ Define unit compatibility rules
- [x] ✅ Define persistence model
- [x] ✅ Define controlled failures

## Implementation

- [x] ✅ Add attribute-validation processing job type
- [x] ✅ Add validation domain models
- [x] ✅ Add validation enums
- [x] ✅ Add validation issue model
- [x] ✅ Add type validator
- [x] ✅ Add numeric-range validator
- [x] ✅ Add allowed-value validator
- [x] ✅ Add safe pattern validator
- [x] ✅ Add unit compatibility validator
- [x] ✅ Add validation engine
- [x] ✅ Add validation result repository protocol
- [x] ✅ Add DynamoDB validation repository
- [x] ✅ Add orchestration service
- [x] ✅ Add job RUNNING transition
- [x] ✅ Add job COMPLETED transition
- [x] ✅ Add job FAILED transition
- [x] ✅ Add resultReference handling
- [x] ✅ Extend local DynamoDB table creation
- [x] ✅ Add controlled exceptions
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add valid motor candidate tests
- [x] ✅ Add invalid efficiency range test
- [x] ✅ Add negative-value test
- [x] ✅ Add phase allowed-value test
- [x] ✅ Add valid IP rating pattern test
- [x] ✅ Add invalid IP rating pattern test
- [x] ✅ Add valid text candidate test
- [x] ✅ Add invalid integer test
- [x] ✅ Add unsupported-unit validation test
- [x] ✅ Add unit-missing validation test
- [x] ✅ Add already-invalid normalization candidate test
- [x] ✅ Add multiple-candidate validation test
- [x] ✅ Add conflicting-candidate preservation test
- [x] ✅ Add issue severity tests
- [x] ✅ Add lineage tests
- [x] ✅ Add persistence tests
- [x] ✅ Add lifecycle tests
- [x] ✅ Add technical failure tests
- [x] ✅ Evaluate optional DynamoDB Local contract test (not added; unit contracts selected)

## Documentation

- [x] ✅ Add attribute-validation architecture documentation
- [x] ✅ Update DynamoDB data model
- [x] ✅ Update system overview
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-027 completion record

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
