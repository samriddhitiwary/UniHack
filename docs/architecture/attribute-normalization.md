# Attribute and Unit Normalization

SPEC-024 consumes one explicitly identified SPEC-023 extraction result. Its
product-level `ATTRIBUTE_NORMALIZATION` job stores `attributeExtractionId` and
has no source ID. Before RUNNING, orchestration verifies the product, same-product
extraction, exact category/schema version, and extraction schema fingerprint.

## Raw and canonical candidates

Every input candidate produces exactly one ordered normalized candidate. Raw
value, raw unit, source candidate/extraction/classification IDs, category,
schema lineage, evidence source/type/location/excerpt, and extraction confidence
remain unchanged. Equivalent canonical values and conflicts stay as separate
records; the engine does not compare them or select a winner.

Numbers use `Decimal`, never float. Plain canonical strings remove redundant
plus signs, zeroes, and negative zero. Conversion results exceeding the
configured decimal-place limit are rounded with `ROUND_HALF_UP`; exact values
are not rounded early. Fractional INTEGER values are invalid and decimal commas
are not inferred.

Text receives whitespace and line-ending cleanup while preserving technical
case, except conservative IP rating, insulation class, and duty rules. Boolean
tokens map exactly to `true` or `false`. ENUM values match only declared allowed
values; unknown text remains raw.

## Canonical units and conversions

The fixed registry is limited to existing motor/pump schemas:

- power: kW; W × 0.001, mechanical hp × 0.745699872
- voltage/current/frequency/speed/percentage: V, A, Hz, rpm, %
- flow: m3/h; L/min × 0.06, US gpm × 0.22712470704
- head/NPSH: m; ft × 0.3048
- connection and diameter: mm; in × 25.4
- pressure: bar; psi × 0.0689475729

Aliases are deterministic and schema compatibility is checked before conversion.
Missing units are never guessed. Unsupported units and malformed values are
preserved as candidate warning outcomes rather than failing the job. The engine
does not apply schema business ranges or patterns to product values.

## Persistence and lifecycle

`attribute-normalization-results` uses `normalizationId`/`recordKey`, with one
`META` record and ordered `CANDIDATE#000001` records. The sparse `JobIdIndex`
uses `jobId`/`createdAt`. Writes are conditional and bounded below 390 KB;
retrieval paginates complete partitions and uses consistent ID reads.

The result is stored before the job completes at 100% with
`attribute-normalization-results/{normalizationId}`. Post-start technical errors
attempt FAILED. If the final completion write fails, the valid result remains
and a consistency-risk event is logged.
