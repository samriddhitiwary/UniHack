# SPEC-020 Task Checklist

## Planning

- [x] ✅ Inspect SPEC-019 image-analysis contracts
- [x] ✅ Inspect processing-job lifecycle rules
- [x] ✅ Evaluate OCR dependency options
- [x] ✅ Define OCR region-selection policy
- [x] ✅ Define recognized-text evidence model
- [x] ✅ Define OCR bounding-box model
- [x] ✅ Define OCR confidence representation
- [x] ✅ Define no-text behaviour
- [x] ✅ Define nameplate-text heuristic
- [x] ✅ Define safety limits
- [x] ✅ Define scalable result persistence
- [x] ✅ Define failure codes

## Implementation

- [x] ✅ Add OCR dependency/configuration
- [x] ✅ Add OCR domain models and enums
- [x] ✅ Add OCR result schemas
- [x] ✅ Add OCR repository protocol and DynamoDB implementation
- [x] ✅ Add local OCR engine adapter and protocol
- [x] ✅ Add in-memory image-region crop and orientation pipeline
- [x] ✅ Add OCR text, bounding-box, and confidence normalization
- [x] ✅ Add conservative duplicate suppression
- [x] ✅ Add OCR quality and deterministic nameplate-text heuristic
- [x] ✅ Add OCR processing service
- [x] ✅ Add RUNNING, COMPLETED, and FAILED lifecycle transitions
- [x] ✅ Add resultReference handling
- [x] ✅ Extend local DynamoDB table creation
- [x] ✅ Add controlled exceptions
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add fake and opt-in real clear-text OCR tests
- [x] ✅ Add multi-line, multi-region, and reading-order tests
- [x] ✅ Add bounding-box and confidence tests
- [x] ✅ Add no-text and low-confidence tests
- [x] ✅ Add conservative duplicate tests
- [x] ✅ Add rotated-orientation and in-memory crop tests
- [x] ✅ Add region, block, text, and item-size limit tests
- [x] ✅ Add domain, schema, serialization, and persistence tests
- [x] ✅ Add lifecycle and storage/OCR/repository failure tests
- [x] ✅ Add optional DynamoDB Local contract test

## Documentation

- [x] ✅ Add OCR architecture documentation
- [x] ✅ Update DynamoDB data model
- [x] ✅ Update image-analysis and system overviews
- [x] ✅ Update processing-job API, local setup, and README
- [x] ✅ Complete SPEC-020 completion record

## Verification

- [x] ✅ Run backend tests and coverage
- [x] ✅ Run Ruff lint and formatting check
- [x] ✅ Run strict mypy
- [x] ✅ Run frontend tests unchanged
- [x] ✅ Run frontend lint and formatting check
- [x] ✅ Run frontend build
- [x] ✅ Run Docker Compose validation
- [x] ✅ Run Git whitespace check
- [x] ✅ Confirm no unrelated feature was implemented
