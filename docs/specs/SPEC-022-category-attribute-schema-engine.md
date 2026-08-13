# SPEC-022 — Category Attribute Schema Engine

## Status
Completed

## Objective
Define, validate, version, fingerprint, persist, and retrieve canonical technical-attribute schemas for the two classified product categories.

## User Story
As a later extraction workflow, I need an immutable contract describing which category-specific fields exist, how source labels resolve to them, and which unit and validation metadata applies.

## Scope
Immutable schema metadata, built-in pump and motor version 1 definitions, aliases, units, validation metadata, deterministic fingerprints, internal lookup/bootstrap services, DynamoDB persistence, local seeding, tests, and documentation.

## Out of Scope
Attribute extraction or values, conversion or normalization, missing-field and conflict detection, actual product-value validation, AI/LLM enrichment, schema APIs/editing/activation, frontend, workers, S3, authentication, authorization, and deployment.

## Functional Requirements
Provide active version 1 schemas for `CENTRIFUGAL_PUMP` and `INDUCTION_MOTOR`; reject `UNCLASSIFIED`; resolve aliases only within a selected category/version; seed built-ins idempotently without overwrite; and detect persisted version drift.

## Non-Functional Requirements
Backend-only, immutable and bounded models, deterministic output/fingerprints, repository abstraction, conditional writes, no floats, no external calls, safe metadata-only logging, and no product mutation.

## Existing Dependencies
ProductCategory, immutable dataclass conventions, DynamoDB serializers/repositories, validated Settings, local table tooling, controlled exceptions, structured logging, and SPEC-021 category boundaries.

## Supported Categories
Exactly `CENTRIFUGAL_PUMP` and `INDUCTION_MOTOR`. `UNCLASSIFIED` has no schema and produces `CATEGORY_ATTRIBUTE_SCHEMA_NOT_AVAILABLE`.

## Attribute Definition Model
Stable camelCase `attribute_id`/`canonical_name`, bounded display name and description, data type, required flag, units, aliases, examples, validation metadata, and positive unique display order.

## Attribute Data Types
Exactly `TEXT`, `NUMBER`, `INTEGER`, `BOOLEAN`, and `ENUM`. No nested/list types.

## Required and Optional Attributes
Required means important for future catalog completeness only. SPEC-022 neither detects missing fields nor validates actual values.

## Unit Metadata
Bounded immutable symbol/canonical/dimension metadata. Units are unique per attribute and permitted only on NUMBER/INTEGER attributes. No conversion occurs.

## Alias Model
Store bounded original aliases. Compare using lowercase, trimmed/collapsed whitespace and conservative punctuation/underscore/hyphen separator normalization. Canonical and display names resolve implicitly. Any normalized cross-attribute collision is rejected.

## Schema Versioning
Positive integer versions, deterministic `{category}:{version}` IDs, `ACTIVE`/`INACTIVE` status, immutable category/version records, and exactly the two built-in active version 1 schemas. No activation workflow.

## Built-In Category Schemas
Motor v1 contains the 13 approved technical fields with five required fields. Pump v1 contains the 12 approved technical fields with flowRate/head required. Product-owned manufacturer/modelNumber are excluded.

## Schema Validation
Enforce supported category, identifier and string bounds, unique canonical names/display order/normalized aliases/units, attribute/alias/example limits, numeric-only units, coherent min/max and allowed-value metadata, at least one attribute, and deterministic schema fingerprint integrity.

## DynamoDB Persistence
Use `{prefix}-category-attribute-schemas` with string `category` partition key and numeric `version` sort key. Store one bounded item, conditionally create immutable versions, retrieve directly by key, and query at most 100 newest category versions to locate ACTIVE without scans. Guard at 390,000 serialized bytes.

## Repository Contract
`create`, `get_by_category_and_version`, and `get_active_by_category`, returning domain objects. Unsupported categories are controlled; absent supported versions return `None` at the repository and become not-available errors at the service.

## Error Handling
Controlled errors cover unsupported/missing schemas, validation, alias conflicts, duplicate versions/active versions, drift, item size, serialization, and repository failures. No HTTP mapping is added.

## Logging Requirements
Log category, version, schema ID, counts, and fingerprint for create/retrieve/seed/skip/drift/failure events. Never log entire schemas repeatedly.

## Security Considerations
Supported-category allowlist, strict bounds, inert validation metadata only, bounded non-executed patterns, no expressions/floats/external calls, conditional immutable persistence, and no arbitrary schema input API.

## Edge Cases
UNCLASSIFIED, malformed canonical names, normalized duplicate aliases, implicit alias collisions, duplicated units/order, incoherent ranges, deterministic reordered fingerprints, timestamp-only changes, absent active schema, duplicate version, conflicting active version, seed rerun, seed drift, malformed items, and oversized records.

## Acceptance Criteria
All 95 controlling criteria must pass, coverage must remain at least 90%, documentation and scope audit must be complete, and existing behavior must remain green.

## Test Plan
Domain invariants; exact motor/pump definitions; alias normalization/scoping/collisions; fingerprint stability/change cases; schema serialization; repository conditionals/lookups/active query/size/errors; bootstrap idempotency/drift; service resolution/errors; optional DynamoDB Local; full backend/frontend/static verification.

## Implementation Notes
Validation rules are inert serializable metadata. Fingerprints use SHA-256 over canonical JSON sorted independently of timestamps and input attribute/alias/unit ordering. Active lookup is intentionally bounded to 100 versions; activation/editing remains future scope.

## Completion Record
Completed on 2026-08-13. Added immutable and bounded attribute, unit, validation-rule, and category-schema models; exact pump/motor ACTIVE v1 built-ins; category-scoped alias resolution; deterministic timestamp-independent fingerprints; conditional DynamoDB persistence; bounded active lookup; idempotent local bootstrap with preflight drift protection; tests; and documentation. The full backend suite passed 1,108 tests with 91.04% coverage and 11 opt-in skips. Ruff, formatting, strict mypy, unchanged frontend test/lint/format/build, Docker Compose validation, and Git whitespace checks passed. No processing job, API, extraction/value persistence, unit conversion, missing-field detection, actual product validation, frontend feature, S3, authentication, or deployment behavior was added.
