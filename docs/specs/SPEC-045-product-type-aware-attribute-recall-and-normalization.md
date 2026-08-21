# SPEC-045 — Product-Type-Aware Attribute Recall Expansion, Measurement Normalization, and Delivery Attribute Population

## Status
Completed

## Objective
Increase source-grounded semantic and official attribute recall using SPEC-044 product types,
deterministic measurement parsing, observed official labels, and conservative mappings while
preserving precision, description grounding, and the exact delivery schema.

## Labelled Attribute Analysis
The two official dishwasher rows contain 30 labelled attribute slots. Their supplied descriptions
are only `Dishwasher SS - Display Only`. `SS` directly supports Material for both rows. No other
value is source-present or safely derivable. Twenty-one populated expected facts are external-only;
seven labelled slots have blank expected values. All 28 non-Material slots remain intentionally
blank during enrichment.

## Scope
Observed label/UOM vocabulary, exact measurements, product-type rules, quantities, grit, materials,
electrical values, semantic candidates, verified label mapping, conflicts, deterministic delivery
slots, evaluation metrics, and a minimal `/quality` extension.

## Out of Scope
Full LOV/UOM masters, taxonomy or marketplace retrieval, manufacturer crawling, broad ontology
design, manufacturer/brand changes, manual review UI, authentication, deployment, and schema changes.

## Domain Separation
Semantic candidates retain source facts even when their official label is unknown. Observed label
definitions describe only the supplied output. Delivery triples require a mapped official label plus
a value; UOM is optional. These concepts never substitute for each other.

## Observed Attribute Vocabulary
The deterministic artifact records 15 official labels, four official UOMs, bounded observed values,
observed dishwasher context, support counts, sources, six semantic mappings, 15 compact product-type
rules, normalization mappings, dataset hashes, policy version, and artifact hash.

## Extraction Rules
Generic rules recognize explicit quantities, materials, voltage, amperage, sound level, pressure,
horsepower, frequency, and dimensional measurements. Grit requires a reviewed abrasive product type.
Sanding Belt resolves width then length; unknown dimension orientation stays as internal numbered
dimensions. Explicit multi-dimensions can map to observed `Size` without claiming orientation.

## Measurement and UOM Normalization
Fractions and mixed fractions use `Fraction`, never binary float. Supported dimensional forms include
two and three values, quotes, inch aliases, feet, and millimetres. Evidence-backed scalar units cover
V, A, dBA, psi, HP, and Hz. Unknown units remain unresolved.

## Label Resolution
Exact observed label, normalized observed label, then explicit semantic mapping are the only routes
to official labels. Unknown semantic names remain internal. Models cannot introduce official labels.

## Confidence and Review
Confidence combines source clarity, product-type interpretation, parsed unit confidence, and label
mapping confidence. Stable reasons cover unknown labels, ambiguous values/units, conflicts, missing
type context, low confidence, and overflow.

## Conflicts and Ordering
Equal normalized semantic values collapse. Different values for one semantic name are all marked for
review and excluded from delivery. Dishwasher slots reuse the observed product-type order; other
attributes follow rule order and stable generic priority. Delivery is capped at 50 triples.

## Model Assistance
Optional strict JSON can propose semantic candidates only. Exact evidence and supported values are
mandatory; unsupported numbers and units are rejected. Candidates still pass normalization, label
mapping, and conflict resolution. No live model is required.

## Enrichment Integration
Trusted attributes populate official triples and can ground existing descriptions. Sanding Belt
width and length also populate dedicated dimension fields. Package quantity never becomes Selling
Qty. The 252 headers remain byte-for-byte unchanged.

## Evaluation and Dashboard
SPEC-043 now reports products with official attributes, average official attributes per product,
semantic candidate counts, unknown labels, conflicts, unit ambiguities, overflow, top official
labels, and review reasons. `/quality` separates all-row coverage from two-row precision/recall.

## Before and After

| Metric | Before | After |
| --- | ---: | ---: |
| Average populated fields | 11.94 | 12.99 |
| Supported-field coverage | 5.80% | 6.30% |
| Attribute-derived coverage | 0.13% | 0.69% |
| Products with at least one official attribute | 0 | 252 |
| Average official attributes/product | 0.00 | 0.25 |
| Semantic attribute recall | 0% | 6.66% |
| Semantic attribute precision | undefined | 100% |
| Label accuracy | 0% | 6.66% |
| Value accuracy | 0% | 6.66% |
| UOM accuracy | 0% | 0% |

The after-run extracted 675 semantic candidates, resolved 258 official triples, retained 417
unknown semantic labels internally, and recorded zero conflicts, unit ambiguities, or overflows.

## Persistence and Runtime
The artifact is built explicitly and written atomically. Cached runtime indexes are keyed by product
type, normalized semantic name, normalized label, and raw UOM. No startup rebuild, scan, network call,
or per-row model request occurs.

## Testing
Tests cover representative challenge examples, fractions, dimensions, quantities, grit, materials,
electrical units, UOMs, unknown labels, duplicates, conflicts, model rejection, artifact round trips,
anti-leakage, delivery slots, evaluation, dashboard behavior, classifications, grounding, and schema.

## Verification
The final gates passed with 1,721 backend tests (18 environment-dependent skips), 90.13% backend
coverage, Ruff lint and format across 597 files, strict mypy across 394 source files, 49 frontend
tests, ESLint, Prettier, Vite production build, Docker Compose validation, and Git whitespace checks.
The responsive quality page was visually inspected at 390x844, 768x1024, 1024x768, 1440x900,
and 1920x1080, plus a full-page desktop capture.

## Completion Record
Completed 2026-08-21. The reproducible official 1,000-row evaluation resolved 258 delivery
attributes across 252 products from 675 semantic candidates. Average populated fields increased
from 11.94 to 12.99, supported-field coverage from 5.80% to 6.30%, and attribute-derived coverage
from 0.13% to 0.69%. On the two labelled products, two source-supported Material triples matched
exactly: 100% semantic precision and 6.66% recall, label accuracy, value accuracy, and triple
accuracy. UOM accuracy is 0% because no source-supported labelled candidate included a UOM.
Classification remained 10/10 and unsupported-fact violations remained zero.
