# SPEC-034 — AI Catalog Enrichment and Commerce Content Generation Engine

## Status
Completed

## Objective
Generate grounded commerce content from one explicit immutable eligible SPEC-031 projection without
inventing facts or mutating authoritative catalog data.

## User Story
As a catalog operator, I need useful commerce copy whose factual claims remain traceable to reviewed
catalog facts so it can be audited before any future publication workflow.

## Scope
Trusted-fact construction, provider-independent generation, deterministic prompts, strict structured
parsing, hallucination guards, bounded retry, immutable DynamoDB results, job lifecycle, tests, and
documentation.

## Out of Scope
Product/projection/export mutation, publishing, web enrichment, marketplace adapters, images,
search indexing, scoring, frontend, authentication, authorization, S3, and deployment.

## Functional Requirements
Require a PENDING product-level AI_CATALOG_ENRICHMENT job and explicit READY or
READY_WITH_WARNINGS projection. Generate title, description, bullets, keywords, and technical
summary; validate every item against stable fact IDs; persist only safe structured output.

## Non-Functional Requirements
Provider-independent, deterministic setup, strict immutable models, bounded inputs/outputs,
auditable validation, safe logs, no secret/raw-response persistence, queries only, and >=90% coverage.

## Existing Dependencies
SPEC-031 projection snapshots, reviewed-attribute lineage, validation/origin metadata, processing-job
state machine, DynamoDB serialization/repository patterns, and SPEC-033 checksum conventions.

## Enrichment Input
One explicit projection ID. Current Product is loaded only for existence and ownership coherence;
prompt facts and identity come exclusively from the immutable projection.

## Trusted Facts Boundary
Only projection identity, category, existing description, reviewed attributes, warnings, origins,
and validation status are trusted. Generic knowledge and inferred claims are not facts.

## LLM Provider Abstraction
A synchronous protocol accepts system/user prompts. A configured OpenAI adapter owns SDK calls,
timeouts, model/output settings, and controlled exception mapping; tests use fakes.

## Prompt Construction
Prompt version `catalog-enrichment-prompt-v1`; canonical sorted trusted-data JSON; explicit untrusted
data delimiter; no timestamps; strict JSON schema and forbidden-claim rules; stable SHA-256.

## Structured Generation Contract
Strict JSON with title, description, featureBullets, searchKeywords, and technicalSummary. Each item
contains only `text` and `factIds`; unknown fields and prose wrappers are rejected.

## Generated Product Title
Required, nonempty, grounded, and limited to 200 characters by default.

## Generated Description
Required, grounded, technical/commercial, and limited to 2,000 characters by default.

## Generated Feature Bullets
Three to eight by default, each nonempty, grounded, limited to 300 characters, and deterministically
deduplicated by collapsed-whitespace case-folded text.

## Generated Search Keywords
One to twenty by default, each grounded, limited to 100 characters, and deterministically
deduplicated while preserving retained casing.

## Generated Technical Summary
Required, grounded, limited to 1,000 characters, and forbidden from conversions or absent values.

## Grounding and Fact Attribution
Stable `IDENTITY:*` and `ATTRIBUTE:*` IDs form the only grounding vocabulary. Every generated item
must cite at least one known fact. Coverage is unique referenced facts divided by eligible facts in
integer basis points.

## Hallucination Guard
Deterministic guards reject unknown/empty references, unsupported numeric and unit claims,
certifications, warranties, materials, performance language, and specific use cases. No LLM judge.

## Generation Validation
Strict parsing, lengths/counts, fact-reference limits, duplicate normalization, numeric/spec support,
and denylist rules execute after every provider response.

## Confidence and Warnings
Successful content has `groundingScoreBp=10000`; this is validation status, not model probability.
`factCoverageBp` measures reference coverage only. Deterministic warnings preserve upstream state and
may flag limited facts or unused descriptions.

## Result Model
Immutable result and content items preserve projection/schema lineage, validated content, coverage,
warnings, provider/model, prompt version/hash, attempts, engine/version, and UTC creation time.

## DynamoDB Persistence
`catalog-enrichment-results` uses enrichmentId/recordKey with META, TITLE, DESCRIPTION,
TECHNICAL_SUMMARY, ordered BULLET and KEYWORD records, sparse JobIdIndex/ProjectionIdIndex, an exact
input guard, conditional writes, complete partition validation, and 390,000-byte item guards.

## Processing Job Lifecycle
Validate deterministic setup before PENDING→RUNNING; call the provider only while RUNNING; persist
before RUNNING→COMPLETED with `catalog-enrichment-results/{enrichmentId}`. Technical/unsafe failures
attempt FAILED. Completion failure retains the valid result.

## Idempotency
One authoritative result per projectionId, promptVersion, provider, and model. A SHA-256 input guard
prevents duplicate provider cost while allowing future prompt/model revisions.

## Safety Limits
Defaults: 200 facts, 10,000 fact-value characters, 200 title, 2,000 description, 8 bullets of 300,
20 keywords of 100, 1,000 summary, 50 references/item, 500 total references, two attempts, and
390,000 bytes per record.

## Error Handling
Controlled errors cover setup/lineage, duplicate input, limits, provider timeout/unavailable/rate
limit/failure, malformed response, unsupported claims, grounding failure, persistence, and engine
failure. Unsafe or raw outputs are never persisted.

## Logging Requirements
Log safe IDs, provider/model, prompt version, attempt, counts, and issue codes. Never log credentials,
full prompts, trusted values, generated copy, or raw responses.

## Security Considerations
Treat delimited catalog text as untrusted data; disable model tools; enforce strict JSON and limits;
perform no web lookup, URL action, code execution, or model-initiated external action.

## Edge Cases
Missing optional identity, human overrides, validation warnings, prompt injection text, duplicate
content, unknown/empty references, unsupported claims, retry success/failure, provider failures,
duplicate races, incomplete partitions, and completion consistency risk.

## Acceptance Criteria
All 151 supplied criteria must pass without out-of-scope behavior.

## Test Plan
Cover trusted facts, prompts, strict parsing, all claim guards, injection, retry/provider failures,
domain/serialization/repository invariants, lifecycle/immutability, optional provider contract, and
all repository-wide verification gates.

## Implementation Notes
The configured adapter is isolated behind the protocol. Prompts/raw responses are not persisted.
Existing Product, projection, reviewed materialization, and export artifacts remain untouched.

## Completion Record
Completed on 2026-08-20. The full backend suite passed with 1,545 tests, 16 explicitly opt-in
integration tests skipped, and 90.75% coverage. Ruff lint/formatting, strict mypy, unchanged frontend
tests, ESLint, Prettier, Vite build, Docker Compose validation, and Git whitespace validation all
passed. All 151 acceptance criteria were verified within the SPEC-034 boundary.
