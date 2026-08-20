# SPEC-037 Task Checklist

## Planning

- [x] ✅ Inspect all existing processing-job types
- [x] ✅ Map stage dependencies
- [x] ✅ Define workflow states
- [x] ✅ Define workflow stage states
- [x] ✅ Define automatic vs optional stages
- [x] ✅ Define human-review checkpoint
- [x] ✅ Define resume semantics
- [x] ✅ Define failure semantics
- [x] ✅ Define retry semantics
- [x] ✅ Define workflow idempotency
- [x] ✅ Define persistence model
- [x] ✅ Define API contract
- [x] ✅ Define progress semantics
- [x] ✅ Define controlled failures

## Implementation

- [x] ✅ Add workflow domain models
- [x] ✅ Add workflow enums
- [x] ✅ Add workflow stage model
- [x] ✅ Add workflow configuration model
- [x] ✅ Add workflow repository protocol
- [x] ✅ Add DynamoDB workflow repository
- [x] ✅ Add stage dependency planner
- [x] ✅ Add workflow state machine
- [x] ✅ Add orchestration engine
- [x] ✅ Add stage execution adapters
- [x] ✅ Add human-review pause handling
- [x] ✅ Add resume logic
- [x] ✅ Add optional export handling
- [x] ✅ Add optional AI enrichment handling
- [x] ✅ Add optional intelligence-score handling
- [x] ✅ Add workflow progress calculation
- [x] ✅ Add workflow result references
- [x] ✅ Add optimistic concurrency
- [x] ✅ Add workflow APIs
- [x] ✅ Add controlled exceptions
- [x] ✅ Add structured logging
- [x] ✅ Extend DynamoDB Local table creation

## Testing

- [x] ✅ Add happy-path workflow test
- [x] ✅ Add text-only product test
- [x] ✅ Add PDF source workflow test
- [x] ✅ Add CSV source workflow test
- [x] ✅ Add image/OCR workflow test
- [x] ✅ Add mixed-source workflow test
- [x] ✅ Add review-required pause test
- [x] ✅ Add resume-after-review test
- [x] ✅ Add already-completed-review resume test
- [x] ✅ Add optional export test
- [x] ✅ Add optional AI enrichment test
- [x] ✅ Add optional intelligence-score test
- [x] ✅ Add failed-stage test
- [x] ✅ Add retry/resume test
- [x] ✅ Add stale workflow version test
- [x] ✅ Add duplicate workflow test
- [x] ✅ Add terminal workflow test
- [x] ✅ Add stage dependency tests
- [x] ✅ Add progress tests
- [x] ✅ Add repository tests
- [x] ✅ Add API tests
- [x] ✅ Add no-duplicate-stage-execution tests
- [x] ✅ Add no-review-bypass test

## Documentation

- [x] ✅ Add workflow architecture documentation
- [x] ✅ Add workflow API documentation
- [x] ✅ Update processing-job architecture docs
- [x] ✅ Update DynamoDB data model
- [x] ✅ Update system overview
- [x] ✅ Update README
- [x] ✅ Complete SPEC-037 completion record

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
- [x] ✅ Confirm no unrelated feature implemented
