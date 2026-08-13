# SPEC-020 — OCR and Nameplate Text Recognition Engine

## Status
Completed

## Objective
Recognize bounded text evidence from stored product images by reusing SPEC-019 analysis regions, persist auditable OCR blocks separately, and update a dedicated OCR job lifecycle.

## User Story
As a later catalog-intelligence stage, I need ordered OCR text, boxes, and engine confidence evidence without classifying the product or inferring attributes.

## Scope
Local on-device OCR, `IMAGE_OCR` job compatibility, SPEC-019 result reuse, in-memory orientation/crops, conservative text normalization and deduplication, deterministic quality/nameplate-text heuristics, composite persistence, lifecycle orchestration, tests, and documentation.

## Out of Scope
Product classification, structured attribute extraction, schema mapping, numeric parsing, unit normalization, conflict detection, LLM/AI cleanup, hosted OCR, APIs, workers, frontend, S3, authentication, authorization, and deployment.

## Functional Requirements
Process only PENDING `IMAGE_OCR` jobs for product-scoped stored IMAGE sources with a compatible completed SPEC-019 result. Reuse its regions, recognize bounded text through a protocol, persist the OCR result before job completion, and safely fail controlled post-start errors.

## Non-Functional Requirements
Backend-only, dependency-injected, immutable evidence, locally runnable without hosted services, no direct filesystem/Boto3/FastAPI access in orchestration, no image/crop writes, no raw engine response, and no float persistence.

## Existing Dependencies
SPEC-019 image metadata/regions/results, processing-job source history and transitions, ProductSourceRepository, ObjectStorage, Pillow, composite DynamoDB patterns, and safe configuration/exceptions/logging.

## OCR Processing Input
A PENDING `IMAGE_OCR` job and matching stored IMAGE source. The service finds the newest completed `IMAGE_ANALYSIS` job for that product/source through the existing source-job query, then retrieves and validates its result.

## OCR Engine Choice
Use `rapidocr-onnxruntime` behind an `OcrEngine` protocol. Tesseract is unavailable in the local environment; RapidOCR is self-contained/on-device and accepts in-memory images without a hosted API or separately installed executable. Construction/import failures map to an explicit unavailable error. Normal tests use a deterministic fake; a real-engine test is opt-in.

## OCR Region Selection
Reuse SPEC-019 regions in `FULL_IMAGE`, `CENTER`, `TOP`, `BOTTOM`, `LEFT`, `RIGHT` order, selecting at most the configured maximum. Always select FULL_IMAGE when allowed; do not perform learned region detection.

## OCR Text Model
Immutable blocks preserve region ID, per-region reading order, conservatively normalized case-sensitive text, integer confidence basis points, and boxes. Nulls and outer/repeated horizontal whitespace are removed while punctuation, units, symbols, decimals, model/serial tokens, and line boundaries remain.

## OCR Bounding-Box Model
Store positive oriented-full-image pixel boxes plus integer 0–10000 relative coordinates. Crop-local engine boxes are translated into the oriented full-image coordinate system and must remain bounded.

## OCR Result Model
An immutable result stores identities, linked analysis, engine/version, oriented dimensions, selected-region/block/duplicate/character counts, average confidence, quality, nameplate-text assessment, ordered blocks, warnings, and UTC creation time.

## Confidence Model
RapidOCR’s local recognition score is converted deterministically to integer basis points from 0 through 10,000. It is OCR-engine confidence only, not business truth.

## Nameplate Text Assessment
Deterministic text-only signals—line count, digits, explicit engineering-unit tokens, label/value punctuation, and model/serial-like tokens—produce `LIKELY_NAMEPLATE_TEXT`, `GENERIC_TEXT`, `NO_TEXT`, or `UNKNOWN` and a 0–100 heuristic score. No category or structured attribute is inferred.

## Result Persistence
Use `{prefix}-image-ocr-results` with `ocrId`/`recordKey`, META and `BLOCK#{index:06d}` records, a sparse JobIdIndex, conditional creation, paginated reconstruction, and a 390,000-byte per-item guard.

## Processing Job Lifecycle
Add `IMAGE_OCR` compatible only with IMAGE. Validate job/source/analysis/duplicate state before start; transition PENDING→RUNNING before object access, persist OCR evidence, then transition RUNNING→COMPLETED at progress 100 with `image-ocr-results/{ocrId}`. Controlled failures attempt RUNNING→FAILED.

## Object Storage Integration
Read through a context-managed `ObjectStorage.open` stream. Decode and orient in memory, compare the current image with SPEC-019 metadata, crop in memory, and never expose paths or write images.

## Safety Limits
Defaults: 6 regions, 5,000 blocks, 500,000 aggregate characters, 10,000 characters per block, and 4,000 minimum-confidence basis points. Limits are validated and never enforced by silent truncation.

## Error Handling
Controlled errors cover invalid jobs/sources, missing analysis, engine unavailable/failure, invalid regions/boxes, region/block/text limits, oversized items, duplicates, serialization, storage, persistence, and completion consistency risk. Stored messages are safe and bounded.

## Logging Requirements
Log safe IDs, engine, bounded counts, basis-point confidence, quality/status/score, and controlled codes. Never log OCR text, bytes, keys, paths, raw responses, or raw errors.

## Security Considerations
Enforce IMAGE-only dedicated jobs, existing validated analysis evidence, bounded in-memory decoding/regions/boxes/text, no shell/remote OCR/LLM, no arbitrary EXIF persistence, no image data in DynamoDB, and no filesystem leakage.

## Edge Cases
No text and weak text complete successfully; overlapping regions may produce exact whitespace-normalized duplicates; rotated/mirrored evidence uses deterministic oriented coordinates; malformed/out-of-bounds engine evidence fails; partial persistence is never treated as complete.

## Acceptance Criteria
All 104 criteria in the controlling amendment must pass with coverage at least 90%, complete repository checks, accurate documentation, and a clean scope audit.

## Test Plan
Use fake-engine fixtures for blocks, multiline text, confidence, boxes, orientation, region reuse, duplicates, limits, quality, heuristics, persistence, lifecycle and failures; add opt-in RapidOCR and DynamoDB Local contracts; run the complete backend/frontend/static/infrastructure suite.

## Implementation Notes
The concrete adapter is local but lazily initialized. Region coordinates originate in SPEC-019’s stored-image space and are mapped to one clearly documented oriented full-image space before OCR evidence is persisted. Analysis lookup uses existing source-job pagination and result lookup, never scan.

## Completion Record
Completed on 2026-08-12. The full backend suite passed with 1,038 tests passed, 9 opt-in tests skipped, and 91.77% coverage. The separately enabled real RapidOCR ONNX generated-image test passed. Ruff lint/format, strict mypy, unchanged frontend test/lint/format/build, Docker Compose validation, and Git whitespace validation passed. All 104 acceptance criteria were audited as passing, and no out-of-scope classification, attribute extraction, normalization, hosted OCR/AI, API, frontend, cloud, authentication, or deployment feature was added.
