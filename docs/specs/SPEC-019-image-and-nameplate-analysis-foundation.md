# SPEC-019 — Image and Nameplate Analysis Foundation

## Status
Completed

## Objective
Validate stored product images, extract privacy-safe metadata, generate deterministic analysis regions, assess pre-OCR nameplate suitability, persist evidence, and update the analysis job.

## User Story
As a future OCR service, I need bounded and auditable image metadata and regions without decoding the same untrusted source blindly.

## Scope
PNG/JPEG/WEBP inspection with Pillow, metadata, EXIF orientation only, geometry regions, deterministic candidate heuristic, limits, composite persistence, lifecycle orchestration, tests, and documentation.

## Out of Scope
OCR, text recognition, object detection, computer vision, AI, classification, attributes, unit normalization, APIs, workers, frontend, S3, authentication, and deployment.

## Functional Requirements
- Process only PENDING IMAGE_ANALYSIS jobs for product-scoped stored IMAGE sources with approved MIME metadata.
- Verify decoded format and animation state, derive bounded metadata, regions, and heuristic output.
- Persist the result before completion and safely fail controlled post-start errors.

## Non-Functional Requirements
Backend-only, dependency-injected, immutable domain evidence, no direct filesystem/Boto3/FastAPI access, no arbitrary EXIF persistence, no float persistence, and no image output.

## Existing Dependencies
IMAGE upload/source validation, job compatibility and transitions, ObjectStorage, Pillow from the current dependency graph, and composite DynamoDB result conventions.

## Image Analysis Input
An IMAGE_ANALYSIS job and matching product-scoped IMAGE source with supported MIME type and logical storage key.

## Supported Image Formats
Exactly PNG/image/png, JPEG/image/jpeg (including .jpg/.jpeg semantics), and WEBP/image/webp. Multi-frame images fail.

## Image Validation
Read bytes with a defensive bound, open/verify using Pillow under its decompression-bomb safeguards, match decoded format to MIME, reject animation/corruption/limits, and never rewrite pixels.

## Image Metadata Model
Immutable format, MIME, width/height, pixel count, aspect numerator/denominator, mode, alpha, grayscale encoding, orientation enum, and actual file bytes.

## Analysis Region Model
Generate FULL_IMAGE, CENTER, TOP, BOTTOM, LEFT, and RIGHT in deterministic order. Store bounded pixel boxes plus 0–10000 basis-point relative coordinates and an integer heuristic score.

## Nameplate Candidate Rules
POSSIBLE requires width at least 300, height at least 150, and aspect between 1:2 and 4:1. UNLIKELY covers width below 150, height below 75, or aspect outside 1:4–8:1. Other cases are UNKNOWN. Score is 0–100 from explicit dimension/aspect factors, never confidence.

## Image Analysis Result Model
Immutable identities, Pillow parser/version, metadata, candidate status/score, ordered regions, warnings, and UTC creation time. No bytes, crops, OCR, or attributes.

## DynamoDB Persistence
Use `{prefix}-image-analysis-results`, `analysisId`/`recordKey`, META and `REGION#{index:06d}`, sparse JobIdIndex, and a 390,000-byte serialized-item guard.

## Processing Job Lifecycle
Validate before start, transition PENDING to RUNNING before ObjectStorage.open, persist the result, then transition to COMPLETED with progress 100 and `image-analysis-results/{analysisId}`. Controlled failures attempt FAILED.

## Object Storage Integration
Use a context-managed binary stream from ObjectStorage only. No path, temp file, crop, or output write.

## Safety Limits
Defaults: 10,485,760 file bytes, width 12,000, height 12,000, 80,000,000 pixels, and 16 regions. All are positive; no resize/truncation.

## Error Handling
Invalid setup fails before RUNNING. Missing/storage/decode/format/animation/limit/region/persistence failures have controlled safe codes. Completion failure preserves the result and logs consistency risk.

## Logging Requirements
Log safe IDs, format, dimensions, pixels, mode, region count, status, score, and controlled codes. Never log bytes, keys, paths, filenames, EXIF, or raw exceptions.

## Security Considerations
Strict formats/MIME, bounded reads/dimensions/pixels/regions, preserved Pillow bomb protection, no arbitrary EXIF, floats, writes, shell, OCR, AI, or code execution.

## Edge Cases
Corrupt/mismatched/animated inputs, grayscale/alpha modes, EXIF rotations/mirroring, tiny/odd dimensions, duplicate geometric boxes, unsupported MIME, incomplete persistence, and completion consistency risk.

## Acceptance Criteria
All 100 criteria in the controlling amendment must pass with coverage at least 90%, full checks, documentation, and scope audit.

## Test Plan
Generate tiny PNG/JPEG/WEBP/animated fixtures; test formats, metadata, orientation, corruption, all limits, regions, heuristic statuses, immutability, serialization, repository reconstruction, lifecycle/failures, and optional DynamoDB Local; then run all repository checks.

## Implementation Notes
Aspect ratio is stored as width/height integers. Relative coordinates use basis points. Grayscale means grayscale-encoded mode only. The nameplate output is geometry/metadata suitability, not recognition.

## Completion Record
Completed on 2026-08-12. The full backend suite passed with 951 tests passed, 7 opt-in DynamoDB Local tests skipped, and 92.31% coverage. Ruff lint/format, strict mypy, unchanged frontend test/lint/format/build, Docker Compose validation, and Git whitespace validation passed. All 100 acceptance criteria were audited as passing, and no out-of-scope OCR, AI, API, frontend, cloud, authentication, or deployment feature was added.
