# Product Intelligence Read API

`GET /api/v1/products/{product_id}/intelligence-scores?limit=20&cursor=...` returns immutable scores
newest first. Limit is 1-100 and the opaque cursor is Product-scoped. Items contain score ID, overall
basis points and persisted integer percent, grade, projection/enrichment lineage, policy version,
and creation time.

`GET /api/v1/products/{product_id}/intelligence-scores/{score_id}` returns one persisted score with
all six deterministic components, metrics, strengths, and improvements. The score must belong to the
Product in the path. Missing and cross-product scores both return
`404 PRODUCT_INTELLIGENCE_SCORE_NOT_FOUND`.

Neither endpoint computes scores or invokes AI. Malformed cursors return
`400 INVALID_CURSOR`, absent Products return `404 PRODUCT_NOT_FOUND`, and storage
failures return `503 PRODUCT_INTELLIGENCE_SCORE_STORAGE_UNAVAILABLE` in the standard request-ID
envelope.
