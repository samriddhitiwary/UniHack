# Workflow Tracking

The Workflow tab consumes the SPEC-037 synchronous start/read/history/resume API. Launch defaults enable publishing readiness, export, AI enrichment, and intelligence scoring. `failOnOptionalStageError` remains off under Advanced settings. A confirmed empty source list disables launch.

The fifteen backend stages map to eight phases:

1. Analyze Sources — `SOURCE_PROCESSING`
2. Understand Product — `PRODUCT_CLASSIFICATION`
3. Structure Attributes — `ATTRIBUTE_EXTRACTION`, `ATTRIBUTE_NORMALIZATION`
4. Validate Catalog — `CONFLICT_DETECTION`, `COMPLETENESS`, `ATTRIBUTE_VALIDATION`, `ATTRIBUTE_SELECTION`
5. Human Review — `HUMAN_REVIEW`
6. Prepare Catalog — `REVIEWED_ATTRIBUTE_MATERIALIZATION`, `CATALOG_PROJECTION`, `PUBLISHING_READINESS`
7. Generate Outputs — `CATALOG_EXPORT`, `AI_ENRICHMENT`
8. Quality Evaluation — `PRODUCT_INTELLIGENCE_SCORE`

The timeline always names phase status in text. Technical stages, job IDs, result references, timestamps, skip reasons, and safe errors remain collapsed by default. Backend `progressPercent` is used directly.

Only full workflow detail with status RUNNING polls, every 2,500ms. Review waiting, failure, completion, and warning completion stop polling. History loads newest-first in bounded pages of ten; selecting a terminal historical run does not poll.

WAITING_FOR_REVIEW preserves `reviewId`. `COMPLETE_PRODUCT_REVIEW` links to the SPEC-041 placeholder and never bypasses review. `RESUME_WORKFLOW` sends the exact current version. Review-incomplete, stale-version, Product-change, source-change, active-workflow, no-source, and classification errors use business-safe messages while retaining codes/request IDs where available.

Completed views surface projection readiness, export/enrichment availability, and compact intelligence only. Export download, enrichment editing, detailed score analysis, raw evidence, and review decisions are intentionally absent.
