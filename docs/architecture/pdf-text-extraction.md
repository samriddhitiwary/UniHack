# PDF Text Extraction

SPEC-016 adds a directly invoked backend service for embedded text extraction. It is not
an HTTP endpoint, worker, queue consumer, scheduler, or OCR engine.

```text
PENDING PDF_TEXT_EXTRACTION job
        |
        | validate job and product-scoped PDF source
        v
RUNNING job -> ObjectStorage.open -> pypdf -> ordered page evidence
                                             |
                                             v
                              extraction-results META + PAGE records
                                             |
                                             v
                         COMPLETED job with resultReference
```

## Parser and normalization

pypdf 6.x reads the binary stream returned by `ObjectStorage.open`. No filesystem path,
shell command, Poppler binary, JavaScript action, embedded attachment, image extraction,
or OCR integration is used.

Each page retains its 1-based PDF position, including blank pages. Parser text has null
characters removed, CRLF/CR converted to LF, and leading/trailing whitespace stripped.
Internal line breaks, case, punctuation, and units remain unchanged. Character counts are
calculated after normalization.

## Safety limits

| Environment setting | Default |
| --- | ---: |
| `PDF_EXTRACTION_MAX_PAGES` | 300 |
| `PDF_EXTRACTION_MAX_PAGE_CHARACTERS` | 100,000 |
| `PDF_EXTRACTION_MAX_TOTAL_CHARACTERS` | 2,000,000 |

All values must be positive. Limits fail extraction without truncating evidence or
persisting a completed result.

## Quality

- `NO_TEXT`: zero normalized characters. Readable scanned/image-only PDFs complete with
  this status; no OCR is attempted.
- `LOW_TEXT`: some text exists but the average is below 25 characters per PDF page.
- `USABLE`: all other structurally readable embedded-text results.

Quality is deterministic and does not use AI. LOW_TEXT and NO_TEXT are successful parser
outcomes, so their jobs complete normally.

## Persistence

`{DYNAMODB_TABLE_PREFIX}-extraction-results` uses partition key `extractionId` and sort key
`recordKey`. One `META` record stores summary data; `PAGE#000001` records store one bounded
page each. Only META contains `jobId` and `createdAt`, making `JobIdIndex` sparse. The
repository reconstructs ordered domain results and paginates DynamoDB queries internally.

Metadata creation is conditional. Pages are written only after META. A page-write failure
may leave an incomplete partition, but it cannot be reported as a successful result and
the job is marked FAILED where possible. Retrieval detects missing pages as controlled
serialization failure.

## Job lifecycle and failures

Job/type/state and source/type/key validation occur before RUNNING. Storage access begins
only after the optimistic RUNNING update. Corrupt PDFs, missing objects, page/text limits,
and result persistence failures apply safe error codes and transition RUNNING to FAILED
where possible. Source status and metadata are never changed.

Result persistence occurs before the COMPLETED update. If that final optimistic job update
fails, the valid result is retained and a `completion_consistency_risk` event is logged;
the job may remain RUNNING. No unsafe result rollback is attempted.
