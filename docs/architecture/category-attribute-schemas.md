# Category Attribute Schemas

SPEC-022 defines the static, versioned contract that later extraction and completeness workflows
will use after a product category is known. It does not inspect SPEC-021 evidence or store actual
attribute values.

Only `CENTRIFUGAL_PUMP` and `INDUCTION_MOTOR` have schemas. `UNCLASSIFIED` is deliberately rejected
with `CATEGORY_ATTRIBUTE_SCHEMA_NOT_AVAILABLE`; there is no generic catch-all. Motor v1 has 13
technical attributes with ratedPower, voltage, frequency, speedRpm, and phase required. Pump v1 has
12 technical attributes with flowRate and head required. Requiredness is catalog-completeness
metadata only. Manufacturer and model number remain top-level Product fields.

Each immutable `AttributeDefinition` uses a stable camelCase ID/name and carries display text,
`TEXT`/`NUMBER`/`INTEGER`/`BOOLEAN`/`ENUM` type, requiredness, deterministic display order, bounded
aliases/examples, optional numeric-unit metadata, and inert min/max/allowed-value/pattern metadata.
Units are allowlisted labels only; no conversion occurs. Patterns are stored but not executed.

Alias comparison lowercases, trims/collapses whitespace, and conservatively treats punctuation,
hyphens, and underscores as separators. Canonical and display names are implicit aliases. Every
normalized alias has one owner within a category schema, while the same phrase may safely mean
something different in another category. Unknown aliases return `None` and are never guessed.

Schemas use positive integer versions, deterministic `{category}:{version}` IDs, and ACTIVE or
INACTIVE status. Built-in pump and motor schemas are ACTIVE version 1. Versions are immutable:
changes require a later version. A SHA-256 fingerprint covers category, version, status,
description, attributes, units, aliases, examples, requiredness, and validation metadata using
canonical ordering. Timestamps are excluded. Bootstrap compares fingerprints and fails with
`CATEGORY_ATTRIBUTE_SCHEMA_VERSION_DRIFT` rather than overwriting changed persisted v1 content.

`{prefix}-category-attribute-schemas` stores one bounded item under string `category` and numeric
`version`. Creation conditionally rejects an existing key and prevents a second active version in
the normal bootstrap path. Direct consistent reads retrieve a version. A bounded descending query
of at most 100 versions finds ACTIVE without scans or an extra index. Serialized items are rejected
above 390,000 bytes.

`seed_category_attribute_schemas.py` is local/development-only. It preflights both built-ins before
writing, creates missing versions, skips identical versions, detects drift, and is idempotent. It is
not a production migration or schema activation system. No API, editor, job, extraction, product
validation, unit normalization, frontend behavior, or deployment provisioning is included.
