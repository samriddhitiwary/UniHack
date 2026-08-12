# Image and Nameplate Analysis Foundation

SPEC-019 adds a direct, backend-only image inspection workflow for stored IMAGE sources. It validates PNG, JPEG, and WEBP content with Pillow, records bounded metadata and deterministic geometry evidence, and updates an existing IMAGE_ANALYSIS processing job. It does not recognize text or objects.

```text
ImageAnalysisService -> ProcessingJobRepository (RUNNING/COMPLETED/FAILED)
                     -> ProductSourceRepository (scoped IMAGE metadata)
                     -> ObjectStorage.open (bounded binary stream)
                     -> ImageInspector (Pillow validation and metadata)
                     -> ImageAnalysisResultRepository (META + REGION evidence)
```

## Validation and metadata

The source MIME type must be exactly `image/png`, `image/jpeg`, or `image/webp`, and the decoded Pillow format must match it. Corrupt, mismatched, unsupported, and multi-frame images fail with controlled codes. Pillow decompression-bomb warnings and errors remain enabled and map to a safe pixel-limit failure.

Inspection stores only safe metadata: decoded format and MIME type, width, height, integer pixel count, the exact integer `width/height` aspect representation, color mode, alpha/grayscale flags, mapped EXIF orientation, and actual bounded file size. Arbitrary EXIF, filenames, paths, object keys, image bytes, crops, and generated files are never persisted.

Default limits are 10,485,760 file bytes, 12,000 pixels per dimension, 80,000,000 total pixels, and 16 regions. The binary stream is stopped before decoding when the byte limit is exceeded. Images are never resized or truncated.

## Regions and nameplate heuristic

Every valid image produces six regions in a fixed order: `FULL_IMAGE`, `CENTER`, `TOP`, `BOTTOM`, `LEFT`, and `RIGHT`. Each region stores a bounded pixel box and integer relative coordinates in basis points from 0 through 10,000. Tiny and odd-sized images remain within the source dimensions.

The result status is `POSSIBLE`, `UNLIKELY`, or `UNKNOWN`, derived only from explicit dimension and aspect thresholds. The 0–100 heuristic score is deterministic geometry suitability, not a probability or confidence score. No OCR, image classification, object detection, AI vision, semantic attribute extraction, or true nameplate recognition occurs.

## Persistence and lifecycle

The `{prefix}-image-analysis-results` table uses `analysisId` and `recordKey`. One `META` record holds identities, parser/version, metadata, aggregate heuristic values, warning codes, counts, and creation time. `REGION#000001` through `REGION#000006` hold ordered region evidence. Only META populates the sparse `JobIdIndex`; reads use queries, paginate, and validate complete reconstruction. Every item is rejected before writing if its serialized size exceeds 390,000 bytes.

The service validates the job, source, MIME metadata, and duplicate-result state before starting. It then transitions `PENDING` to `RUNNING`, opens the object through the storage protocol, inspects and persists the result, and transitions to `COMPLETED` with progress 100 and `image-analysis-results/{analysisId}`. Controlled failures after start attempt `FAILED`. If the final job update fails after result persistence, the evidence is preserved and a safe consistency-risk event is logged.

There is no execution endpoint, result endpoint, worker, scheduler, queue, frontend, S3 implementation, authentication, or deployment change in this feature.
