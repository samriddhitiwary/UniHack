# Catalog AI Grounding and Hallucination Controls

## Trusted facts

Only immutable SPEC-031 identity, category, existing description, reviewed attributes, warnings,
origin, and validation metadata enter the prompt. Stable IDs use `IDENTITY:name`,
`IDENTITY:manufacturer`, `IDENTITY:modelNumber`, `IDENTITY:category`, `IDENTITY:description`, and
`ATTRIBUTE:{canonicalName}`. Raw sources, excerpts, OCR/PDF/CSV evidence, generic industry knowledge,
and inferred specifications are excluded. Fact count and value lengths are bounded before RUNNING.

An existing description is untrusted text within trusted-data delimiters. It may ground ordinary
wording, but high-risk claims and numeric/spec facts require structured identity or reviewed
attribute support. This prevents embedded instructions or an unsupported legacy description from
overriding system rules.

## Deterministic validation

Every title, description, bullet, keyword, and summary must cite at least one known fact ID. Numeric
tokens, number words, model/spec codes such as IP55/IE3, and unit tokens must occur in the referenced
structured facts exactly; no unit conversion is performed. Unknown references and unsupported
numeric or unit claims reject the output.

Conservative phrase guards reject unsupported certifications/compliance, warranties/guarantees,
construction materials, performance/marketing claims, and specific use cases. High-risk phrases are
allowed only when a referenced reviewed attribute explicitly supports them. Exact case/whitespace
duplicate bullets and keywords are removed deterministically; no semantic rewrite occurs.

## Retry and persistence boundary

The model never judges its own correctness. A first malformed or unsafe response can cause one
correction prompt containing trusted facts and stable issue categories. Provider failures are not
hidden behind an unbounded retry loop. If the final attempt remains malformed or unsafe, the job
fails and neither raw nor parsed content is persisted. Only the final strictly parsed, deterministically
grounded structure becomes an immutable result.

These controls deliberately prefer rejection over permissive marketing language. They reduce obvious
hallucinations but do not claim semantic completeness or probabilistic truth confidence.
