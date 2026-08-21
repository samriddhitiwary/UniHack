# SPEC-042 — Evidence-Grounded Unilog Product Enrichment, Description Construction, and Exact Delivery Record Generation

## Status
Completed

## Objective
Transform official challenge input rows into trustworthy, partially populated, exact 252-column
delivery records without inventing unavailable product facts.

## Challenge Context
The official input has 1,000 six-column rows. The official labelled delivery file has two rows and
252 immutable headers. Those rows provide incomplete vocabulary and examples, not a hidden answer
source.

## Scope
Single-row and bounded batch enrichment, deterministic signal extraction, resolution,
classification, attributes, descriptions, delivery assembly, validation, isolated result storage,
CLI execution, and exact CSV export.

## Out of Scope
Evaluation dashboard, judge-facing analytics, crawling/scraping, asset discovery, authentication,
S3, deployment, frontend screens, fabricated masters, and row-specific expected-answer lookup.

## Existing Dependencies
SPEC-041 input/delivery domains, cleansing, manufacturer parsing, observed vocabulary, provenance,
comparison, CSV parsing, and separate challenge repository. CatalogIQ grounding concepts are
reused where their fact-transformation semantics match.

## Enrichment Pipeline
Input → cleansing → manufacturer/brand evidence → description signals → product type/classification
→ attribute/measurement candidates → conflicts → field resolution → descriptions → assembly →
252-column validation.

## Field Population Strategy
The central registry covers each exact header. See
`docs/challenge/unilog-field-population-strategy.md`.

## Direct Fields
Seven semantically safe input mappings are exact copies. Customer/internal part identifiers remain
blank because they are not assumed equal to MPN.

## Manufacturer and Brand Resolution
Placeholder brands are excluded. Normalized agreement can resolve a brand. Supplier-like
`Part_Manuf` evidence and manufacturer/brand disagreement remain ambiguous and review-required.

## Product Classification
Product type comes from explicit description noun phrases. Classpath must be an exact observed path
with a supported general rule; unknown taxonomy remains blank.

## Attribute Extraction
Candidates preserve raw spans, exact normalized value, unit, confidence, and fact identity.
Unknown official labels remain internal. Duplicate equal values collapse and conflicts require
review.

## Attribute Normalization
Trade fractions use exact `Fraction` representation. Attached quotation marks normalize to inches;
unmarked dimensions require explicit product context.

## Description Construction
Product Name, invoice, mobile, short, long, retail, and marketing fields are deterministic trusted
fact transformations. Invoice is uppercase and ≤40; mobile prefers 60–80 without fabricated
padding.

## Item Features
Up to 20 features may restate validated attributes. Features retain fact IDs and cannot introduce
marketing or performance claims.

## Commercial Fields
Prices, selling semantics, warranty, and identifiers remain blank without direct trusted evidence.
Packaging candidates are not automatically Selling Qty.

## Dimensions and Measurements
Dimensions populate only when orientation is explicit. V1 supports width/length for a recognized
sanding-belt `A x B` convention; other measurements remain semantic candidates.

## Asset and Reference Fields
All asset and URL fields remain blank unless an actual verified source exists. No URL or filename
is synthesized.

## Provenance
Every populated resolution has field, value, evidence source/reference, method, strength,
confidence, and review state.

## Confidence
Overall confidence averages populated fields only. Coverage separately reports populated,
supported, and total fields; blanks do not inflate confidence.

## Human Review
Ambiguous manufacturer/brand, unknown classification, conflicts, low-confidence values, and
description validation warnings require review while still allowing partial output.

## Delivery Record Assembly
The assembler accepts validated resolutions and creates `UnilogDeliveryRecord`; internal metadata
stays in `UnilogEnrichmentResult`.

## Delivery Schema Validation
Exactly 252 unique headers, exact order, triple integrity, invoice format, and blank sentinel rules
are enforced before export.

## Batch Processing
Maximum 1,000 rows, input order preserved, failures isolated, and transparent statistics returned.

## CSV Export
UTF-8, LF newline, deterministic minimal quoting, canonical headers, and empty cells. No internal
fields are exported.

## Error Handling
Invalid field output becomes blank with a warning. Unexpected row failures are isolated in batch
status. Optional model failure falls back deterministically.

## Determinism
Policy v1 uses stable ordering, exact fractions, bounded rules, and SHA-256 request identity.

## Non-Hallucination Rules
Populate only from raw input, deterministic parsing, general official labelled patterns, validated
model source spans, official sources, or human review. Never infer UPC/EAN/GTIN/UNSPSC, warranty,
origin, assets, URLs, prices, certifications, or unknown taxonomy.

## Testing
Unit and integration tests cover signals, fractions, resolvers, classification, attributes,
descriptions, grounding, provenance, confidence, review, exact schema, CSV, batch isolation,
idempotency, optional model bounds, anti-leakage, and labelled regression.

## Acceptance Criteria
All 137 criteria in the authoritative request must pass or be documented as deliberately blank
under the non-hallucination policy.

## Completion Record
Completed on 2026-08-21. The official 1,000-row CLI run enriched all rows without a failed row;
all rows remain review-required under the conservative v1 policy because the available input and
two-row vocabulary cannot safely resolve every manufacturer/classification. The delivery writer
produced 1,000 ordered rows with 252 exact headers.

Labelled regression deliberately does not target full equality:

| MPN | Exact | Normalized | Mismatch | Generated blank for labelled value | Both blank | Generated value where label blank |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `PDSH4816AF` | 9 | 0 | 7 | 47 | 187 | 2 |
| `WDTS7024RZ` | 9 | 0 | 9 | 53 | 181 | 0 |

The mismatches are conservative factual constructions or attribute-position differences. Generated
blanks primarily represent external product facts that cannot be derived from the six-column input.

Verification: 1,691 backend tests passed, 16 intentionally skipped, coverage 90.30%; Ruff lint and
format, strict mypy over 343 source files, 44 frontend tests, ESLint, Prettier, Vite production build
(1,233 modules), Docker Compose validation, and Git whitespace validation all passed.
