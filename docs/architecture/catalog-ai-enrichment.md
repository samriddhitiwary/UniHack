# Grounded AI Catalog Enrichment

SPEC-034 generates commerce copy from one explicit immutable SPEC-031 projection. The generated
title, description, feature bullets, search keywords, and technical summary are a separate immutable
artifact. Product fields, reviewed attributes, projections, and SPEC-033 export packages are never
modified.

## Input and lifecycle

`AI_CATALOG_ENRICHMENT` is product-level, has no source, and requires `projectionId`. Deterministic
setup verifies a PENDING job, Product existence, projection ownership, READY or
READY_WITH_WARNINGS status, structural coherence, fact limits, and absence of an exact duplicate.
BLOCKED is rejected before RUNNING. Prompt identity comes only from the projection snapshot; current
Product content is not substituted.

After setup, the job becomes RUNNING immediately before the provider call. Validated output is
persisted before COMPLETED and linked as `catalog-enrichment-results/{enrichmentId}`. Provider,
parsing, grounding, limit, and storage errors attempt FAILED. If completion fails after persistence,
the valid immutable result remains and a consistency-risk event is logged.

## Provider boundary and structured generation

`CatalogEnrichmentLlm` is a provider-independent synchronous protocol. The configured OpenAI
Responses API adapter takes its API key, model, temperature, token bound, and timeout from settings,
disables tools, and maps timeout, unavailable, rate-limit, and generic failures to safe codes. It
never logs secrets, full prompts, or raw responses.

Prompt version `catalog-enrichment-prompt-v1` uses sorted compact trusted-data JSON and no current
time. The system instructions isolate catalog text as untrusted data, prohibit external actions and
unsupported claims, and require JSON-only output. Strict parsing rejects wrappers, extra/missing
fields, wrong types, empty grounding, and configured content/reference limits. A failed parse or
grounding check may trigger one deterministic correction attempt containing issue codes—not unsafe
generated text.

## Quality metadata

Every content item preserves fact IDs. `factCoverageBp` is unique referenced trusted facts divided by
eligible trusted facts in integer basis points. `groundingScoreBp=10000` means every persisted item
passed deterministic checks; it is not model confidence or a probability. Warnings preserve upstream
projection warnings and flag limited facts, unused descriptions, human overrides, validation
warnings, or low coverage.

## Persistence and idempotency

`catalog-enrichment-results` stores META, TITLE, DESCRIPTION, TECHNICAL_SUMMARY, ordered BULLET, and
ordered KEYWORD records under enrichmentId/recordKey. Sparse JobIdIndex and ProjectionIdIndex provide
query-only access. A transactional SHA-256 guard over projection ID, prompt version, provider, and
model prevents duplicate provider cost while permitting future prompt/model revisions. Complete
partition reconstruction, conditional writes, and 390,000-byte item limits apply.

## Scope boundary

There is no execution API, Product/projection/export mutation, external publishing, marketplace
adapter, web enrichment, model browsing/tools, image generation, search indexing, score, frontend,
authentication, authorization, S3, or deployment behavior.
