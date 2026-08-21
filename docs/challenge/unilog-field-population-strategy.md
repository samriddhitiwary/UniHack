# Unilog 252-Field Population Strategy

## Contract

`UNILOG_DELIVERY_HEADERS` is the immutable source of header names and order. The code-level
`UnilogFieldPopulationStrategy` creates one entry for every header and fails at import time unless
there are exactly 252 entries. Each entry contains the field, strategy, possible source,
validation, confidence behavior, and blank behavior. Every unsupported or invalid value becomes
an empty CSV cell.

The registry distribution is:

| Strategy | Exact field count |
| --- | ---: |
| `DIRECT_COPY` | 7 |
| `DETERMINISTIC_PARSE` | 2 |
| `OBSERVED_MAPPING` | 4 |
| `ATTRIBUTE_DERIVED` | 186 |
| `DESCRIPTION_CONSTRUCTED` | 7 |
| `MODEL_ASSISTED` | 0 final fields in v1 |
| `EXTERNAL_ONLY` | 44 |
| `UNSUPPORTED` | 2 |
| **Total** | **252** |

## Strategy Profiles

| Strategy | Possible source | Validation | Confidence behavior | Blank behavior |
| --- | --- | --- | --- | --- |
| `DIRECT_COPY` | Exact official input cell | Semantic mapping and exact MPN preservation | 10000 bp after schema validation | Blank only when the source is blank |
| `DETERMINISTIC_PARSE` | Cleansed/corroborated organizer evidence | Placeholder removal, normalized agreement, supplier distinction | 8500–9500 bp when resolved | Ambiguity is blank and review-required |
| `OBSERVED_MAPPING` | General official labelled pattern/vocabulary | Must be in observed vocabulary; no evaluated-row lookup | At least 9000 bp for an exact rule | Unknown mapping is blank and review-required |
| `ATTRIBUTE_DERIVED` | Parsed description signal or validated attribute | Evidence span, supported label, triple integrity, units, conflicts | At least 8500 bp | Unknown labels/conflicts are retained internally but blank in delivery |
| `DESCRIPTION_CONSTRUCTED` | Trusted resolved facts | Grounding, numeric traceability, duplication, case, length | Minimum input confidence; warnings require review | Invalid construction is blank |
| `MODEL_ASSISTED` | Structured model proposal over trusted input | Strict JSON, exact source spans, two attempts maximum | At least 8500 bp and reviewable | Deterministic fallback; no final field is model-only in v1 |
| `EXTERNAL_ONLY` | Official manufacturer/organizer source or human review | Source and semantic validation plus provenance | Direct trusted evidence only | Blank without the source |
| `UNSUPPORTED` | No safe SPEC-042 source | Population prohibited | No confidence | Always blank |

## Exact Field Matrix

The following rows expand to the exact canonical headers shown. Numbered ranges mean every
individual canonical header in the inclusive range and are enforced individually by the registry.

