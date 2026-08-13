# SPEC-021 Task Checklist

## Planning

- [x] ✅ Inspect existing ProductCategory enum
- [x] ✅ Inspect all extraction-result repositories
- [x] ✅ Define classification job semantics
- [x] ✅ Define evidence aggregation model
- [x] ✅ Define supported category signals
- [x] ✅ Define deterministic scoring rules
- [x] ✅ Define ambiguity/conflict behaviour
- [x] ✅ Define classification confidence representation
- [x] ✅ Define result persistence
- [x] ✅ Define processing failure codes

## Implementation

- [x] ✅ Add product-level classification job type and persistence semantics
- [x] ✅ Add classification domain models and enums
- [x] ✅ Add classification result schemas
- [x] ✅ Add bounded evidence aggregation service
- [x] ✅ Add deterministic classification engine and rules
- [x] ✅ Add score/confidence and ambiguity/conflict handling
- [x] ✅ Add classification repository protocol and DynamoDB implementation
- [x] ✅ Add classification orchestration and lifecycle service
- [x] ✅ Add resultReference handling and local table creation
- [x] ✅ Add controlled exceptions and structured logging

## Testing

- [x] ✅ Add pump, motor, insufficient, ambiguous, and conflict tests
- [x] ✅ Add all five evidence-source and multi-source tests
- [x] ✅ Add boundary, scoring, confidence, and provenance tests
- [x] ✅ Add evidence/match/item limits
- [x] ✅ Add domain, serialization, and repository tests
- [x] ✅ Add lifecycle and technical-failure tests
- [x] ✅ Add optional DynamoDB Local contract test

## Documentation

- [x] ✅ Add product-classification architecture documentation
- [x] ✅ Update DynamoDB data model and system overview
- [x] ✅ Update processing-job/API and README documentation
- [x] ✅ Complete SPEC-021 completion record

## Verification

- [x] ✅ Run backend tests and coverage
- [x] ✅ Run Ruff lint and formatting check
- [x] ✅ Run strict mypy
- [x] ✅ Run unchanged frontend test/lint/format/build
- [x] ✅ Run Docker Compose and Git whitespace checks
- [x] ✅ Confirm no unrelated feature was implemented
