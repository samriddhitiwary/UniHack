# System Overview

The foundation has three independently runnable parts:

```text
Browser -> React/Vite application
              |
              v
        FastAPI /api/v1
              |
              v
       Repository interface
              |
              v
       DynamoDB repository -> DynamoDB Local (development)
                          -> Amazon DynamoDB (production configuration)
```

The frontend owns presentation and browser-side state. The API owns validated configuration and application behavior. Product and product-source domain models are independent of Boto3. Their repository protocols return domain entities, while DynamoDB implementations own item naming, serialization, conditional writes, index queries, and cursors.

The local products table supports repository development. SPEC-006 exposes create, list, retrieve, partial-update, and conditional-delete routes through this dependency chain:

```text
Product route -> ProductService -> ProductRepository protocol -> DynamoDBProductRepository
```

FastAPI providers construct the configured repository and service, so tests can replace the service without AWS. Routes never import Boto3 or instantiate repositories. The list service selects the existing creation-time or status access pattern, while cursor decoding and newest-first DynamoDB queries remain repository responsibilities. For PATCH, the service retrieves the immutable entity and merges only explicitly supplied editable fields; the repository owns conditional version comparison, version increment, and update timestamp. DELETE also performs a service pre-read, then the repository atomically requires the expected version to prevent a stale client from deleting newer data. There is no soft delete, restore, cascade, bulk operation, PUT replacement, or frontend product workflow; only DynamoDB infrastructure code may call Boto3.

SPEC-007 adds a backend-only product-source metadata foundation:

```text
Future source service -> ProductSourceRepository protocol -> DynamoDBProductSourceRepository
```

The source table groups records by product, lists them newest first through `ProductCreatedAtIndex`, and protects mutations with versions. Scoped opaque cursors prevent source-list cursors from crossing products or being reused as product-list cursors.

SPEC-008 adds an independent backend-only object-storage foundation:

```text
Future source service -> ObjectStorage protocol -> LocalObjectStorage (development)
```

Logical keys, rather than filesystem paths, identify objects. The local backend streams bytes through bounded chunks, enforces the caller's maximum size, calculates SHA-256, prevents overwrite, and stores validated metadata sidecars. Every operation validates path safety and resolved-root containment. The settings-driven provider currently accepts only `local`; S3 remains a future backend. This layer does not create source records and is not exposed through an API.

SPEC-009 exposes one source workflow while keeping the storage foundation separate:

```text
POST text-source route
        |
        v
ProductSourceService
        |-- ProductRepository (parent existence)
        `-- ProductSourceRepository (TEXT metadata persistence)
```

The service validates the parent, computes UTF-8 size and SHA-256, and persists a `READY` text source through the existing DynamoDB repository. Routes contain no repository or checksum logic. The text endpoint stores no file and does not call `ObjectStorage`. No source list, retrieve, update, delete, or processing workflow exists.

SPEC-010 adds a separate multipart upload route. The service validates filename, MIME, and a bounded content sample, streams through `ObjectStorage`, and persists `READY` file metadata. Persistence failure triggers compensating object deletion; no parser or processing workflow runs.

SPEC-011 exposes read-only source metadata workflows:

```text
GET product sources route -> ProductSourceService -> parent ProductRepository check
                                              `-> ProductSourceRepository query/get
```

Both reads validate the parent before accessing sources. Listing reuses the descending `ProductCreatedAtIndex` query and product-bound opaque cursor, defaults to 20 records, and permits 1 through 100. Retrieval uses the product/source composite key, so cross-product source IDs remain undisclosed. These routes do not call object storage or return file bytes, and they add no filters, scans, counts, mutation, download, or processing behavior.

SPEC-012 adds one product-scoped partial-update workflow:

```text
PATCH source route -> ProductSourceService -> parent/source validation
                                      |-> transition and explicit-field merge
                                      `-> conditional ProductSourceRepository update
```

The public allowlist contains only display name, status, and error message plus the required client version. The service preserves immutable content/file metadata, validates direct status transitions, and clears stale errors on recovery or completion. DynamoDB atomically checks the expected version, increments it once, and refreshes the update timestamp. The workflow never accesses object storage and does not replace files/text or start a processing job.

SPEC-013 adds one conditional source-deletion workflow:

```text
DELETE source route -> ProductSourceService -> parent/source/version validation
                                      |-> ObjectStorage.delete (PDF/IMAGE/CSV only)
                                      `-> conditional ProductSourceRepository.delete
```

TEXT deletion bypasses storage. File-backed metadata must contain a server-owned logical key; missing or absent objects are controlled consistency failures. Object-first ordering avoids deleting metadata successfully while leaving an orphan, but storage and DynamoDB are not transactional: a final repository failure may leave metadata after its bytes were removed. That risk is logged and returned as failure without weakening concurrency.

SPEC-014 adds a processing-job domain and DynamoDB persistence foundation:

```text
Future job service -> ProcessingJobRepository protocol -> DynamoDBProcessingJobRepository
```

One immutable record represents one future attempt for one product source. The repository conditionally creates jobs, retrieves by `jobId`, lists newest first by product or product/source with separately scoped opaque cursors, and conditionally updates status metadata by expected version. The processing-jobs table uses `ProductCreatedAtIndex` and `SourceCreatedAtIndex`; the latter partitions on server-derived `productId#sourceId`. No API route, worker, queue, polling, retry execution, parser, extractor, OCR, or AI call exists.

SPEC-015 exposes only processing-job creation and reads:

