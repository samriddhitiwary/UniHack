# Catalog Search API

## Search products

`GET /api/v1/catalog/products`

Pagination uses `limit` (default 20, range 1-100) and opaque `cursor`. Results are newest-first except
normalized name-prefix results, which are lexical ascending.

| Filters | Match |
| --- | --- |
| none | newest Products |
| `status` | exact enum |
| `category` | exact enum |
| `category` + `status` | exact pair |
| `manufacturer` | normalized exact equality |
| `modelNumber` | normalized exact equality |
| `namePrefix` | normalized prefix |

Text normalization trims, lowercases, and collapses whitespace. `publishingReadiness`,
`intelligenceGrade`, `minIntelligenceScore`, and `maxIntelligenceScore` are recognized but unsupported
because no scan-free Product access plan exists. Any other filter combination is also unsupported.

Compact items include Product identity/lifecycle fields, readiness, freshness, persisted intelligence
percent/grade, top improvement codes, and enrichment/export availability. Components are omitted.

Errors: malformed/mismatched cursor `400 INVALID_CURSOR`; unsupported plan
`422 CATALOG_SEARCH_FILTER_COMBINATION_UNSUPPORTED`; invalid parameters
`422 REQUEST_VALIDATION_FAILED`; storage failure `503 CATALOG_SEARCH_STORAGE_UNAVAILABLE`.

## Product catalog summary

`GET /api/v1/products/{product_id}/catalog-summary`

Returns Product identity, latest projection and score summaries, freshness flags, and artifact
availability. Missing downstream artifacts are nullable values. An absent Product returns
`404 PRODUCT_NOT_FOUND`; storage failure returns `503 CATALOG_SEARCH_STORAGE_UNAVAILABLE`.
