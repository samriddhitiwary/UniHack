# Product Intelligence Scoring Methodology

All scores and weights use integer basis points from 0 through 10000. Base weights are completeness
2500, validation 2000, corroboration 2000, conflict health 1500, review quality 1000, and AI
grounding 1000. Only evaluated components participate; their weights are normalized to exactly
10000 with deterministic remainder assignment to the highest-weight components in stable enum
order. Overall score is only the sum of integer component contributions—there is no hidden penalty.

- Completeness: 85% required resolved plus 15% optional resolved. With zero optional definitions,
  required completeness receives the whole component.
- Validation: final required attributes have importance 2 and optional attributes 1. VALID is
  10000, VALID_WITH_WARNINGS 8000, and a deterministically validated human override 8500. Invalid
  final candidate lineage fails technically.
- Corroboration: three or more distinct sources score 10000, two score 9000, one scores 6000, and a
  human override without a source scores 5000. Repetition inside one source is not independent.
- Conflict health: agreement is 10000, tolerance agreement 9500, single candidate 8000, conflict
  resolved by a candidate 7000, conflict resolved by override 6000, and indeterminate evidence
  resolved by review 6500. Review does not erase historical disagreement.
- Review quality: approved proposed values score 10000, approved candidates 8500, and human
  overrides 7000. This describes automation intervention, not reviewer or data validity.
- AI grounding: when explicit compatible enrichment exists, score is 80% grounding plus 20% fact
  coverage. Otherwise it is NOT_EVALUATED and its weight is redistributed without penalty.

Grades use inclusive lower bounds: EXCELLENT 9000, GOOD 8000, FAIR 6500, POOR 5000, and CRITICAL
below 5000. Display percent is `(overallScoreBp + 50) // 100`. Stable component reasons are mapped
to deduplicated overall action codes; the top five prioritize required gaps, invalid/indeterminate
required data, conflicts, weak required support, validation warnings, human overrides, optional
coverage, then AI coverage. AI-not-evaluated remains informational and is excluded from top actions.
