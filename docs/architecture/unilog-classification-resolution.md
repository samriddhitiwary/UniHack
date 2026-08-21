# Unilog Classification Resolution

```text
Part_Desc
    ↓
Existing description signal extraction
    ↓
Indexed observed phrase / variant / abbreviation resolver
    ↓
Optional strictly validated model candidate
    ↓
Resolved Product Type + optional Product Family + exact evidence span
    ↓
Verified general Product-Type → Classpath mapping
    ↓
Official Dept/Class/Fine/Classpath OR blank
```

The offline builder is the only component that scans the challenge dataset. It writes the versioned
JSON reference artifact atomically. Runtime loads that artifact once, builds direct normalized
variant indexes, and performs bounded in-memory matching without a DynamoDB scan or network request.

The challenge classifier composes this resolver without replacing the generic SPEC-021 classifier.
Product-type confidence and Classpath confidence are independent. The Classpath resolver accepts
only mappings marked verified and sourced from official labelled output or human verification. It
keys mappings by canonical product type, never MPN or row identity. Model-assisted types are always
blocked from directly producing Classpath.

The enrichment pipeline uses the selected type as a grounded fact for Product Name and descriptions.
Only the registry's reviewed Sanding Belt measurement rule interprets first/second dimensions as
width/length. Classification warnings retain specific reasons for evaluation. The evaluation layer
reports coverage and review burden across unlabelled rows and exact results only for official labels.
