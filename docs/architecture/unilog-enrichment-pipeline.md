# Unilog Evidence-Grounded Enrichment Pipeline

## Boundary

The challenge enrichment aggregate is separate from CatalogIQ `Product`. It produces an isolated
`UnilogEnrichmentResult` containing the exact delivery record plus internal resolutions,
provenance, confidence, coverage, warnings, and review state. Internal metadata never enters the
challenge CSV.

## Flow

```text
UnilogChallengeInputRow
  -> conservative cleansing and SPEC-041 manufacturer parse
  -> brand evidence and supplier-aware manufacturer resolution
  -> description signal extraction with exact source spans
  -> observed-vocabulary-constrained classification
  -> semantic attributes and exact trade-fraction measurements
  -> duplicate/conflict resolution
  -> trusted fact set
  -> deterministic description and feature construction
  -> field resolutions with provenance/confidence
  -> exact 252-column assembly and validation
```

`UnilogEnrichmentService.enrich_row` is deterministic without a configured model. The identity is
SHA-256 over input row identity, policy version, and the deterministic provider/model identity.
The policy version is `unilog-enrichment-policy-v1`.

## Resolvers

Brand fields remain distinct through cleansing. A single normalized candidate resolves; multiple
candidates conflict. A description match to observed vocabulary remains weaker and reviewable.
Manufacturer resolution rejects supplier-like terms such as dealer, distributor, cooperative, or
industrial supply. Manufacturer and brand disagreement also remains ambiguous.

## Classification and Attributes

Product type is an explicit noun phrase found in `Part_Desc`. An official `Classpath` is emitted
only when an exact observed path has a deterministic product-type rule. Unknown product types do
not create taxonomy paths.

Measurements use `Fraction`; `1/2`, `3/8`, `1-1/4`, and `50-1/4` remain exact. Quotation marks are
inches only when attached to dimensions. Unmarked `A x B` requires an explicit product convention.
SPEC-042 implements sanding-belt width/length only. Semantic attributes without an observed
official label remain internal.

## Descriptions and Features

Builders consume only trusted facts. `INVOICE_DESC` is uppercase and at most 40 characters, using
field-priority removal instead of slicing. `MOBILE_DESC` prefers 60–80 characters; a shorter
grounded result receives a format warning rather than filler. Numeric and risky marketing claims
are validated. Features restate attributes and retain fact IDs; at most 20 are assembled.

## Optional Model Boundary

The optional signal assistant can propose only product type and attribute source spans. It uses
strict JSON, validates every proposed value against `Part_Desc`, and stops after two attempts. It
cannot see labelled row answers and does not populate final fields by itself. Failure returns to
the deterministic path.

## Batch and CSV

`UnilogBatchEnrichmentService` accepts at most 1,000 rows, preserves order, and isolates failures.
Statistics distinguish success, review-required, and failed rows and report average populated
fields and confidence. The writer uses UTF-8, LF newlines, canonical header order, minimal
deterministic quoting, and empty cells for missing values.
