# Unilog Product-Type Vocabulary

The SPEC-044 vocabulary is a deterministic snapshot derived from all 1,000 official challenge
descriptions. It is not an official or complete Unilog taxonomy.

The builder evaluates reviewed noun phrases against every `Part_Desc`, safely normalizes case,
spacing, hyphens, slashes, and underscores, and records canonical type, observed variants, row
frequency, optional family, brand/manufacturer evidence counts, source, confidence, and at most
three example descriptions. It does not reduce semantically distinct phrases to a generic head noun.

Abbreviations are accepted only with observed contextual support. `Lt`, `Elect`, `Circ`, `Conn`, and
`Dr` have verified observed contexts; `Cand` remains ambiguous. Unknown expansions are unsupported.
Generic-only terms such as product, part, component, assembly, accessory, replacement, item, and kit
cannot produce a verified Classpath.

Resolution prioritizes explicit phrases, then observed variants/abbreviations, then an optional
strictly validated model proposal, then unresolved. Every resolved type carries the exact source
span. Equal collisions are ambiguous. Product-type confidence measures phrase support only.

Product Type answers what the item is. Product Family is an optional broader internal grouping.
Official Classpath is separate and requires an official-labelled or human-verified mapping. A type
can therefore be high-confidence while its Classpath correctly stays blank.

Artifact statistics: 1,000 rows, 998 unique descriptions, 190 candidates, 90 canonical observed
types, 99 variants, five verified abbreviations, one ambiguous abbreviation, and one verified
Classpath mapping. These counts describe this dataset only and do not imply unlabelled accuracy.
