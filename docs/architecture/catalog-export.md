# Structured Catalog Export

SPEC-033 turns one explicit immutable SPEC-031 commerce catalog projection into a portable local
publication package. It prepares files only; it does not publish, call marketplaces, expose a
download API, use S3, or mutate Product or projection state.

## Input and eligibility

`CATALOG_EXPORT` is a product-level processing job with `sourceId = null` and a required explicit
`projectionId`. The service accepts only READY or READY_WITH_WARNINGS projections, rejects BLOCKED,
and validates Product ownership, category, schema fingerprint, counts, and attribute bounds before
RUNNING. A later Product version is permitted because the projection is the authoritative immutable
snapshot; current Product identity never replaces projection identity. Current Product category must
still match to detect corrupt cross-category lineage.

## Deterministic package

Every package contains exactly `catalog.json`, `catalog.csv`, and `manifest.json` under
`catalog-exports/{exportId}/`. Canonical JSON uses sorted compact keys, UTF-8 without BOM, one final
LF, stable display-order attributes, warning reasons, and bounded lineage without raw evidence. CSV
uses Python's `csv` module, UTF-8 without BOM, LF records, one product row, fixed identity/projection
columns, display-order canonical attribute columns, schema-unit companion columns, empty optional
values, and `|`-joined warning reasons.

The compact sorted manifest records package version, immutable identities, projection status,
creation time, warning reasons, and JSON/CSV filenames, media types, exact byte sizes, and SHA-256
hashes. It deliberately omits its own checksum to avoid recursion. Result metadata stores the
manifest checksum separately. All hashes are lowercase SHA-256 over the exact bytes passed to
storage.

## Storage, persistence, and consistency

The orchestration service writes through the existing `ObjectStorage` protocol, with
`LocalObjectStorage` used in development; it performs no direct filesystem access. Metadata remains
bounded to the storage provider's safe key, size, checksum, and timestamp sidecar contract.

`catalog-export-results` stores one META and three ARTIFACT records. Sparse JobIdIndex and
ProjectionIdIndex access META records; a conditional `PROJECTION#{projectionId}` guard enforces one
authoritative export per projection. All retrieval uses queries and complete partitions are
validated. Items are limited to 390,000 serialized bytes.

Storage precedes result persistence, which precedes job completion. A partial write or result-create
failure triggers best-effort reverse-order object deletion. Cleanup failures are safely logged. If
job completion fails after the package and result are valid, both are retained and a
`catalog_export.completion_consistency_risk` event is logged.

## Limits and scope

Configured limits bound attributes and JSON, CSV, and manifest bytes. Filenames and keys are
server-generated and path-safe. SPEC-033 adds no external publication, marketplace adapter,
XLSX/XML, network delivery, S3, AI enrichment, frontend, authentication, authorization, or
deployment behavior.
