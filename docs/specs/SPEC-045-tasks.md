# SPEC-045 Task Checklist

## Discovery
- [x] ✅ Analyze all 30 labelled attributes against source evidence and all 1,000 descriptions
- [x] ✅ Classify source-present, derivable, absent, and external-only labelled facts
- [x] ✅ Identify high-frequency dimensions, materials, electrical values, quantities, and grit

## Vocabulary and Rules
- [x] ✅ Add observed label/UOM domain, semantic mappings, 15 compact product-type rules, artifact, command, policy, and hash

## Extraction and Normalization
- [x] ✅ Add exact fractions, multi-dimensions, quantities, grit, materials, electrical values, UOM normalization, confidence, and evidence spans

## Resolution and Delivery
- [x] ✅ Add label mapping, internal unknown labels, duplicate/conflict handling, deterministic ordering, 50-triple cap, and triple integrity
- [x] ✅ Preserve conservative commercial and dedicated-dimension behavior

## Model Boundary
- [x] ✅ Add optional strict semantic candidates, evidence validation, unsupported-value rejection, and no direct official-label promotion

## Evaluation and Frontend
- [x] ✅ Add attribute coverage, average attributes, precision/recall, top labels, review reasons, and minimal responsive `/quality` UI

## Regression Safety
- [x] ✅ Preserve 10/10 labelled classification, zero unsupported facts, and exact 252-column schema

## Verification
- [x] ✅ Backend tests and coverage ≥90%; Ruff; formatting; strict mypy
- [x] ✅ Frontend tests; ESLint; Prettier; Vite build
- [x] ✅ Docker Compose; Git whitespace; required viewport visual QA
