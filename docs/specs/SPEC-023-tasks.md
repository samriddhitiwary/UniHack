# SPEC-023 Task Checklist

## Planning

- [x] ✅ Inspect SPEC-021 classification result contract
- [x] ✅ Inspect SPEC-022 active schema and alias resolution
- [x] ✅ Define attribute-extraction job semantics
- [x] ✅ Define evidence aggregation contract
- [x] ✅ Define label-matching rules
- [x] ✅ Define raw-value extraction rules
- [x] ✅ Define raw-unit extraction rules
- [x] ✅ Define candidate confidence rules
- [x] ✅ Define duplicate handling
- [x] ✅ Define scalable result persistence
- [x] ✅ Define controlled failure codes

## Implementation

- [x] ✅ Add attribute-extraction processing job type
- [x] ✅ Add extraction domain models
- [x] ✅ Add extraction enums
- [x] ✅ Add candidate/result schemas
- [x] ✅ Add extraction evidence model
- [x] ✅ Add evidence aggregation service
- [x] ✅ Add alias/label matcher
- [x] ✅ Add raw value parser
- [x] ✅ Add raw unit parser
- [x] ✅ Add candidate confidence scorer
- [x] ✅ Add duplicate candidate handling
- [x] ✅ Add extraction result repository protocol
- [x] ✅ Add DynamoDB extraction result repository
- [x] ✅ Add extraction orchestration service
- [x] ✅ Add job RUNNING transition
- [x] ✅ Add job COMPLETED transition
- [x] ✅ Add job FAILED transition
- [x] ✅ Add resultReference handling
- [x] ✅ Extend local DynamoDB table creation
- [x] ✅ Add controlled exceptions
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add induction-motor extraction test
- [x] ✅ Add centrifugal-pump extraction test
- [x] ✅ Add direct-text extraction test
- [x] ✅ Add PDF-text extraction test
- [x] ✅ Add PDF-table extraction test
- [x] ✅ Add CSV extraction test
- [x] ✅ Add OCR extraction test
- [x] ✅ Add alias matching tests
- [x] ✅ Add number extraction tests
- [x] ✅ Add text-value extraction tests
- [x] ✅ Add integer extraction tests
- [x] ✅ Add raw-unit extraction tests
- [x] ✅ Add missing-unit test
- [x] ✅ Add multiple-candidate test
- [x] ✅ Add conflicting-source candidate test
- [x] ✅ Add duplicate-candidate test
- [x] ✅ Add confidence tests
- [x] ✅ Add evidence-provenance tests
- [x] ✅ Add result persistence tests
- [x] ✅ Add lifecycle tests
- [x] ✅ Add technical failure tests
- [x] ✅ Evaluate optional DynamoDB Local test; unit contract used

## Documentation

- [x] ✅ Add structured-attribute extraction architecture documentation
- [x] ✅ Update DynamoDB data model
- [x] ✅ Update system overview
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-023 completion record

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