```text
Processing-job routes -> ProcessingJobService -> ProductRepository (parent check)
                                         |----> ProductSourceRepository (scoped source check)
                                         `----> ProcessingJobRepository (create/get/query)
```

Create accepts only a job type, validates product/source ownership and the centralized compatibility matrix, then persists one PENDING job. Product and source lists validate their parents before using the existing descending GSIs and separately scoped opaque cursors. Routes depend only on the service; the service imports neither FastAPI nor Boto3. No PATCH, DELETE, global list, start, cancel, retry, worker, scheduler, queue, parser, extraction, OCR, or AI execution is exposed.

SPEC-016 adds direct PDF embedded-text extraction orchestration:

```text
PdfTextExtractionService -> ProcessingJobRepository (RUNNING/COMPLETED/FAILED)
                         -> ProductSourceRepository (scoped PDF metadata)
                         -> ObjectStorage.open (binary PDF stream)
                         -> PdfTextParser (pypdf, bounded pages/text)
                         -> PdfExtractionResultRepository (META + PAGE evidence)
```

Result evidence is stored outside source/job records in a composite DynamoDB table. Blank
pages retain their positions; deterministic quality is USABLE, LOW_TEXT, or NO_TEXT.
Readable scanned/image-only PDFs complete as NO_TEXT without OCR. The service has no API,
worker, scheduler, queue, direct filesystem/Boto3 use, table extraction, or AI behavior.

SPEC-017 adds direct PDF structured-table extraction orchestration:

```text
PdfTableExtractionService -> ProcessingJobRepository (RUNNING/COMPLETED/FAILED)
                          -> ProductSourceRepository (scoped PDF metadata)
                          -> ObjectStorage.open (binary PDF stream)
                          -> PdfTableParser (pdfplumber, bounded evidence)
                          -> PdfTableExtractionRepository (META + TABLE evidence)
```

Page and parser table order, empty cells, and rectangular row/column positions are preserved. Readable PDFs without tables complete as NO_TABLES. Results live outside sources/jobs and each table record is size-checked before persistence. There is no OCR, semantic table joining, AI, worker, or execution/result API.

SPEC-018 adds direct CSV processing orchestration:

```text
CsvProcessingService -> ProcessingJobRepository (RUNNING/COMPLETED/FAILED)
                     -> ProductSourceRepository (scoped CSV metadata)
                     -> ObjectStorage.open (bounded binary stream)
                     -> CsvParser (UTF-8, allowlisted dialect, ordered strings)
                     -> CsvProcessingResultRepository (META + ROW evidence)
```

Headers, data-row order, blank cells, leading zeroes, quoted multiline text, and formula-looking strings are preserved without evaluation. Short and overflow rows complete with explicit warnings; structural and hard-limit failures do not persist successful results. There is no schema inference, classification, attribute extraction, API, worker, or AI behavior.

SPEC-019 adds direct image-analysis orchestration:

```text
ImageAnalysisService -> ProcessingJobRepository (RUNNING/COMPLETED/FAILED)
                     -> ProductSourceRepository (scoped IMAGE metadata)
                     -> ObjectStorage.open (bounded binary stream)
                     -> ImageInspector (Pillow validation and safe metadata)
                     -> ImageAnalysisResultRepository (META + REGION evidence)
```

PNG, JPEG, and WEBP inputs are decoded with format/MIME matching, animation rejection, decompression-bomb safeguards, and explicit byte/dimension/pixel limits. The service stores safe metadata plus six deterministic geometry regions and a pre-OCR suitability heuristic. It performs no OCR, object detection, classification, AI vision, or attribute extraction and exposes no execution or result API.

SPEC-020 adds direct local OCR orchestration:

```text
ImageOcrService -> ProcessingJobRepository (analysis history + lifecycle)
                -> ProductSourceRepository (scoped IMAGE metadata)
                -> ImageAnalysisResultRepository (SPEC-019 regions)
                -> ObjectStorage.open (bounded analyzed bytes)
                -> OcrEngine / RapidOCR ONNX Runtime (in-memory local OCR)
                -> ImageOcrResultRepository (META + BLOCK evidence)
```

A dedicated `IMAGE_OCR` job avoids reusing a completed analysis job. The service maps SPEC-019 regions into a deterministic oriented-image coordinate system, preserves normalized text, reading order, integer confidence basis points, and boxes, suppresses only overlapping whitespace-equivalent duplicates, and completes successfully for TEXT_FOUND, LOW_CONFIDENCE_TEXT, or NO_TEXT. Its nameplate-text score is a deterministic evidence heuristic only. No product classification, structured attribute extraction, unit normalization, LLM, hosted OCR, worker, execution/result API, or frontend behavior is added.

SPEC-021 adds internal product-level deterministic classification:

```text
ProductClassificationService -> Product/ProcessingJob repositories (validation/lifecycle)
                             -> ProductClassificationEvidenceAggregator
                                  -> source and extraction-result repositories
                             -> ProductClassificationEngine (bounded integer rules)
                             -> ProductClassificationResultRepository (META + MATCH evidence)
```

Unlike prior jobs, `PRODUCT_CLASSIFICATION` has no source ID and is omitted from the sparse source
index. The source-scoped public job API rejects it. Available direct text, PDF text/table, CSV, and
OCR evidence is normalized only for matching, remains traceable, and is hard bounded. Classified,
ambiguous, insufficient, and conflicting outcomes all complete successfully. Confidence is score
separation in basis points rather than ML probability. No LLM, file access, API, frontend, attribute
extraction, or automatic `Product.category` mutation is added.
