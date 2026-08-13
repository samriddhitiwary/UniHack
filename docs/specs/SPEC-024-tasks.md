# SPEC-024 Task Checklist

## Planning

- [x] ✅ Inspect SPEC-023 raw candidate contract
- [x] ✅ Inspect SPEC-022 unit metadata
- [x] ✅ Define normalization job semantics
- [x] ✅ Define canonical numeric representation
- [x] ✅ Define canonical unit policy
- [x] ✅ Define supported conversion dimensions
- [x] ✅ Define text normalization rules
- [x] ✅ Define boolean normalization rules
- [x] ✅ Define enum normalization rules
- [x] ✅ Define precision/rounding policy
- [x] ✅ Define normalization statuses
- [x] ✅ Define persistence model
- [x] ✅ Define controlled failures

## Implementation

- [x] ✅ Add attribute-normalization processing job type
- [x] ✅ Add normalization domain models
- [x] ✅ Add normalization enums
- [x] ✅ Add normalized candidate schemas
- [x] ✅ Add decimal parser
- [x] ✅ Add canonical unit registry
- [x] ✅ Add unit alias matcher
- [x] ✅ Add unit conversion engine
- [x] ✅ Add numeric normalizer
- [x] ✅ Add integer normalizer
- [x] ✅ Add text normalizer
- [x] ✅ Add boolean normalizer
- [x] ✅ Add enum normalizer
- [x] ✅ Add normalization engine
- [x] ✅ Add normalization result repository protocol
- [x] ✅ Add DynamoDB normalization repository
- [x] ✅ Add normalization orchestration service
- [x] ✅ Add job RUNNING transition
- [x] ✅ Add job COMPLETED transition
- [x] ✅ Add job FAILED transition
- [x] ✅ Add resultReference handling
- [x] ✅ Extend local DynamoDB table creation
- [x] ✅ Add controlled exceptions
- [x] ✅ Add structured logging

## Testing

- [x] ✅ Add W to kW conversion test
- [x] ✅ Add hp to kW conversion test
- [x] ✅ Add m3/h normalization test
- [x] ✅ Add L/min to m3/h conversion test
- [x] ✅ Add gpm conversion test
- [x] ✅ Add ft to m conversion test
- [x] ✅ Add psi to bar conversion test
- [x] ✅ Add inch to mm conversion test
- [x] ✅ Add rpm normalization test
- [x] ✅ Add percent normalization test
- [x] ✅ Add voltage/current/frequency normalization tests
- [x] ✅ Add integer normalization tests
- [x] ✅ Add text normalization tests
- [x] ✅ Add boolean normalization tests
- [x] ✅ Add enum normalization tests
- [x] ✅ Add unsupported-unit test
- [x] ✅ Add unitless-number test
- [x] ✅ Add malformed-number test
- [x] ✅ Add precision tests
- [x] ✅ Add conflicting-candidate preservation test
- [x] ✅ Add lineage tests
- [x] ✅ Add persistence tests
- [x] ✅ Add lifecycle tests
- [x] ✅ Add technical failure tests
- [x] ✅ Evaluate optional DynamoDB Local contract test; unit contract used

## Documentation

- [x] ✅ Add normalization architecture documentation
- [x] ✅ Update DynamoDB data model
- [x] ✅ Update system overview
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-024 completion record

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
