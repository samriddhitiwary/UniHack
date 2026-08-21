# Unilog Evaluation Architecture

SPEC-043 is a post-enrichment measurement boundary. `UnilogEvaluationService` first enriches the
official input through the SPEC-042 service, fingerprints that generated batch, and only then loads
the official expected output. Expected values are never passed to a resolver, classifier,
description builder, or attribute extractor.

```text
UnilogEvaluationService
  -> SPEC-042 batch enrichment
  -> ground-truth field and semantic attribute comparators
  -> coverage, description, confidence, review, and reliability evaluators
  -> deterministic field-error analysis and recommendations
  -> UnilogEvaluationRepository
```

The repository is intentionally separate from enrichment results. Its current process-local
implementation provides isolated local/API operation without changing the delivery schema or
requiring a DynamoDB scan. The protocol permits a durable adapter later. An evaluation ID is the
SHA-256 binding of the official dataset fingerprint, generated-batch fingerprint, and
`unilog-evaluation-policy-v1`; identical inputs therefore reproduce identical metric content.

The API exposes explicit creation, latest/by-ID reads, a summary, bounded and cursor-paginated field
metrics, stable labelled-row lookup, batch metrics, and error analysis. Row IDs are stable hashes,
not raw expected values. Filters are allowlisted and limits are bounded.

The React `/quality` route consumes the summary and selected row through the shared `/api/v1`
client. It keeps 2-row accuracy visually distinct from 1,000-row quality, uses textual labels for
every bar/status, and adapts analytical tables into cards on narrow screens. Loading, no-result, and
safe request-ID error states remain localized to the page.
