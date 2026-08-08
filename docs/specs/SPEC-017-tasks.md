# SPEC-017 Task Checklist

## Planning

- [x] ✅ Inspect SPEC-016 extraction architecture
- [x] ✅ Inspect processing-job lifecycle rules
- [x] ✅ Select PDF table extraction approach
- [x] ✅ Define table/cell evidence model
- [x] ✅ Define table quality statuses
- [x] ✅ Define scalable table-result persistence
- [x] ✅ Define extraction safety limits
- [x] ✅ Define job failure behaviour

## Implementation

- [x] ✅ Add or configure table extraction dependency
- [x] ✅ Add table extraction domain models
- [x] ✅ Add table quality enum
- [x] ✅ Add table result schemas
- [x] ✅ Add repository protocol
- [x] ✅ Add DynamoDB table-result repository
- [x] ✅ Add PDF table parser
- [x] ✅ Add normalization rules
- [x] ✅ Add safety-limit enforcement
- [x] ✅ Add table extraction service
- [x] ✅ Add job RUNNING transition
- [x] ✅ Add job COMPLETED transition
- [x] ✅ Add job FAILED transition
- [x] ✅ Add resultReference handling
- [x] ✅ Extend local DynamoDB table creation if needed
- [x] ✅ Add controlled exceptions
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add single-table extraction test
- [x] ✅ Add multi-table same-page test
- [x] ✅ Add multi-page table test
- [x] ✅ Add table-order preservation test
- [x] ✅ Add row/column preservation test
- [x] ✅ Add blank-cell test
- [x] ✅ Add no-table PDF test
- [x] ✅ Add malformed/corrupt PDF test
- [x] ✅ Add non-PDF source rejection test
- [x] ✅ Add wrong-job-type rejection test
- [x] ✅ Add table-count limit test
- [x] ✅ Add row-count limit test
- [x] ✅ Add column-count limit test
- [x] ✅ Add cell-count limit test
- [x] ✅ Add result persistence tests
- [x] ✅ Add processing-job lifecycle tests
- [x] ✅ Add repository/storage failure tests
- [x] ✅ Add optional DynamoDB Local contract test

## Documentation

- [x] ✅ Add PDF table extraction architecture document
- [x] ✅ Update DynamoDB data model
- [x] ✅ Update system overview
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-017 completion record

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
