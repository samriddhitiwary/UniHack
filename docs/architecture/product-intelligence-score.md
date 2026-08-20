# Product Intelligence Score

SPEC-035 creates an immutable diagnostic of catalog-information quality. It does not measure the
physical Product and it does not replace the independent `READY`, `READY_WITH_WARNINGS`, or
`BLOCKED` publishing-readiness decision.

An internal product-level `PRODUCT_INTELLIGENCE_SCORE` job names one explicit `projectionId` and an
optional explicit `enrichmentId`. The service derives every core upstream identifier from the
projection, loads only those exact artifacts, verifies Product/category/schema lineage, and permits
a structurally coherent BLOCKED projection. It never performs a latest-result lookup.

The pure engine evaluates completeness, validation quality, distinct-source corroboration,
historical conflict health, review intervention, and optional AI grounding. It uses integer basis
points, stable reason codes, bounded metrics, and policy `product-intelligence-score-v1`; it makes
no provider, LLM, filesystem, or network call. Missing enrichment is explicit `NOT_EVALUATED`, is
informational, and has no score penalty.

The immutable result retains complete lineage, readiness context, six ordered component records,
overall score/grade, strengths, action-oriented improvements, up to five prioritized improvements,
policy/engine metadata, and UTC time. Neither Product nor any upstream artifact is mutated.

Exact input uniqueness is the SHA-256 of projection ID, enrichment ID-or-NONE, and policy version.
A future policy version, projection, or enrichment can therefore create a new historical score.
Setup validation precedes RUNNING, persistence precedes COMPLETED, and a completion-update failure
retains the valid result while logging a consistency risk.
