# Unilog Observed Attribute Vocabulary

This vocabulary describes evidence in the supplied challenge artifacts. It is not a complete Unilog
production attribute, LOV, or UOM master.

The two labelled dishwasher outputs contain 15 recurring official labels and four UOMs: `V`, `A`,
`in`, and `dBA`. Definitions store normalized labels, bounded observed values, observed UOMs,
observed product types, support count, and source. Six reviewed mappings connect semantic candidates
to observed labels: Series, Material, Dimensions→Size, Voltage Rating, Amperage Rating, and Sound
Level. Unknown names such as Grit, Package Quantity, Horsepower, and individual Sanding Belt Width or
Length stay internal because no official label was supplied for them.

The normalizer safely handles exact challenge forms and reviewed aliases for inches plus explicit V,
A, dBA, ft, mm, psi, HP, and Hz. This table is deliberately small and makes no completeness claim.
Fractions remain exact. Values are changed only through deterministic equivalence.

Fifteen compact product-type rules prioritize the dataset's useful abrasive, decking/fascia, rail,
and dishwasher contexts. Sanding Belt alone has a width/length orientation rule. Grit requires an
abrasive context. Generic explicit multi-dimensions may map to `Size`, but unknown orientation never
becomes Width or Length. Quantities stay semantic attributes and never become commercial Selling Qty.

Equal candidates collapse; conflicting values are reviewed and omitted from delivery. Official
triples require label plus value and are capped at 50. Runtime uses cached indexes and never rebuilds
the artifact or calls a network service per row.
