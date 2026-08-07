# SPEC-008 — Local Object Storage Foundation

## Status

Completed

## Objective

Create a backend-only object-storage contract and secure local filesystem implementation that future source workflows can use without depending on filesystem paths or a particular cloud provider.

## User Story

As a future product-source service, I need to save, inspect, open, and delete binary objects through a stable abstraction so local development works safely now and an S3 backend can be introduced later without changing application-service contracts.

## Scope

Add an object-storage protocol, immutable stored-object metadata, centralized object-key generation and validation, a local backend with streamed writes and atomic metadata sidecars, controlled storage exceptions, a configuration-driven provider, focused unit tests, and storage documentation.

## Out of Scope

Upload or download APIs, multipart handling, product-source services or DynamoDB writes, S3, presigned or public URLs, content inspection, MIME sniffing, parsing, extraction, OCR, processing jobs, AI, frontend changes, authentication, authorization, deployment, and cleanup workers are excluded.

## Functional Requirements

- Generate platform-independent logical keys in `products/{product_id}/sources/{source_id}/{random_uuid}{extension}` format.
- Accept only `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, and `.csv`, normalized to lowercase; reject empty or unsupported filenames.
- Validate every key and reject absolute paths, drive paths, schemes, backslashes, null bytes, traversal, empty/malformed segments, reserved internal filenames, and keys longer than 1,024 characters.
- Stream a binary input in 256 KiB chunks into a controlled temporary file, enforcing a positive byte limit and computing SHA-256 during the write.
- Permit zero-byte objects when the positive maximum permits them; permit objects exactly at the limit.
- Finalize the object and its UTF-8 strict-JSON metadata sidecar without overwriting an existing object or sidecar.
- Open regular objects as binary streams, check existence, retrieve validated sidecar metadata, and delete an object with its sidecar.
- Create the configured local root on dependency construction and reject roots that are files.

## Non-Functional Requirements

The public contract uses logical object keys and never exposes local paths. The implementation is synchronous, mockable, independent of FastAPI request/response types, bounded-memory, Windows/Linux compatible, safe to construct with temporary roots, and introduces no runtime dependency. Filesystem failures are translated to controlled exceptions with chained causes and path-safe messages.

## Existing Dependencies

SPEC-008 reuses Pydantic Settings, `pathlib`, UUID and UTC conventions, dataclass-based immutable domain objects, standard-library logging, existing storage environment variables, product-source storage metadata terminology, pytest, Ruff, strict mypy, and the ignored root `storage/` runtime areas established by SPEC-001 through SPEC-007.

## Storage Abstraction

`ObjectStorage` defines `save`, `open`, `exists`, `get_metadata`, and `delete`. `save` accepts an object key, a `BinaryIO`, and a positive maximum size and returns `StoredObject`. No method exposes `Path`, FastAPI types, URLs, or provider-specific concepts.

## Local Storage Design

`LocalObjectStorage` resolves and creates its root only when instantiated. Objects live beneath that root at their logical key. Each object has a deterministic `.metadata.json` sidecar containing only its key, size, SHA-256 checksum, and UTC creation time. Object and sidecar writes use random temporary files, exclusive mode-restricted final-name reservations, and atomic replacement in the destination directory, preventing silent replacement without creating filesystem hard links. Failures remove all reservations, temporary files, and partially finalized files created by that save.

## Object-Key Format

Generated keys use `products/{product UUID}/sources/{source UUID}/{random UUID}{approved lowercase extension}` with `/` separators on every platform. The original filename contributes only its validated extension and is never retained in the stored filename.

## File Safety Rules

Keys must be nonblank relative logical paths of at most 1,024 characters. Empty, `.` and `..` segments; leading slash/backslash; drive prefixes; URL schemes; backslashes; null bytes; control characters; repeated separators; trailing separators; sidecar names; and temporary-file markers are rejected. The resolved destination and sidecar must remain beneath the resolved root using `Path.relative_to`, including after parent creation. Directories and symbolic links are not treated as stored objects.

## Configuration

`STORAGE_BACKEND=local` selects `LocalObjectStorage`; `LOCAL_STORAGE_ROOT=../../storage` supplies its root. The root is not created at module import. An unsupported configured backend, including the reserved future value `s3`, raises `ObjectStorageConfigurationError`. Local persistence is development-only and must not be relied upon by future Lambda production deployments.

## Error Handling

`ObjectStorageError` is the safe base error. Specialized errors cover invalid keys, unsupported extensions, duplicates, missing objects, exceeded sizes, malformed/missing metadata, and invalid configuration. Raw filesystem, stream, JSON, and validation errors do not escape the storage boundary; causes remain available through exception chaining, while messages omit absolute paths.

## Logging Requirements

Log concise `object_storage.save_started`, `object_storage.saved`, `object_storage.opened`, `object_storage.deleted`, and `object_storage.failed` events. Logs may contain backend, the first logical key category, byte size, and a short checksum prefix. They must not include object contents, chunks, full object keys, roots, absolute paths, original filenames, credentials, environment values, or unsafe raw exception messages.

## Security Considerations

Validation and resolved containment prevent traversal and absolute-path access. Exclusive finalization prevents overwrites. Stream enforcement prevents oversized persistence, and cleanup prevents partial/temp leakage. Reserved sidecar/temp names cannot be accessed as objects. Regular-file and symlink checks prevent directory or link traversal. Content validation, malware scanning, encryption, and access control remain outside this foundation.

## Edge Cases

Cover zero bytes, exact and one-byte-over limits, duplicate destinations, nested parent creation, stream failures, filesystem failures, missing/malformed/mismatched sidecars, object-size tampering, missing objects, directories, symlinks, unsupported extensions, repeated generated keys, maximum-length keys, Windows-form keys on all hosts, and deletion that never traverses or cascades.

## Acceptance Criteria

All 69 acceptance criteria in the approved SPEC-008 request must pass: required artifacts and contract exist; key generation, key safety, root configuration, streaming, checksums, limits, cleanup, duplicate protection, read/existence/metadata/delete behavior, provider selection, controlled errors, tests, all backend/frontend/Compose/Git quality gates, documentation, completion marking, and the explicit scope audit succeed.

## Test Plan

Add focused tests for every approved extension and key property; unsafe and boundary-length keys; small, empty, exact-limit, oversized, duplicate, nested, broken-stream, and filesystem-failure saves; known checksums; open/existence behavior; valid, missing, malformed, mismatched, and tampered metadata; deletion and outside-root protection; protocol substitutability; local provider construction, root creation/file rejection, caching override behavior, and unsupported backends. Then run the complete backend suite with coverage, Ruff lint/format, strict mypy, unchanged frontend test/lint/format/build, Docker Compose validation, and Git whitespace/scope checks.

## Implementation Notes

Use `app/storage` without adding routes or services. Sidecars use the deterministic suffix `.metadata.json`, camelCase JSON fields, and atomic exclusive finalization. Storage dependency construction remains framework-independent so future FastAPI dependencies and tests can reuse or override it. The existing product-source `storage_key`, size, and checksum fields are not written by SPEC-008.

## Completion Record

Completed on 2026-08-06. Added a provider-independent storage protocol, immutable stored-object metadata, safe generated logical keys, strict key validation, a secure local backend with 256 KiB streaming, positive size limits, single-pass SHA-256, random temporary files, exclusive no-overwrite finalization, strict atomic JSON sidecars, controlled open/existence/metadata/delete behavior, settings-driven construction, safe exceptions/logging, focused tests, and architecture/local-setup documentation. The no-overwrite finalization was subsequently made security-software-friendly by replacing filesystem hard links with exclusive final-name reservations followed by atomic replacement.

Verification passed: 311 backend tests passed with 2 opt-in DynamoDB Local tests skipped and 91.23% coverage; Ruff lint and formatting passed; strict mypy passed across 48 source files; the unchanged frontend passed 1 Vitest test, ESLint, Prettier, and a 1,063-module Vite production build; Docker Compose validation and Git whitespace checks passed. All 69 acceptance criteria passed. No API route, multipart/upload workflow, product-source service or DynamoDB write, S3 implementation, URL, parser/extractor, processing/AI feature, frontend feature, authentication, or deployment feature was added.
