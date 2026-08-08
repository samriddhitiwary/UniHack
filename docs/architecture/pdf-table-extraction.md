# PDF Table Extraction

SPEC-017 adds a directly invoked backend service for bounded structured-table extraction. It is not an HTTP endpoint, worker, OCR engine, or semantic interpreter.

```text
PENDING PDF_TABLE_EXTRACTION job
        |
        | validate job and product-scoped PDF source
        v
RUNNING -> ObjectStorage.open -> pdfplumber -> page-ordered tables
                                                |
                                                v
                     table-extraction-results META + TABLE records
                                                |
                                                v
                         COMPLETED with resultReference
```

## Parser, evidence, and ordering

`pdfplumber` 0.11.x reads the binary stream from `ObjectStorage.open` with no path, shell command, Poppler process, Java runtime, OCR, or attachment extraction. Pages are visited in ascending order. Tables retain parser order and receive a 1-based index that restarts on each page. Tables are never merged within or across pages.

Cells retain zero-based row and column positions. `None` becomes an empty string; null characters are removed; CRLF/CR become LF; and outer whitespace is trimmed. Internal spaces/newlines, case, punctuation, symbols, and units are preserved. Ragged rows are padded with explicit empty cells to the widest extracted row. A candidate with no rows, no columns, or only empty cells is ignored as parser noise.

## Quality and safety

- `TABLES_FOUND`: at least one valid table and no recoverable parser warnings.
- `NO_TABLES`: a readable PDF contains no detectable valid tables; this completes successfully.
- `PARTIAL`: reserved for tables with real recoverable parser warnings. The current adapter emits no warnings because pdfplumber exposes no deterministic warning contract; it does not fabricate this state.

| Environment setting | Default |
| --- | ---: |
| `PDF_TABLE_EXTRACTION_MAX_PAGES` | 300 |
| `PDF_TABLE_EXTRACTION_MAX_TABLES` | 500 |
| `PDF_TABLE_EXTRACTION_MAX_ROWS_PER_TABLE` | 5,000 |
| `PDF_TABLE_EXTRACTION_MAX_COLUMNS_PER_TABLE` | 200 |
| `PDF_TABLE_EXTRACTION_MAX_CELLS` | 500,000 |
| `PDF_TABLE_EXTRACTION_MAX_CELL_CHARACTERS` | 20,000 |

All settings must be positive. Limits fail without truncation or successful partial persistence.

## Persistence and lifecycle

`{DYNAMODB_TABLE_PREFIX}-table-extraction-results` uses `extractionId`/`recordKey`. `META` stores identities, parser metadata, aggregates, quality, warnings, and creation time. `TABLE#{page:06d}#{table:06d}` stores one table's rows and cells, preserving lexical order. Only META has `jobId` and `createdAt`, making `JobIdIndex` sparse. Every serialized record is checked below a conservative 390,000-byte ceiling before any write.

Job/source validation and duplicate-result lookup happen before RUNNING. The optimistic RUNNING update precedes storage access. The result is persisted before COMPLETED, which sets progress 100 and `table-extraction-results/{extractionId}`. Corrupt PDFs, missing objects, parser/limit/storage/persistence failures attempt FAILED with safe metadata. If the final COMPLETED update fails, the valid result remains and a consistency-risk event records that the job may remain RUNNING. Product-source status is never modified.

Multi-record writes are not transactional. A mid-write storage failure can leave incomplete records, but retrieval count/invariant validation rejects them and the job is never completed. No cleanup worker is introduced.
