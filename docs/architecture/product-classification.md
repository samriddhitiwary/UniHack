# Product Classification

SPEC-021 adds an internal, backend-only deterministic classifier. A product-level
`PRODUCT_CLASSIFICATION` job has no `sourceId`; all older processing jobs remain source scoped.
The public source-job creation API explicitly rejects this job type. There is no classification
execution or result HTTP endpoint.

The evidence aggregator pages through product sources and their completed job histories in
repository order. It converts direct TEXT, PDF pages, PDF table cells, CSV headers/cells, and OCR
blocks into a common traceable model. Default limits are 5,000 items, 500,000 total characters,
and 5,000 characters per item. Exceeding a limit fails instead of truncating. OCR evidence weight
is `100 * confidenceBp // 10000`; fixed weights are 100 for direct/PDF text, 110 for table cells
and CSV headers, and 90 for CSV cells.

`deterministic-rule-v1` uses word-boundary-aware curated pump and motor phrases with integer
STRONG/MEDIUM/WEAK strengths of 10/4/1. Scores are strength times evidence weight. The minimum
score is 1,000 and clear-margin threshold is 300. Strong opposing signals from different sources
produce `CONFLICTING_EVIDENCE`; close qualifying scores produce `AMBIGUOUS`; weak evidence
produces `INSUFFICIENT_EVIDENCE`. These are all successful results. Confidence is integer basis
points: `min(10000, margin * 10000 // max(winner, 1000))`. It is rule separation, not an ML
probability.

`{prefix}-product-classification-results` uses `classificationId`/`recordKey`. META stores result
identity, scores, confidence, counts, engine/version, warnings, and creation time. Ordered
`MATCH#000001` records store bounded excerpts and provenance for matched signals only. META alone
populates the sparse `JobIdIndex`. Creation is conditional, partition reconstruction paginates,
and every item has a 390,000-byte pre-write guard. No scans or raw source documents are stored.

The service validates job/product/duplicate state, transitions PENDING to RUNNING, aggregates and
classifies, persists the result, then completes with
`product-classification-results/{classificationId}`. Technical failures attempt FAILED with safe
codes. It never mutates `Product.category`; applying a reviewed classification is intentionally
deferred.
