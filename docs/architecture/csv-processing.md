# CSV Processing

SPEC-018 adds a directly invoked backend service for bounded CSV parsing. It is not an HTTP endpoint, worker, spreadsheet evaluator, or semantic interpreter.

```text
PENDING CSV_PROCESSING job
        |
        | validate job and product-scoped CSV source
        v
RUNNING -> ObjectStorage.open -> standard-library csv.reader -> ordered evidence
                                                              |
                                                              v
                                  csv-processing-results META + ROW records
                                                              |
                                                              v
                                      COMPLETED with resultReference
```

## Encoding, dialect, and header

The parser reads the binary object in bounded chunks and decodes strictly with `utf-8-sig`, accepting UTF-8 with or without BOM. Invalid bytes fail; legacy encoding is not guessed. A bounded sample is passed to `csv.Sniffer` with only comma, semicolon, tab, and pipe. A comma fallback is permitted only when an unquoted comma is clearly present. Ambiguous delimiters fail safely.

Python `csv.reader(..., strict=True)` supplies standard quoted-field, escaped-quote, quoted-delimiter, and quoted-multiline behavior. The first meaningful parsed row is the required header. Header order, duplicates, and empty names remain unchanged. A header-only CSV is valid; a file with no header row fails.

## Row evidence and warnings

Data rows are numbered from one in source order. Cells remain strings: no numbers, dates, Booleans, formulas, or units are interpreted. Null characters are removed, CRLF/CR become LF, and outer whitespace is trimmed; internal spacing/newlines, case, punctuation, leading zeroes, and formula-looking prefixes (`=`, `+`, `-`, `@`) remain text.

Regular `cells` always match header width. Short rows are padded with empty cells and receive `CSV_ROW_MISSING_COLUMNS`. Overflow values are retained in `extraCells` and receive `CSV_ROW_EXTRA_COLUMNS`. Recoverable rows produce `VALID_WITH_WARNINGS`; completely aligned rows produce `VALID`. Only parser rows equal to `[]` are ignored as blank physical lines, so explicitly quoted empty values remain evidence.

`totalCellCount` includes normalized regular cells and preserved extra cells, excluding headers. `emptyCellCount` counts empty regular and extra cells. Malformed-row count and result warning codes derive from row evidence.

## Safety limits

| Environment setting | Default |
| --- | ---: |
| `CSV_PROCESSING_MAX_FILE_BYTES` | 5,242,880 |
| `CSV_PROCESSING_MAX_ROWS` | 100,000 |
| `CSV_PROCESSING_MAX_COLUMNS` | 500 |
| `CSV_PROCESSING_MAX_TOTAL_CELLS` | 1,000,000 |
| `CSV_PROCESSING_MAX_CELL_CHARACTERS` | 50,000 |
| `CSV_PROCESSING_SAMPLE_BYTES` | 65,536 |

All values must be positive. Header width and overflow row width both honor the column limit. No limit silently truncates evidence.

## Persistence and lifecycle

`{DYNAMODB_TABLE_PREFIX}-csv-processing-results` uses `processingId`/`recordKey`. `META` stores identities, UTF-8/delimiter metadata, header, aggregates, quality, warnings, and creation time. `ROW#{rowNumber:09d}` stores one ordered row. Only META contains `jobId` and `createdAt`, making `JobIdIndex` sparse. All serialized items are checked below 390,000 bytes before any writes.

Validation and duplicate-result lookup occur before RUNNING. Storage access follows the optimistic RUNNING update. Result persistence precedes COMPLETED, which sets progress 100 and `csv-processing-results/{processingId}`. Controlled storage, decoding, delimiter, syntax, limit, size, and persistence errors attempt FAILED with safe metadata. A final completion-update failure preserves the valid result and logs that the job may remain RUNNING.

Multi-record writes are not transactional. A mid-write failure cannot complete the job, and retrieval validates row counts/order and rejects incomplete partitions. No cleanup worker, retry, API, classification, attribute extraction, or AI is introduced.
