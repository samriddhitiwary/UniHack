# Challenge Quality Dashboard

`/quality` is the judge-facing Unilog evaluation console. It reads the latest isolated evaluation
and makes the sample boundary explicit: correctness comes from 2 officially labelled products,
while batch quality describes all 1,000 input products.

The hero establishes the 1,000-row, 252-column, 2-label context. KPI cards report labelled exact
matches, supported-field coverage, processing success, review rate, and deterministic description
grounding. Supporting sections cover the ground-truth breakdown, raw/supported and strategy
coverage, batch health, confidence and review reasons, description compliance, field groups, top
problems, and metric-derived improvement opportunities.

The labelled comparison selects either official product, shows Expected/CatalogIQ/status values,
and supports All, Matches, Mismatches, and Missing filters. Both-blank fields are hidden by default
and exposed through a labelled switch. Exact, normalized, mismatch, missing, and unexpected statuses
combine restrained semantic tint with visible text; no meaning depends on color alone.

Desktop uses the full shell and two-column analytical grids. Tablet removes the sidebar and stacks
major sections as space tightens. Mobile uses one column and converts field rows to comparison cards.
The page has no horizontal document overflow at 1440x900, 1280x800, 1024x768, 768x1024, or
390x844. Keyboard-labelled filters, semantic table roles, visible status text, dashboard-shaped
skeletons, an actionable empty state, and a safe request-ID error state provide accessible feedback.