| Exact field(s) | Count | Strategy | Source and field-specific validation |
| --- | ---: | --- | --- |
| `Mfg_Part_Num`, `Part_Desc`, `E1_Brand`, `Unilog_Brand`, `DIB_Brand`, `Part_Manuf`, `MANUFACTURER_PART_NUMBER` | 7 | `DIRECT_COPY` | Official input; preserve exact text and MPN punctuation |
| `MANUFACTURER_NAME`, `BRAND_NAME` | 2 | `DETERMINISTIC_PARSE` | Corroborated evidence only; supplier conflict and placeholders reject population |
| `Dept`, `Class`, `Fine`, `Classpath` | 4 | `OBSERVED_MAPPING` | Only a general exact official mapping; unknown taxonomy remains blank |
| `Product Name`, `MOBILE_DESC`, `INVOICE_DESC`, `SHORT_DESC`, `LONG_DESC1`, `RETAIL_DESC`, `MARKETING_DESCRIPTION` | 7 | `DESCRIPTION_CONSTRUCTED` | Trusted facts; invoice uppercase and ≤40; mobile 60–80 preferred; all numbers grounded |
| `ITEM_FEATURES_1` through `ITEM_FEATURES_20` | 20 | `ATTRIBUTE_DERIVED` | Up to 20 supported fact restatements, each with fact IDs; no marketing invention |
| `ATTRIBUTE_LABEL 1`, `ATTRIBUTE_VALUE 1`, `ATTRIBUTE_UOM 1` through `ATTRIBUTE_LABEL 50`, `ATTRIBUTE_VALUE 50`, `ATTRIBUTE_UOM 50` | 150 | `ATTRIBUTE_DERIVED` | Observed/validated label, value required with label, optional unit, stable order, maximum 50 |
| `With`, `Standard/Approvals`, `Prop 65`, `Application`, `Includes`, `Standard Packaging Information` | 6 | `ATTRIBUTE_DERIVED` | Populate only when a validated semantic attribute directly supports the field |
| `LENGTH`, `LENGTH_UOM`, `HEIGHT`, `HEIGHT_UOM`, `WIDTH`, `WIDTH_UOM`, `WEIGHT`, `WEIGHT_UOM`, `VOLUME`, `VOLUME_UOM` | 10 | `ATTRIBUTE_DERIVED` | Orientation and unit must be deterministic; v1 implements only explicit sanding-belt width/length convention |
| `MFR URL`, `Ref URL 1` through `Ref URL 5` | 6 | `EXTERNAL_ONLY` | Verified official URL only; never synthesize domains or search links |
| `PART_NUMBER`, `SKU - MY_PART_NUMBER` | 2 | `EXTERNAL_ONLY` | Organizer/customer identifiers are not assumed equal to MPN |
| `UPC`, `EAN`, `GTIN`, `UNSPSC` | 4 | `EXTERNAL_ONLY` | Exact trusted identifier only; never derive from MPN |
| `Warranty`, `List Price`, `Selling Qty`, `Selling UOM` | 4 | `EXTERNAL_ONLY` | Direct commercial evidence only; packaging text is not automatically selling quantity |
| `Product Image`, `Alternate Image 1` through `Alternate Image 4` | 5 | `EXTERNAL_ONLY` | Existing verified asset only; do not create filenames or URLs |
| `SDS`, `SDS_1`, `Warranty Information`, `Catalog`, `Specification Sheet`, `Instruction/Installation Manual`, `Service Manual`, `Owners/User Manual`, `Line Drawing`, `MTR`, `RoHS`, `Full Engineering Drawing`, `Energy Star Guide`, `Technical Bulletin`, `Submittal`, `Compatibility Chart`, `Size Chart`, `Product Label/Insert`, `Video Link`, `Video Link 1` | 20 | `EXTERNAL_ONLY` | Existing verified asset/reference only |
| `Country Of Origin`, `Discontinued`, `Actual Image (Yes/No)` | 3 | `EXTERNAL_ONLY` | Explicit trusted evidence only; never infer from names or description absence |
| `TRADE_NAME`, `ALTERNATE_PART_NUMBER` | 2 | `UNSUPPORTED` | No safe source in SPEC-042 |

The grouped counts above total 252 and map one-to-one to the canonical schema. Tests assert exact
header order, count, per-header registry coverage, no extra field, and empty-cell export behavior.

## Labelled-Row Field Analysis

Both official labelled rows have source input limited to MPN, a short dishwasher description,
placeholder brands, and the supplier-like `Appliance Dealers Cooperative (APPDE)` value.

| Populated labelled field group | Derivation classification | SPEC-042 behavior |
| --- | --- | --- |
| `Mfg_Part_Num`, `Part_Desc`, three raw brand fields, `Part_Manuf` | Direct copy | Copy exactly |
| `MANUFACTURER_PART_NUMBER` | Semantically safe direct mapping from MPN | Copy MPN exactly |
| `MANUFACTURER_NAME`, `BRAND_NAME` | External/ambiguous; not derivable from supplied row | Blank and review-required; the labelled Rheem/Frigidaire combination is not learned as truth |
| `Dept`, `Class`, `Fine`, `Classpath` | Observed general mapping from explicit Dishwasher type | Only `Classpath` is emitted because the exact classpath is observed and type-supported; internal organizer hierarchy IDs remain blank |
| `Product Name` | Deterministic noun phrase | `Dishwasher` |
| Six description fields | Constructed; most labelled facts require external evidence | Build only from MPN, Dishwasher, and deterministic `SS`→Stainless Steel; do not reproduce unsupported cycles, voltage, sound, series, mounting, or marketing claims |
| Attribute labels 1–15 | Observed vocabulary | Used as allowed label vocabulary, not as row answers |
| Attribute values/UOMs | Mostly external facts | Blank except deterministic material from `SS`; label-only triples in official examples are rejected by v1 triple-integrity policy |
| Item features, `With`, approvals | External product facts | Blank without evidence |
| URLs, images, manuals, warranty | External-only | Blank; filenames and URLs are not inferred |
| Remaining blank labelled fields | Unsupported or absent | Stay blank |

## Non-Hallucination and Leakage Boundary

Labelled output contributes only general vocabulary and patterns. The enrichment service accepts
an input row and optional `ObservedVocabulary`; it has no parameter or repository method for the
expected record of that input row. Optional model input includes only raw input and constrained
vocabulary, never expected delivery values. No MPN-specific branch exists.
