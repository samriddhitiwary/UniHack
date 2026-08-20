# Catalog workflow API

All routes are Product-scoped and use camelCase JSON. Responses contain job/result references, not
raw extracted attributes or source content.

## Start

`POST /api/v1/products/{productId}/workflows`

```json
{
  "applyPublishingReadiness": true,
  "generateExport": true,
  "generateAiEnrichment": true,
  "calculateIntelligenceScore": true,
  "failOnOptionalStageError": false
}
```

The call executes synchronously until review, a terminal failure, or completion. A second active
workflow for the Product returns `409 WORKFLOW_ALREADY_ACTIVE`; a Product without sources returns
`409 WORKFLOW_NO_PRODUCT_SOURCES`.

## Read and history

- `GET /api/v1/products/{productId}/workflows/{workflowId}` returns full compact stage state.
- `GET /api/v1/products/{productId}/workflows?limit=20&cursor=...` returns newest-first history.

Cursors are opaque, Product-scoped, and limited to 100 records per page. Cross-Product workflow IDs
return `404 CATALOG_WORKFLOW_NOT_FOUND`.

## Resume

`POST /api/v1/products/{productId}/workflows/{workflowId}/resume`

```json
{"version": 18}
```

Only `WAITING_FOR_REVIEW` is resumable. The exact stored review must be COMPLETED. Stale versions
return `409 WORKFLOW_VERSION_CONFLICT`; an OPEN review returns
`409 WORKFLOW_REVIEW_NOT_COMPLETED`; Product/source changes or terminal workflows return a controlled
resume conflict. The response is the newly paused or terminal workflow.
