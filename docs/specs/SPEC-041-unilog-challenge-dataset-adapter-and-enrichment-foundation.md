# SPEC-041 — Unilog Challenge Dataset Adapter, Exact Delivery Schema, Input Cleansing, Ground-Truth Learning, and Enrichment Foundation

## Status

Completed

## Objective

Create a deterministic adapter around the two official Unilog challenge CSVs without inventing unavailable reference masters or final enriched content.

## Challenge Context

The challenge supplies messy distributor rows and an immutable 252-column delivery contract with two representative labelled outputs.

## Authoritative Inputs

- `Unihack_ Sample Dataset - Input (1).csv`
- `Unihack_ Expected Output - Delivery Format.csv`
- Written challenge guidance embedded in SPEC-041

No manufacturer master, LOV, UOM, Faucets/Fittings, or internal-guideline workbook is available.

## Scope

Input ingestion, exact schema validation, placeholder cleansing, manufacturer parsing, brand evidence, deterministic row identity/alignment, ground-truth structures, observed vocabulary, provenance/confidence/review semantics, enrichment interfaces, and an explicit import artifact.

## Out of Scope

Final enrichment, description generation, external retrieval, web crawling, marketplace sourcing, Excel writing, accuracy dashboards, frontend changes, authentication, and deployment.

## Input Dataset Profile

The official CSV contains 1,000 data rows and six exact ordered headers. Raw part numbers, descriptions, brands, and manufacturer strings remain unchanged alongside cleaned/parsed forms.

## Expected Output Profile

The official CSV contains 252 exact ordered headers and two labelled rows. Both labelled rows uniquely align to input through `Mfg_Part_Num`.

## Input Domain Model

Immutable rows include a dataset-scoped deterministic row ID, source row number, raw evidence, cleaned brand values, parsed manufacturer text, and an optional final parenthesized source-reference code.

## Output Schema Contract

`UNILOG_DELIVERY_HEADERS` preserves exact spelling and order. Records reject unknown, duplicate, missing, or reordered fields. Internal metadata never enters the submission schema.

## Placeholder Cleansing

Known organizer placeholders and blank values become `None`; meaningful evidence is trimmed but otherwise preserved.

## Manufacturer Parsing

Only an unambiguous final parenthesized token is separated. Earlier parentheses remain part of the manufacturer name, and canonical legal names are never invented.

## Brand Evidence

E1, Unilog, and DIB values remain separate evidence sources. Description text is retained as weaker candidate evidence and is never promoted automatically to manufacturer identity.

## Ground-Truth Alignment

Alignment uses exact `Mfg_Part_Num` indexing. Zero matches remain unaligned; multiple matches produce an explicit ambiguous issue. No row-ID answer lookup is exposed to enrichment interfaces.

## Field Provenance

Each proposed field value carries source type, reference, method, evidence strength, confidence basis points, and review requirement.

## Confidence Model

Confidence is a deterministic 0–10,000 similarity/evidence score, not a statistical probability.

## Human Review Model

Conflicts, ambiguity, unsupported inference, and insufficient corroboration set `review_required` rather than guessing.

## Manufacturer Resolution Foundation

A protocol and evidence-only implementation expose supplier manufacturer and brand evidence without pretending it is a complete canonical master.

## Classification Foundation

A protocol reserves classpath classification while forbidding unsupported taxonomy values.

## Attribute Enrichment Foundation

Ordered candidate triples are bounded to 50 and item features to 20. Mapping helpers target exact delivery headers.

## External Evidence Boundary

A manufacturer-evidence provider protocol is defined; no network retrieval is implemented.

## Non-Hallucination Rules

Populated values require raw input, official labelled output, deterministic parsing, official future manufacturer evidence, validated inference, or human review. Unsupported fields remain blank and reviewable.

## Persistence

Challenge imports serialize to a separate deterministic JSON artifact and can be loaded into an indexed repository. Existing Product records remain unchanged.

## APIs / Service Interfaces

No public API is added. Internal protocols cover manufacturer, brand, classification, attributes, descriptions, and future manufacturer evidence.

## Error Handling

Missing files, schema mismatch, unsafe size limits, malformed rows, ambiguous alignment, and import failure use controlled challenge-specific exceptions or result statuses.

## Testing

Tests cover real schema shapes, 1,000-row ingestion, placeholders, parsing, schema ordering, blank semantics, alignment, provenance, observed vocabulary, repository indexes, malformed inputs, and deterministic imports.

## Acceptance Criteria

All 118 controlling SPEC-041 acceptance criteria must pass without SPEC-042 or frontend implementation.

## Completion Record

Completed on 2026-08-21. The two official CSV artifacts were profiled and imported through a
bounded deterministic adapter. All 252 delivery headers are preserved exactly and in order; 1,000
input rows and two labelled output rows import successfully, with both labels uniquely aligned.

Verification: 1,658 backend tests passed with 16 skipped and 90.15% coverage; 44 frontend tests
passed. Ruff lint/format, strict mypy, ESLint, Prettier, Vite build, Docker Compose validation, and
Git whitespace validation passed. No frontend, final enrichment, external retrieval, or delivery
writer was added.
