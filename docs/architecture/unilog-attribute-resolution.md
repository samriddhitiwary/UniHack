# Unilog Attribute Resolution

```text
Part_Desc
   ↓
SPEC-044 resolved Product Type
   ↓
Generic signal extraction + reviewed product-type rules
   ↓
Semantic attribute candidates with exact evidence
   ↓
Fraction / measurement / UOM normalization
   ↓
Observed official label mapping
   ↓
Duplicate collapse + conflict review
   ↓
Observed/rule/generic deterministic ordering
   ↓
ATTRIBUTE_LABEL / VALUE / optional UOM triples
   ↓
Exact 252-column delivery record
```

The offline command aligns the two labelled outputs to inputs only to build general observed label,
UOM, product-type order, and semantic mapping metadata. Runtime never receives expected rows, row
IDs, or MPN answers. It loads one immutable artifact and builds direct indexes by normalized label,
semantic name, raw UOM, and product type.

Candidate evidence is independent of delivery eligibility. Unknown official labels remain useful for
grounded descriptions and review analytics but cannot enter attribute columns. Model proposals use
the same boundary and cannot bypass normalization or mappings. Conflicting values are never selected.

All-row attribute coverage is reported separately from labelled precision and recall. The dashboard
does not describe unlabelled coverage as accuracy.
