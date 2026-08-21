# SPEC-046 — Manufacturer and Brand Evidence Resolution Expansion

## Status
Completed

## Objective
Resolve manufacturer and brand independently from supplied challenge evidence while preserving a
separate supplier/source-organization role. No external lookup or invented canonical master is used.

## Dataset Analysis
The 1,000 rows contain 76 normalized raw `Part_Manuf` values: 75 valid organizations plus the `-`
missing marker. Five organizations contain dataset-observed supplier terms and cover 222 rows.
Organizer fields provide 446 non-placeholder brand rows and 35 distinct observed brand spellings.
That evidence comprises 201 E1 rows, zero Unilog rows, and 245 DIB rows. The incomplete artifact
contains 52 observed manufacturer entries, 37 observed brand entries including the two reusable
labelled values, 28 manufacturer-to-brand relations, and five supplier-to-brand relations.
The artifact records two repeated description-leading brand candidates and 33 repeated MPN-prefix
groups; only prefixes with at least three rows and one corroborated brand can resolve.

## Evidence Policy
Official reusable labelled vocabulary ranks first, followed by consistent organizer brand fields,
repeated description-leading evidence, repeated row relationships, supported MPN prefixes, validated
model candidates, then unresolved. Organizer brand conflicts are never majority-voted. Product type
may reject generic phrases but never creates an identity.

## Supplier and Manufacturer
Supplier-likeness uses only observed terms: supply, industrial supply, distribution/distributor,
wholesale, sales, dealer/dealers, cooperative, building materials, and lumber. It is negative role
evidence, not a universal statement about an organization. Supplier-only rows retain the parsed
organization internally and leave `MANUFACTURER_NAME` blank. A manufacturer requires repeated exact
organizer evidence plus role evidence, direct brand agreement, or a sufficiently supported consistent
relationship. Ambiguous roles remain blank.

## Brand Resolution
Non-placeholder E1, Unilog, and DIB values retain their organizer spelling. Repeated leading phrases,
MPN prefixes, and organization-brand relationships may corroborate a brand already in the observed
challenge vocabulary. Brand can resolve while manufacturer remains blank. `TRADE_NAME` is untouched.

## Relationships
Manufacturer→brand, brand→manufacturer, and supplier→brand counts preserve many-to-many evidence.
They support resolution but never assert corporate ownership or force a one-to-one mapping.

## Model Boundary
Optional JSON candidates require an exact description span, observed vocabulary, and repeated
dataset support for every proposed manufacturer or brand. They remain review-required semantic
evidence and cannot directly populate delivery identity fields. No live model is required.

## Before and After

| Metric | Before | After |
| --- | ---: | ---: |
| Manufacturer resolved | 82 | 482 |
| Manufacturer ambiguous | 918 | 255 |
| Brand resolved | 446 | 599 |
| Brand ambiguous | 0 | 0 |
| Supplier-only rows | 0 separately identified | 222 |
| Overall review-required | 1,000 | 1,000 |
| Average populated fields | 12.99 | 13.54 |
| Supported-field coverage | 6.30% | 6.57% |
| Constructed-description coverage | 59.10% | 59.10% |

The two labelled rows remain 0/2 exact for both manufacturer and brand because their supplied source
fields contain only a supplier organization and brand placeholders. Their external expected identity
values are not recoverable without prohibited row-specific or external lookup.

After resolution, identity review reasons are: brand unresolved 401, manufacturer ambiguous 255,
organization role ambiguous 255, supplier-only evidence 222, MPN-prefix weak 44, and manufacturer
unresolved 41. Calibrated overall confidence is 89.79% average and 89.94% median, with 469 high and
531 medium-confidence rows rather than the previous all-high distribution.

## Regression Safety
Classification remains 10/10 exact, semantic attribute precision remains 100%, description grounding
remains 100% with zero unsupported facts, the exact 252-column contract is unchanged, and all 1,000
rows complete with zero failures.

## Limitations
This is incomplete challenge-observed evidence, not a manufacturer, trademark, brand, or ownership
master. Supplier and manufacturer roles can remain ambiguous without external verification.
