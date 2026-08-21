# SPEC-043 — Unilog Ground-Truth Evaluation, Field Accuracy Metrics, Batch Quality Analytics, and Challenge Dashboard

## Status
Completed

## Objective
Measure labelled-row correctness and whole-batch quality honestly, expose reproducible bounded APIs,
and present the results in an accessible judge-facing Challenge Quality dashboard.

## Challenge Context
Only two of 1,000 official products have labelled 252-column outputs. Labelled accuracy and
unlabelled batch quality must remain visibly separate.

## Scope
Field-aware ground-truth evaluation, semantic attribute metrics, coverage, description compliance,
confidence/review analysis, batch reliability, error prioritization, isolated persistence, JSON
report CLI, APIs, and `/quality` frontend.

## Out of Scope
Crawling, marketplace sourcing, hidden reference data, taxonomy masters, delivery schema changes,
replacement enrichment, deployment, authentication, S3, and score manipulation.

## Existing Dependencies
SPEC-041 ground truth/alignment/schema and SPEC-042 enrichment results, strategy registry,
provenance, batch processing, and descriptions.

## Evaluation Dataset
Accuracy uses two official labelled rows. Batch analytics use all 1,000 generated results.

## Evaluation Semantics
See `docs/challenge/unilog-evaluation-methodology.md`.

## Field Comparison
Exact, safe normalized-only, mismatch, expected missing, unexpected generated, both blank, and not
evaluated are explicit.

## Exact Accuracy
Exact matches divided by populated expected fields. Both blank is excluded.

## Normalized Accuracy
Safe field-aware normalization preserves trademark symbols, punctuation, numbers, and units.

## Coverage
Raw 252-field and supported-strategy coverage are distinct from correctness.

## Blank-Field Semantics
Expected missing and unexpected generated are separate. External-only blanks are expected.

## Manufacturer / Brand Metrics
Exact, mismatch, and blank counts are displayed as sample counts, not statistical percentages alone.

## Classification Metrics
Classpath and group metrics are evaluated only where official labels exist.

## Attribute Metrics
Position-sensitive cells plus slot-independent semantic precision, recall, F1, and label/value/UOM/
triple metrics.

## Description Compliance
Invoice case/length, mobile preferred length, grounding, numeric traceability, duplicate warnings,
and deterministic unsupported-fact violations.

## Confidence Metrics
Average, median, and high/medium/low deterministic score bands.

## Review Metrics
Count, rate, and actual reason-code breakdown; review is not failure.

## Batch Quality Metrics
Total, processed, failed, coverage distribution, strategy coverage, and blank supported fields.

## Field Error Analysis
Frequency × importance × fixability produces transparent priority and rule-based recommendations.

## Evaluation Persistence
Evaluation results live in a separate repository and never mutate enrichment or Product artifacts.

## Evaluation APIs
Explicit create/read, summary, bounded field metrics, stable labelled-row comparison, and batch
analytics endpoints.

## Challenge Dashboard
Real `/quality` page with context, KPIs, breakdowns, comparison filters, and non-misleading copy.

## Responsive Behaviour
Two-column desktop, stacked tablet, single-column mobile, and comparison cards on narrow screens.

## Accessibility
Textual chart labels, non-color-only statuses, keyboard controls, semantic tables, and labelled
filters.

## Testing
Domain, comparator, attributes, compliance, batch, API, dashboard, responsive, accessibility, and
anti-inflation tests.

## Acceptance Criteria
All authoritative SPEC-043 criteria must pass before completion.

## Completion Record
Completed on 2026-08-21. The deterministic official run evaluated 2 labelled products and all
1,000 input rows without exposing expected values to enrichment. It produced 16 exact matches,
0 normalized-only matches, 12 mismatches, 106 expected values missing from generated output,
2 unexpected generated values, and 368 both-blank comparisons across a 134-field populated-expected
denominator. Batch results were 1,000 processed, 0 failed, 100% review-required, 3.13% raw delivery
coverage, 3.83% supported-field coverage, 98.91% average confidence score, 100% description
grounding, and 0 deterministic unsupported-fact violations.

The backend provides isolated evaluation models/persistence, field-aware and semantic attribute
comparison, coverage/compliance/review/reliability analytics, deterministic error recommendations,
bounded APIs, and a reproducible JSON CLI report. The `/quality` dashboard provides honest KPI
context, analytical sections, labelled-row comparison, responsive cards, accessible controls, and
loading/empty/error states.

Verification passed: 1,704 backend tests and 18 opt-in skips with 90.58% coverage; Ruff lint and
formatting; strict mypy across 359 source files; 49 frontend tests; ESLint; Prettier; a 1,252-module
Vite production build; Docker Compose validation; Git whitespace validation; repeat-run report hash
equality; and visual QA at 1440x900, 1280x800, 1024x768, 768x1024, and 390x844. No crawler,
fabricated reference source, delivery-schema change, expected-answer lookup, deployment, or unrelated
feature was added.
