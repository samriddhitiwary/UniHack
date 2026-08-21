# SPEC-044 Task Checklist

## Discovery
- [x] ✅ Analyze all 1,000 Part_Desc values, existing classifiers, failures, labels, recurring phrases, abbreviations, variants, and generic nouns
- [x] ✅ Document Product Type, Product Family, and Official Classpath separately

## Vocabulary
- [x] ✅ Add vocabulary domain, phrase counts, variants, abbreviations, bounded evidence, source metadata, artifact, hash, and policy version

## Resolution
- [x] ✅ Add indexed resolver, safe normalization, ambiguity/generic handling, evidence spans, confidence, review reasons, validated model proposal, and fallback

## Classpath
- [x] ✅ Add verified mappings with source/support/confidence and reject model-only or unknown Classpaths

## Integration
- [x] ✅ Integrate SPEC-042 Product Name, descriptions, Sanding Belt dimensions, review reasons, and preserve manufacturer and 252-column behavior

## Evaluation
- [x] ✅ Re-run 1,000 rows and SPEC-043; capture classification, coverage, description, attribute, and labelled before/after metrics

## Frontend
- [x] ✅ Add accessible responsive classification coverage, verified Classpath, review reasons, and top product types to `/quality`

## Testing
- [x] ✅ Cover phrases, variants, abbreviations, generic terms, ambiguity, model validation/hallucination, verified/model-only Classpath, labels, anti-leakage, enrichment, evaluation, and UI

## Verification
- [x] ✅ Backend suite and coverage ≥90%
- [x] ✅ Ruff lint and formatting, strict mypy
- [x] ✅ Frontend tests, ESLint, Prettier, Vite build
- [x] ✅ Docker Compose and Git whitespace
