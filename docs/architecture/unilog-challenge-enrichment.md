# Unilog Challenge Enrichment Architecture

SPEC-042 implements the evidence-grounded enrichment stage described in
`docs/architecture/unilog-enrichment-pipeline.md`. The SPEC-041 adapter and exact schema remain the
foundation; delivery enrichment remains isolated from the generic Product aggregate.

```text
Official input CSV
       ↓
Bounded challenge adapter
       ↓
Raw evidence + placeholder cleansing + manufacturer parsing
       ↓
Manufacturer / brand / classification / attribute interfaces
       ↓
Provenance + confidence basis points + review semantics
       ↓
Exact 252-column delivery-record contract
```

The adapter is isolated from CatalogIQ's existing Product aggregate. It neither mutates `Product.category` nor overwrites `Product.manufacturer`.

The expected-output CSV is both schema authority and limited labelled evidence. Ground-truth alignment uses an indexed exact part-number join and reports duplicate input candidates as ambiguous. Expected blanks are retained as missing labels, not treated as permanent instructions to keep a field empty.

Observed manufacturers, brands, classpaths, attribute labels, and UOMs are derived only from labelled rows and are explicitly incomplete. Enrichment code cannot retrieve a row's expected answer through its row ID, avoiding a direct leakage path.

Future evidence priority is manufacturer-owned documentation followed by other approved authoritative sources. The external-provider boundary performs no retrieval in SPEC-041, and marketplace data is not treated as authoritative.

Imports are explicit, fingerprinted, idempotent, and written to a challenge-specific JSON artifact. No CSV parsing occurs during API startup and no 252-field expansion is added to existing Product storage.
