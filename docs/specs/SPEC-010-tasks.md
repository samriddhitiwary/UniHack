# SPEC-010 Task Checklist

## Planning

- [x] ✅ Inspect product-source service conventions
- [x] ✅ Inspect ObjectStorage protocol and local implementation
- [x] ✅ Define multipart request contract
- [x] ✅ Define supported extension and MIME mappings
- [x] ✅ Define file-signature validation rules
- [x] ✅ Define maximum upload-size policy
- [x] ✅ Define storage and persistence compensation flow
- [x] ✅ Define stable upload error codes

## Implementation

- [x] ✅ Add multipart dependency if required
- [x] ✅ Add upload validation constants
- [x] ✅ Add file-type detection utilities
- [x] ✅ Add upload request metadata schema if required
- [x] ✅ Extend product-source service with one file-upload method
- [x] ✅ Add ObjectStorage dependency to source service
- [x] ✅ Add parent-product validation
- [x] ✅ Add secure object-key generation
- [x] ✅ Add streamed save through ObjectStorage
- [x] ✅ Add source metadata construction
- [x] ✅ Add DynamoDB source persistence
- [x] ✅ Add object cleanup after persistence failure
- [x] ✅ Add upload route
- [x] ✅ Add multipart OpenAPI metadata
- [x] ✅ Add controlled exception mappings
- [x] ✅ Add safe structured logging

## Testing

- [x] ✅ Add service test for successful PDF upload
- [x] ✅ Add service test for successful image upload
- [x] ✅ Add service test for successful CSV upload
- [x] ✅ Add service test for missing product
- [x] ✅ Add service test for unsupported extension
- [x] ✅ Add service test for invalid declared MIME type
- [x] ✅ Add service test for signature mismatch
- [x] ✅ Add service test for oversized stream
- [x] ✅ Add service test for storage failure
- [x] ✅ Add service test for repository failure cleanup
- [x] ✅ Add service test for cleanup failure handling
- [x] ✅ Add API test for successful upload
- [x] ✅ Add API test for missing file
- [x] ✅ Add API test for empty filename
- [x] ✅ Add API test for unsupported file type
- [x] ✅ Add API test for invalid product UUID
- [x] ✅ Add API test for missing product
- [x] ✅ Add API test for validation failures
- [x] ✅ Add API test for storage failure
- [x] ✅ Add API test for repository failure
- [x] ✅ Add API test for unexpected failure
- [x] ✅ Verify exact OpenAPI operations
- [x] ✅ Verify no parsing or processing endpoints exist

## Documentation

- [x] ✅ Update product-source API documentation
- [x] ✅ Update object-storage documentation
- [x] ✅ Update local setup documentation
- [x] ✅ Update root README
- [x] ✅ Complete the SPEC-010 completion record

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
- [x] ✅ Confirm no unrelated features were implemented
