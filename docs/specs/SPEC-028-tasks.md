# SPEC-028 Task Checklist

## Planning

- [x] ✅ Inspect SPEC-025 conflict output
- [x] ✅ Inspect SPEC-027 validation output
- [x] ✅ Define selection job semantics
- [x] ✅ Define candidate eligibility rules
- [x] ✅ Define candidate ranking rules
- [x] ✅ Define auto-selection conditions
- [x] ✅ Define review-required conditions
- [x] ✅ Define selection confidence model
- [x] ✅ Define reason codes
- [x] ✅ Define proposed-attribute model
- [x] ✅ Define review-summary model
- [x] ✅ Define persistence
- [x] ✅ Define controlled failures

## Implementation

- [x] ✅ Add attribute-selection processing job type
- [x] ✅ Add selection domain models
- [x] ✅ Add selection enums
- [x] ✅ Add candidate ranking helper
- [x] ✅ Add auto-selection policy
- [x] ✅ Add review-required policy
- [x] ✅ Add selection confidence scorer
- [x] ✅ Add selection reason model
- [x] ✅ Add proposed-attribute result model
- [x] ✅ Add review-summary model
- [x] ✅ Add result repository protocol
- [x] ✅ Add DynamoDB result repository
- [x] ✅ Add orchestration service
- [x] ✅ Add job RUNNING transition
- [x] ✅ Add job COMPLETED transition
- [x] ✅ Add job FAILED transition
- [x] ✅ Add resultReference handling
- [x] ✅ Extend local DynamoDB table creation
- [x] ✅ Add controlled exceptions
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add exact-agreement auto-selection test
- [x] ✅ Add converted-unit agreement auto-selection test
- [x] ✅ Add single-source review test
- [x] ✅ Add tolerance-agreement selection test
- [x] ✅ Add true-conflict review-required test
- [x] ✅ Add invalid-candidate exclusion test
- [x] ✅ Add valid-vs-invalid candidate test
- [x] ✅ Add unsupported-unit exclusion test
- [x] ✅ Add multi-source corroboration test
- [x] ✅ Add same-source repetition test
- [x] ✅ Add no-candidate test
- [x] ✅ Add missing-required review test
- [x] ✅ Add invalid-only review test
- [x] ✅ Add optional attribute test
- [x] ✅ Add ranking determinism test
- [x] ✅ Add selection-confidence tests
- [x] ✅ Add reason-code tests
- [x] ✅ Add lineage tests
- [x] ✅ Add persistence tests
- [x] ✅ Add lifecycle tests
- [x] ✅ Add technical failure tests
- [x] ✅ Evaluate optional DynamoDB Local contract test (unit contract coverage selected)

## Documentation

- [x] ✅ Add candidate-selection architecture documentation
- [x] ✅ Update DynamoDB data model
- [x] ✅ Update system overview
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-028 completion record

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
