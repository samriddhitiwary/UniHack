# SPEC-010 — Product Source API: Local File Upload

## Status

Completed

## Objective

Allow one supported file to be attached to an existing product through validated multipart input, streamed object storage, and matching DynamoDB source metadata.

## User Story

As an API client, I need to upload one PDF, image, or CSV source so its bytes are stored safely and its verified metadata is ready for future processing.

## Scope

Add one multipart POST endpoint, configuration-driven per-type limits, filename/MIME/signature validation, transport-neutral stream inspection, storage integration, source persistence with compensation cleanup, safe errors, tests, and documentation.

## Out of Scope

Source read/list/update/delete, batch upload, S3, URLs, parsing, extraction, OCR, image analysis, processing, AI, frontend, authentication, authorization, and deployment are excluded.

## Functional Requirements

- Implement only `POST /api/v1/products/{product_id}/sources/upload` with required `file` and optional `displayName` multipart fields.
- Support PDF, PNG, JPEG, WEBP, and CSV with approved extension/MIME combinations and content checks.
- Verify the parent before validation/storage, generate a secure key with the source's generated ID, stream through `ObjectStorage`, persist returned size/checksum, and return a `READY` source with HTTP 201.
- Delete the stored object after any source-repository failure while preserving the original error.

## Non-Functional Requirements

The service has no FastAPI, Boto3, or filesystem calls. The route has no validation, key, storage, or persistence workflow. Inspection is prefix-bounded and loses no bytes. Existing APIs and CORS remain unchanged.

## Existing Dependencies

Reuse the product/source repositories, `ProductSource` factory, object-storage protocol/provider, secure key generator, public record schema, global envelopes, request IDs, logging, and FastAPI conventions from SPEC-001–009. Add only `python-multipart` for multipart parsing.

## Supported File Types

`.pdf`/`application/pdf` maps to PDF; `.png`/`image/png`, `.jpg` or `.jpeg`/`image/jpeg`, and `.webp`/`image/webp` map to IMAGE; `.csv` with `text/csv`, `application/csv`, or `application/vnd.ms-excel` maps to CSV.

## Multipart API Contract

The endpoint requires one binary `file` with a nonblank filename and declared MIME type. `displayName` is optional and uses the 200-character domain limit. Technical metadata is server-managed.

## Validation Pipeline

After parent validation, normalize the basename and lowercase extension, reject null/blank/overlong/unsupported names, normalize the MIME without parameters, require extension agreement, then inspect at most 4 KiB. Require `%PDF-`, the PNG signature, JPEG `FF D8 FF`, or `RIFF....WEBP`. CSV must be nonempty, null-free, valid UTF-8, and free of disallowed control bytes. Restore seekable streams or prepend the sample for non-seekable streams.

## Service-Layer Design

Extend `ProductSourceService` with `create_file_source`, accepting only `BinaryIO`, filename, MIME, display name, and product UUID. It validates the parent, validates the file, creates a provisional domain source to obtain its ID, generates the key, saves with the configured type limit, replaces metadata/status immutably, persists, compensates on failure, and returns the record.

## Object Storage Integration

Depend only on `ObjectStorage`. Call `save` once with the inspected/restored stream and configured limit. Use its returned key, actual byte size, and SHA-256. Never expose or construct local paths.

## Product Source Persistence

Persist mapped PDF/IMAGE/CSV type, `READY`, normalized filename/MIME/display name, stored key/size/checksum, null text/error, generated identity/timestamps, and version 1.

## Cleanup and Compensation

If repository creation raises any exception after storage, attempt `ObjectStorage.delete`. Preserve the original exception even if cleanup fails, and log cleanup outcomes without paths or keys. This is compensating cleanup, not a distributed transaction.

## Dependency Injection

The existing source-service provider receives the existing object-storage dependency plus validated settings and constructs one immutable per-type limit object. All dependencies remain overridable.

## Error Handling

Map unsupported types, MIME mismatches, and invalid content to distinct safe 422 codes; size overflow to `PRODUCT_SOURCE_FILE_TOO_LARGE`/413; other storage errors to `OBJECT_STORAGE_UNAVAILABLE`/503. Retain existing 404, 409, repository 503, validation 422, and unexpected 500 mappings.

## Logging Requirements

Log safe requested/validated/saved/created/cleanup/failed events with IDs, type, extension, size, and display-name presence only. Never log content, samples, filenames, full keys/checksums, paths, bodies, tables, or credentials.

## Security Considerations

Enforce UUID, basename normalization, allowlists, binary signatures/text sampling, streamed limits, secure random keys, server-owned metadata, no whole-file buffering, no direct paths, cleanup, no execution/extraction, unchanged CORS, and no public URL. Checks do not claim malware scanning or full format authenticity.

## Edge Cases

Cover fake paths, uppercase extensions/MIME parameters, empty names/files/CSV, binary CSV, nonseekable streams, exact/over limits, missing parents, validation before storage, storage failure, controlled/duplicate/unexpected persistence failures, cleanup failure, and no byte loss.

## Acceptance Criteria

All 80 approved criteria must pass, including exact endpoint/OpenAPI scope, supported mappings, validation, streaming/limits, safe metadata, compensation, error mapping, tests, all quality gates, documentation, and scope audit.

## Test Plan

Add unit tests for every format and invalid signature/MIME/name/CSV case, stream restoration and limits, service ordering/metadata/storage/compensation, dependency wiring, multipart API errors/success, temporary local-storage persistence/cleanup, and exact OpenAPI paths. Run full backend coverage, Ruff, mypy, unchanged frontend checks/build, Compose, and Git audits.

## Implementation Notes

Use a small `utils/file_validation.py` module and standard-library checks. Empty uploads are rejected by signature/content validation. The route closes the underlying upload stream in `finally`. No content parser or storage implementation is added.

## Completion Record

Completed on 2026-08-07. Added multipart parsing, per-type byte limits, bounded filename/MIME/signature validation, non-seekable stream replay, transport-neutral service orchestration, secure key generation, streamed object storage, `READY` source metadata persistence, compensating cleanup, safe exception mappings/logging, focused tests, local-storage integration coverage, and documentation.

Verification passed: 387 backend tests passed with 2 opt-in DynamoDB Local tests skipped and 91.91% coverage; Ruff lint and formatting passed; strict mypy passed across 52 source files; the unchanged frontend passed 1 Vitest test, ESLint, Prettier, and a 1,063-module Vite build; Docker Compose, Git whitespace, scope, filesystem-link-reference, and direct OpenAPI audits passed. All 80 acceptance criteria passed. OpenAPI contains exactly the text and upload source POST operations, with no source GET/PATCH/DELETE, batch, parsing, or processing operation.
