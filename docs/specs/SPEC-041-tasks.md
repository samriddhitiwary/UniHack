# SPEC-041 Task Checklist

## Discovery
- [x] ✅ Inspect official input dataset
- [x] ✅ Inspect expected-output workbook
- [x] ✅ Record all sheets
- [x] ✅ Record exact input headers
- [x] ✅ Record exact output headers
- [x] ✅ Record exact output header order
- [x] ✅ Determine labelled row availability
- [x] ✅ Determine input/output row alignment key
- [x] ✅ Document missing-data patterns
- [x] ✅ Document placeholder patterns
- [x] ✅ Create challenge data profile

## Input Foundation
- [x] ✅ Add challenge input-row model
- [x] ✅ Add input dataset parser
- [x] ✅ Preserve Mfg_Part_Num exactly
- [x] ✅ Preserve Part_Desc exactly
- [x] ✅ Add placeholder cleansing
- [x] ✅ Add Part_Manuf parser
- [x] ✅ Add brand-evidence extraction
- [x] ✅ Add row-level source identity

## Output Foundation
- [x] ✅ Add exact delivery-schema contract
- [x] ✅ Preserve every official header exactly
- [x] ✅ Preserve official header order
- [x] ✅ Add delivery-record domain model
- [x] ✅ Add safe blank/default semantics
- [x] ✅ Add schema validation
- [x] ✅ Add output-template validation

## Ground Truth
- [x] ✅ Add labelled-output parser if available
- [x] ✅ Add input-output alignment
- [x] ✅ Add field-level ground-truth representation
- [x] ✅ Add populated/blank field distinction
- [x] ✅ Add reusable evaluation comparison model

## Enrichment Foundation
- [x] ✅ Add field provenance model
- [x] ✅ Add confidence model
- [x] ✅ Add needs-review semantics
- [x] ✅ Add manufacturer-resolution interface
- [x] ✅ Add brand-resolution interface
- [x] ✅ Add classification interface
- [x] ✅ Add attribute-enrichment interface
- [x] ✅ Add external-evidence interface
- [x] ✅ Add non-hallucination enforcement rules

## Testing
- [x] ✅ Test input parsing
- [x] ✅ Test 1,000-row ingestion
- [x] ✅ Test placeholder cleansing
- [x] ✅ Test manufacturer parsing
- [x] ✅ Test brand placeholder handling
- [x] ✅ Test exact schema preservation
- [x] ✅ Test header ordering
- [x] ✅ Test blank-field behavior
- [x] ✅ Test labelled-output ingestion
- [x] ✅ Test row alignment
- [x] ✅ Test provenance
- [x] ✅ Test confidence/review semantics
- [x] ✅ Test malformed input
- [x] ✅ Test missing expected-output header
- [x] ✅ Test no invented reference data

## Documentation
- [x] ✅ Add challenge data profile
- [x] ✅ Add challenge architecture document
- [x] ✅ Update system overview
- [x] ✅ Document assumptions
- [x] ✅ Document unavailable reference data
- [x] ✅ Complete SPEC-041 completion record

## Verification
- [x] ✅ Backend tests
- [x] ✅ Backend coverage >=90%
- [x] ✅ Ruff lint
- [x] ✅ Ruff formatting
- [x] ✅ strict mypy
- [x] ✅ Frontend tests unchanged
- [x] ✅ ESLint
- [x] ✅ Prettier
- [x] ✅ Vite build
- [x] ✅ Docker Compose validation
- [x] ✅ Git whitespace check
- [x] ✅ Confirm no unrelated feature implemented
