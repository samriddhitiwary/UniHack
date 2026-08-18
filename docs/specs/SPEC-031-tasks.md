# SPEC-031 — Task Checklist

## Planning

- [x] ✅ Read SPEC-031 completely
- [x] ✅ Confirm SPEC-030 materialization input contract
- [x] ✅ Confirm Product identity input contract
- [x] ✅ Confirm processing-job lifecycle contract
- [x] ✅ Confirm DynamoDB repository conventions
- [x] ✅ Define immutable catalog projection boundary
- [x] ✅ Define readiness status precedence
- [x] ✅ Define blocking reason precedence
- [x] ✅ Define warning reason precedence
- [x] ✅ Define idempotency boundary
- [x] ✅ Define persistence access patterns
- [x] ✅ Confirm out-of-scope behavior

## Implementation

- [x] ✅ Add catalog-projection processing job type
- [x] ✅ Add catalog projection domain models
- [x] ✅ Add readiness enums
- [x] ✅ Add blocking/warning reason enums
- [x] ✅ Add product identity projector
- [x] ✅ Add reviewed attribute projector
- [x] ✅ Add publishing readiness evaluator
- [x] ✅ Add catalog projection engine
- [x] ✅ Add result repository protocol
- [x] ✅ Add DynamoDB catalog projection repository
- [x] ✅ Add orchestration service
- [x] ✅ Add job RUNNING transition
- [x] ✅ Add job COMPLETED transition
- [x] ✅ Add job FAILED transition
- [x] ✅ Add resultReference handling
- [x] ✅ Extend local DynamoDB table creation
- [x] ✅ Add controlled exceptions
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add fully ready motor projection test
- [x] ✅ Add fully ready pump projection test
- [x] ✅ Add missing core product name test
- [x] ✅ Add unclassified category rejection test
- [x] ✅ Add missing reviewed materialization test
- [x] ✅ Add optional unresolved attribute test
- [x] ✅ Add manual-override projection test
- [x] ✅ Add warning-preservation test
- [x] ✅ Add immutable lineage test
- [x] ✅ Add readiness blocking-reason tests
- [x] ✅ Add readiness warning tests
- [x] ✅ Add stable attribute ordering test
- [x] ✅ Add idempotency tests
- [x] ✅ Add persistence tests
- [x] ✅ Add lifecycle tests
- [x] ✅ Add technical failure tests
- [x] ✅ Add optional DynamoDB Local contract test

## Documentation

- [x] ✅ Add catalog-projection architecture documentation
- [x] ✅ Update DynamoDB data model
- [x] ✅ Update processing-job docs
- [x] ✅ Update system overview
- [x] ✅ Update README if required
- [x] ✅ Complete SPEC-031 completion record

## Verification

- [x] ✅ Run focused catalog-projection tests
- [x] ✅ Run full backend test suite
- [x] ✅ Verify backend coverage threshold
- [x] ✅ Run backend lint checks
- [x] ✅ Run backend formatting check
- [x] ✅ Run strict backend type checks
- [x] ✅ Run frontend tests
- [x] ✅ Run frontend lint checks
- [x] ✅ Run frontend formatting check
- [x] ✅ Run frontend production build
- [x] ✅ Validate Docker Compose configuration
- [x] ✅ Run whitespace and scope audit
