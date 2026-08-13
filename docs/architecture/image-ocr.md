# OCR and Nameplate Text Recognition Engine

SPEC-020 adds a backend-only, locally runnable OCR phase for stored IMAGE sources. It reuses SPEC-019 metadata and regions, preserves ordered text/box/confidence evidence, and updates a dedicated `IMAGE_OCR` job. It does not classify products or extract structured attributes.

```text
ImageOcrService -> ProcessingJobRepository (source history + lifecycle)
                -> ProductSourceRepository (scoped IMAGE metadata)
                -> ImageAnalysisResultRepository (SPEC-019 regions)
                -> ObjectStorage.open (bounded analyzed bytes)
                -> OcrEngine protocol / RapidOCR ONNX Runtime
                -> ImageOcrResultRepository (META + BLOCK evidence)
```

## Local engine

The concrete adapter uses `rapidocr-onnxruntime` 1.x with its packaged ONNX models. `uv sync --project apps/api --all-groups` installs the Python package, ONNX Runtime, and local model assets; Tesseract and a hosted account/API are not required. Engine construction validates imports and model initialization and returns a controlled unavailable error on failure. Application orchestration depends only on the `OcrEngine` protocol, and ordinary tests use deterministic fakes. Set `RUN_RAPIDOCR_INTEGRATION=1` to opt into the generated-image real-engine test.

No image, OCR text, or metadata is sent to Cloud Vision, Textract, an LLM, or another hosted service.

## Analysis reuse, orientation, and regions

`IMAGE_OCR` is compatible only with IMAGE sources. Before RUNNING, the service pages the existing product/source job history, selects the newest completed `IMAGE_ANALYSIS` job with a stored result, and verifies product/source/MIME/file-size linkage. It never recalculates or silently invents SPEC-019 regions.

Regions remain ordered `FULL_IMAGE`, `CENTER`, `TOP`, `BOTTOM`, `LEFT`, `RIGHT`; selection takes at most `IMAGE_OCR_MAX_REGIONS` and always begins with FULL_IMAGE. Source bytes are read through `ObjectStorage.open`, bounded to the analyzed size, decoded in memory under Pillow safeguards, and compared with analyzed format/dimensions. Crops exist only as temporary in-memory Pillow objects.

Orientation is deterministic: 90/180/270 rotations are applied clockwise as recorded by SPEC-019, MIRRORED uses its canonical horizontal mirror, and NORMAL/UNKNOWN retain stored orientation. Original region rectangles are mapped rigorously into the oriented full-image coordinate system. Every persisted OCR box uses that oriented coordinate space; 90/270 rotations therefore swap image width and height.

## Text, boxes, confidence, and duplicates

Normalization removes nulls, converts line endings to LF, trims outer whitespace, and collapses repeated horizontal whitespace per line. It preserves case, punctuation, line boundaries, symbols, decimal points, units, and model/serial tokens. It performs no spelling correction or semantic rewrite.

Every immutable block stores region ID, per-region reading order, normalized text, a positive oriented-image pixel box, integer 0–10,000 relative coordinates, and OCR-engine confidence converted from RapidOCR's 0–1 score to integer basis points. Raw floats and engine responses are not persisted.

Overlapping regions can repeat evidence. Deduplication compares only exact text after whitespace collapse and requires overlapping oriented boxes. The higher-confidence block is retained; different model/value text and nonoverlapping occurrences remain. Final blocks are ordered deterministically by source region and reading order, and the suppressed count is recorded.

## Quality and nameplate-text heuristic

`TEXT_FOUND` means at least one block meets `IMAGE_OCR_MIN_CONFIDENCE_BP`; `LOW_CONFIDENCE_TEXT` means text exists but none does; `NO_TEXT` means no nonempty blocks. All are successful technical outcomes.

The deterministic non-AI nameplate assessment returns `LIKELY_NAMEPLATE_TEXT`, `GENERIC_TEXT`, `NO_TEXT`, or `UNKNOWN`. Its 0–100 score uses only line count, digit-bearing lines, explicit engineering-unit tokens, colon label/value shapes, and mixed alphanumeric model/serial-like tokens. It does not identify a product category, parse a value, normalize a unit, or create an attribute.

## Persistence and lifecycle

The `{prefix}-image-ocr-results` table uses `ocrId` and `recordKey`. META contains identities, linked analysis, engine/version, oriented dimensions, aggregate counts, quality, nameplate status/score, warnings, and creation time. `BLOCK#000001` records contain ordered text/box/confidence evidence. Only META populates the sparse `JobIdIndex`. Creation is conditional; reads query and paginate; incomplete partitions fail; every item is rejected above 390,000 bytes.

The service validates job/source/duplicate/analysis state before starting, transitions PENDING→RUNNING before storage access, persists the OCR result, and transitions RUNNING→COMPLETED with progress 100 and `image-ocr-results/{ocrId}`. Controlled post-start failures attempt FAILED. A final job-update failure preserves the valid result and logs `image_ocr.completion_consistency_risk`.

Defaults are 6 regions, 5,000 blocks, 500,000 total characters, 10,000 characters per block, and 4,000 minimum-confidence basis points. Limits fail without truncation.

There is no run/result API, worker, queue, retry, frontend, S3 implementation, authentication, authorization, or deployment change.
