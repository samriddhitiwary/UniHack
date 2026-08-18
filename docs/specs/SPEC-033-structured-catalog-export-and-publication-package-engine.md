# SPEC-033 — Structured Catalog Export and Publication Package Engine

## Status
Completed

## Objective
Generate one immutable, portable, deterministic JSON/CSV/manifest package from an explicit eligible
SPEC-031 catalog projection without publishing it externally.

## User Story
As a downstream catalog integrator, I need stable files and verified checksums representing a
reviewed projection so a future delivery workflow can consume them safely.

## Scope
Product-level export jobs, deterministic serializers/package building, local ObjectStorage writes,
immutable result metadata, DynamoDB access patterns, compensation, tests, and documentation.

## Out of Scope
External publication, marketplace adapters, feeds, FTP, webhooks, downloads, XLSX/XML, S3, AI,
content generation, search, frontend, authentication, authorization, and deployment.

## Functional Requirements
Load an explicit projection and Product, validate ownership/category/eligibility, build exactly
three artifacts, store them in deterministic order, persist immutable metadata, and complete the job.

## Non-Functional Requirements
Byte-deterministic UTF-8 serialization, exact SHA-256, fixed names/keys, bounded inputs and outputs,
no scans, conditional uniqueness, immutable upstream data, safe logging, and compensation.

## Existing Dependencies
SPEC-008 ObjectStorage, existing SHA-256 conventions, SPEC-018 standard-library CSV handling,
SPEC-031 immutable projections, SPEC-032 readiness meaning, and processing-job/repository patterns.

## Export Input
One PENDING product-level CATALOG_EXPORT job containing an explicit `projectionId`; no latest lookup.

## Export Eligibility
READY and READY_WITH_WARNINGS are accepted unchanged. BLOCKED is rejected before RUNNING. A stale
projection remains exportable as its own snapshot, but current Product category must still match.
Product READY_TO_PUBLISH status is not required and Product is never mutated.

## Export Formats
Exactly CANONICAL_JSON (`catalog.json`), CATALOG_CSV (`catalog.csv`), and MANIFEST_JSON
(`manifest.json`).

## Canonical JSON Export
Compact sorted-key JSON with one trailing LF contains schema marker/version, immutable Product
identity, projection status/schema/attributes/warnings, and compact upstream lineage. Values remain
strings and raw source evidence is excluded.

## Flat CSV Export
One header and one Product row. Fixed identity/projection columns precede canonical attributes in
display order. Unit companion columns appear only for attributes carrying canonical units. Missing
optional identity and null units are empty; warnings use `|` in persisted reason order.

## Publication Package Manifest
Compact sorted-key JSON records package version, export/Product/projection IDs, projection status,
createdAt, warnings, and JSON/CSV names, media types, exact sizes and hashes. It does not recursively
contain its own checksum.

## Deterministic Serialization
UTF-8 without BOM, stable field/attribute/artifact order, compact JSON, standard-library CSV with LF,
fixed filenames, and no payload-generated timestamps beyond supplied immutable package metadata.

## Checksums
Lowercase SHA-256 over the exact bytes passed to ObjectStorage; stored metadata is verified against
the planned size and checksum.

## Export Artifact Metadata
Immutable format, filename, media type, safe object key, positive size, SHA-256, and UTC createdAt.

## Local Object Storage
Use ObjectStorage with internally generated `catalog-exports/{exportId}/{fixedName}` keys. The
configured LocalObjectStorage is supported; no service performs direct filesystem access or S3.

## Result Model
Immutable EXPORTED result with export/job/Product/projection/schema lineage, exact projection Product
version/status/warnings, three artifacts, engine/version, and UTC creation time.

## DynamoDB Persistence
`catalog-export-results` uses exportId/recordKey with META, three ARTIFACT records, a projection
uniqueness guard, sparse JobIdIndex and ProjectionIdIndex, query-only reads, and item guards.

## Processing Job Lifecycle
Validate setup before PENDING to RUNNING. Build/write artifacts, persist result, then complete with
100 percent and `catalog-export-results/{exportId}`. Technical post-start failures attempt FAILED.

## Idempotency
Exactly one authoritative export per projection, enforced by a transactional conditional guard as
well as preflight lookup. Neither objects nor results are overwritten.

## Safety Limits
100 attributes; 2,000,000 JSON bytes; 2,000,000 CSV bytes; 200,000 manifest bytes; 1,024-character
object keys; and 390,000 serialized bytes per DynamoDB item.

## Error Handling
Controlled failures cover invalid jobs, missing/cross-product/blocked/incoherent projections,
duplicates, size/attribute/serialization/storage/result failures, cleanup risks, and engine failures.

## Logging Requirements
Log safe job/Product/projection/export IDs, formats, sizes, checksum prefixes, warning counts, and
lifecycle events. Never log artifact bytes, attributes, descriptions, local paths, or secrets.

## Security Considerations
Explicit UUID lineage, fixed filenames, validated internally generated keys, bounded bytes, no raw
evidence, no arbitrary serializer selection, no overwrite, and no outbound network behavior.

## Edge Cases
Stale snapshots, optional identity nulls, special JSON/CSV text, unitless attributes, human
overrides, validation warnings, partial writes, cleanup failure, duplicate races, and completion risk.

## Acceptance Criteria
All 153 supplied criteria must pass without introducing any out-of-scope behavior.

## Test Plan
Cover domain invariants, JSON/CSV/manifest determinism and round trips, checksums/limits, repository
access patterns and incomplete partitions, eligibility/idempotency, storage order/cleanup, lifecycle,
optional LocalObjectStorage/DynamoDB Local contracts, and all repository-wide gates.

## Implementation Notes
Artifact preparation is not publication. Manifest lists JSON and CSV only to avoid recursive hash
design; result metadata stores the manifest checksum. Existing ObjectStorage sidecars remain bounded
to key, size, checksum, and time.

## Completion Record
Completed on 2026-08-19. The full backend suite passed with 1,489 tests, 14 optional local-service
tests skipped, and 90.64% coverage. Ruff lint and formatting, strict mypy, unchanged frontend tests,
ESLint, Prettier, Vite build, Docker Compose validation, and Git whitespace validation all passed.
All 153 acceptance criteria were verified within the SPEC-033 boundary.
