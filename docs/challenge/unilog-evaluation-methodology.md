# Unilog Evaluation Methodology

## Evaluation Populations

Ground-truth accuracy uses only the two officially labelled products: `PDSH4816AF` and
`WDTS7024RZ`. It is indicative development evidence, not a statistically robust challenge score.
Batch quality uses all 1,000 official input rows and measures coverage, confidence, review burden,
rule compliance, and processing reliability. It does not measure correctness.

Expected output is loaded only after enrichment completes. Enrichment receives raw input and the
general observed vocabulary, never the expected record for the row being enriched.

## Field Comparison

Statuses are mutually exclusive:

- `EXACT_MATCH`: identical string value, including case, punctuation, numbers, units, and trademark
  symbols.
- `NORMALIZED_MATCH`: only a field-approved normalization makes two populated values equal.
- `MISMATCH`: both populated and unequal.
- `EXPECTED_POPULATED_ACTUAL_BLANK`: expected content is missing from generated output.
- `EXPECTED_BLANK_ACTUAL_POPULATED`: generated content has no official labelled counterpart. This
  is reported separately and is not automatically called incorrect.
- `BOTH_BLANK`: both empty; excluded from content-accuracy numerator and denominator.
- `NOT_EVALUATED`: the field cannot be evaluated under the selected policy.

Safe normalization trims outer whitespace, converts CRLF/CR to LF, and collapses repeated
whitespace. Case-folding is limited to names, classification text, and non-invoice descriptive
text. It never removes trademark symbols, punctuation, numbers, or units. `INVOICE_DESC` remains
case-sensitive because uppercase is a delivery rule.

The populated-expected denominator is:

```text
EXACT_MATCH + NORMALIZED_MATCH + MISMATCH + EXPECTED_POPULATED_ACTUAL_BLANK
```

`BOTH_BLANK` never inflates accuracy. The current deterministic SPEC-042 regression totals are 16
exact, 0 normalized-only, 12 mismatches, 106 expected-populated/generated-blank, 2
expected-blank/generated-populated, and 368 both blank over 504 compared cells. The evaluable
populated-expected denominator is 134.

## Field Groups

Every canonical header belongs to exactly one group: `IDENTITY`, `CLASSIFICATION`, `DESCRIPTION`,
`FEATURE`, `ATTRIBUTE`, `COMMERCIAL`, `DIMENSION`, `ASSET`, `DOCUMENT`, `REFERENCE`, or `OTHER`.
Group accuracy is reported only when at least one official expected value exists.

Core Enrichment Fields are manufacturer, brand, MPN, classpath, Product Name, mobile, invoice,
short, and long descriptions plus each populated official attribute triple. Core membership is
transparent and creates a filtered view; it does not silently reweight headline accuracy.

## Attribute Evaluation

Position-sensitive metrics compare all 150 official attribute cells in their exact slots. Semantic
metrics parse up to 50 triples and match by safely normalized label regardless of slot. Labels,
values, and units are compared separately. A full triple requires matching label and value plus
matching optional UOM. Precision is correct generated triples divided by generated triples; recall
is recovered expected triples divided by expected triples; F1 is shown only when defined.

## Coverage

Raw row coverage is populated fields divided by 252. Supported-field coverage uses strategies that
SPEC-042 can populate from available evidence: direct, deterministic, observed mapping,
attribute-derived, description-constructed, and validated model-assisted. External-only and
unsupported fields are reported separately because blank values are expected.

Batch coverage reports average populated field count, median, minimum, maximum, per-strategy
coverage, and frequently blank supported fields. Coverage is never called accuracy.

## Description Compliance

Populated `INVOICE_DESC` values are evaluated for uppercase, at most 40 characters, non-empty rate,
and grounding. `MOBILE_DESC` reports preferred 60–80 length, under-60, over-80, and grounding;
under-60 grounded text is a warning, not invalid. Other descriptions report non-empty rate,
grounding, numeric traceability, and duplicate-token warnings.

Unsupported Fact Violations count deterministic validation issues; this is not marketed as perfect
hallucination detection.

## Confidence and Review

Confidence is a deterministic score, not a probability. Bands are High (at least 9000 bp), Medium
(7000–8999 bp), and Low (below 7000 bp). Average and median use row-level overall confidence.
Review rate is review-required rows divided by all processed rows. Reasons are aggregated from
actual warning codes: manufacturer ambiguity, brand ambiguity, classification uncertainty,
attribute conflict, low-confidence field, and description warning.

## Reliability and Improvement Priority

Processing success is `(total - failed) / total`; review is not failure. Timing is omitted unless
measured by the run.

Problem priority is deterministic integer multiplication:

```text
issue count × field importance × fixability
```

Core identity/classification/descriptions use importance 3, attributes 2, and other fields 1.
Missing or mismatched supported fields use fixability 3; normalized-only uses 1; external-only uses
1. Recommendations are fixed rules selected from these metrics, never LLM-generated.
