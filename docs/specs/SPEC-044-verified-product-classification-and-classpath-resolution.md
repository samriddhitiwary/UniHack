# SPEC-044 — Verified Product Classification Vocabulary Expansion and Evidence-Grounded Classpath Resolution

## Status
Completed

## Objective
Resolve evidence-supported product types across the official challenge dataset while populating an
official Unilog Classpath only from a verified general mapping.

## Challenge Context
SPEC-043 reported classification uncertainty on all 1,000 rows and only 2 of 10 exact labelled
classification fields. The official input has 1,000 rows and 998 unique descriptions; the expected
output contains two labelled dishwasher products.

## Existing Classification Limitations
SPEC-042 recognized a short fixed list and could not reuse a persisted description vocabulary.
Classpath handling depended on vocabulary passed after enrichment, so the non-leaking evaluation
correctly left it blank.

## Scope
Dataset analysis, deterministic vocabulary persistence, product-type/variant resolution, bounded
abbreviation evidence, optional model-candidate validation, verified Classpath mapping, enrichment,
evaluation metrics, and a minimal `/quality` extension.

## Out of Scope
Web crawling, marketplace sourcing, taxonomy scraping, fabricated taxonomy, attribute overhaul,
manufacturer/brand overhaul, manual review UI, authentication, deployment, and schema changes.

## Dataset Analysis
The offline build processed all 1,000 rows, including both distinct `AVM6EV` rows. It found 998
unique descriptions, 190 bounded candidates, 90 canonical observed types, 99 observed variants,
five verified abbreviations, one ambiguous abbreviation, and one official Classpath mapping.

## Product Type Definition
A plain description-supported answer to “what is this item?”, such as `Sanding Belt`.

## Product Family Definition
An optional broader grouping, such as `Abrasives`. It is internal and never treated as Classpath.

## Official Classpath Definition
A delivery taxonomy value available only through an official-labelled or human-verified mapping.

## Vocabulary Discovery
Reviewed phrase policies are applied to every description. Only phrases actually present in the
input become artifact entries; legacy SPEC-042 deterministic terms remain a compatibility fallback.

## Phrase Extraction
Bounded noun-phrase rules retain row counts, source evidence, brand/manufacturer support, and up to
three examples. Nested observed phrases are counted without collapsing different product types.

## Phrase Normalization
Lookup uses case folding, whitespace collapse, and safe punctuation separators. Meaningful tokens
are preserved, so a saw blade is not reduced to a generic blade.

## Variant Resolution
Observed variants share one canonical type. Longest evidence wins; equal support for distinct
canonical types returns an ambiguous result instead of first-match selection.

## Abbreviation Resolution
Only dataset-observed contextual forms are stored. Five expansions are verified; the observed
`Cand` expansion remains explicitly ambiguous.

## Product Type Resolution
The runtime builds direct indexes once from the bundled artifact, returns the exact description
span, method, separate confidence, candidates, and review reasons, and performs no network call.

## Model-Assisted Product-Type Extraction
Optional strict JSON accepts only `productType` and `evidenceText`. Evidence must be an exact source
substring and must directly contain the proposed type; unsupported specificity is rejected.

## Official Classpath Resolution
The official dishwasher labels yield one general type mapping. It applies by resolved product type,
never MPN or row ID. A model-only type is barred from Classpath even when its text matches a mapping.

## Verification Rules
Mapping source, support count, verified flag, and confidence are mandatory. Unknown and conflicting
taxonomy evidence leaves all taxonomy fields blank.

## Confidence
Product-type and Classpath confidences are independent basis-point values. A confident type does not
raise taxonomy confidence.

## Review Semantics
The six stable reasons distinguish unknown, ambiguous, and generic types from unknown, weak, and
conflicting Classpath mappings. Existing aggregate classification warning behavior is preserved.

## Enrichment Integration
The existing signal extractor now composes the indexed resolver. Resolved types ground Product Name
and the six descriptions. The reviewed Sanding Belt rule retains width/length interpretation.
Verified mappings populate Dept, Class, Fine, and Classpath through observed-mapping provenance.

## Evaluation Integration
SPEC-043 now reports product-type coverage, unresolved count, verified Classpath coverage,
classification review rate/reasons, and top ten product types. These are coverage metrics, not
accuracy claims for unlabelled rows.

## Dashboard Integration
`/quality` adds one responsive, text-labelled card for product-type coverage, verified Classpath
coverage, review reasons, and the top observed product types.

## Persistence
`unilog_classification_v1.json` is a deterministic bundled reference artifact with input hash,
policy version, vocabulary hash, bounded evidence, mappings, unresolved candidates, and statistics.
It is loaded and cached; API startup does not rebuild it.

## Error Handling
Ordinary unknown classification is a reviewable domain result, not an infrastructure exception.
Invalid or missing artifacts fail explicitly during resolver construction.

## Testing
Tests cover representative real descriptions, normalization, variants, abbreviations, generic and
unknown terms, collisions, strict model evidence, hallucination rejection, verified mappings,
model-only Classpath rejection, duplicate-row counts, deterministic hashes, integration, evaluation,
API serialization, and dashboard rendering.

## Acceptance Criteria
All 100 authoritative acceptance criteria are satisfied and the exact 252-column contract is
unchanged.

## Completion Record
Completed 2026-08-21. The official after-run resolved 591 product types, left 409 unresolved,
populated verified Classpaths for 10 dishwasher rows, and reduced classification-specific review to
990 rows. Average populated fields rose from 7.89 to 11.94; supported coverage from 3.83% to 5.80%;
constructed descriptions from 1.70% to 59.10%; attribute-derived coverage remained 0.13%. Both
official labelled products generated `Dishwasher` and their exact official Classpath; labelled
classification improved from 2/10 to 10/10 exact. Two labels are not statistically robust.

Verification passed with 1,712 backend tests and 18 opt-in skips at 90.43% coverage; Ruff lint and
format checks; strict mypy; 49 frontend tests; ESLint; Prettier; a 1,253-module Vite build; Docker
Compose validation; Git whitespace validation; repeatable official evaluation; and Chromium visual
QA at 1440x900, 1280x800, 1024x768, 768x1024, and 390x844.
