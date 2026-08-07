# SPEC-014 Task Checklist

## Planning

- [x] ✅ Inspect existing source repository conventions
- [x] ✅ Inspect DynamoDB table-creation conventions
- [x] ✅ Define processing-job domain fields
- [x] ✅ Define job status enum
- [x] ✅ Define job type enum
- [x] ✅ Define job access patterns
- [x] ✅ Finalize DynamoDB key design
- [x] ✅ Finalize optimistic-concurrency behaviour

## Implementation

- [x] ✅ Add job status enum
- [x] ✅ Add job type enum
- [x] ✅ Add immutable processing-job domain entity
- [x] ✅ Add processing-job schemas
- [x] ✅ Add serialization support
- [x] ✅ Add repository protocol
- [x] ✅ Add DynamoDB repository
- [x] ✅ Add scoped job cursors
- [x] ✅ Extend DynamoDB table-creation script
- [x] ✅ Add processing-job exceptions

## Testing

- [x] ✅ Add domain tests
- [x] ✅ Add schema tests
- [x] ✅ Add serialization tests
- [x] ✅ Add repository create tests
- [x] ✅ Add duplicate-create tests
- [x] ✅ Add retrieve tests
- [x] ✅ Add product-scoped list tests
- [x] ✅ Add source-scoped list tests
- [x] ✅ Add newest-first pagination tests
- [x] ✅ Add status update tests
- [x] ✅ Add optimistic-concurrency tests
- [x] ✅ Add terminal-state tests
- [x] ✅ Confirm delete tests are not applicable because the repository excludes delete
- [x] ✅ Add repository failure tests
- [x] ✅ Add optional DynamoDB Local contract test

## Documentation

- [x] ✅ Update DynamoDB data-model documentation
- [x] ✅ Update system architecture documentation
- [x] ✅ Update README/local table setup documentation
- [x] ✅ Complete SPEC-014 completion record

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
