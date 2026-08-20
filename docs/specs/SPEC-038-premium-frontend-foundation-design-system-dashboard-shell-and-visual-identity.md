# SPEC-038: Premium Frontend Foundation, Design System, Dashboard Shell, and Visual Identity

**Status:** Completed

## Objective

Establish CatalogIQ's premium light enterprise frontend: a centralized MUI design system, responsive application shell, reusable interface primitives, future-friendly routes, and a polished fixture-driven Overview dashboard. This foundation supports SPEC-039 through SPEC-041 without implementing them early.

## Visual direction

CatalogIQ uses a cool-neutral canvas, crisp white surfaces, deep-slate typography, and a restrained indigo intelligence accent. Information hierarchy comes from typography, alignment, borders, spacing, and subtle elevation. The identity uses a compact spark mark, the CatalogIQ wordmark, and the “AI Product Intelligence” descriptor.

## Scope delivered

- Central palette, semantic colors, typography, radius, shadows, transitions, layout tokens, and MUI overrides.
- Persistent 252px desktop sidebar, compact top header, responsive content container, and tablet/mobile drawer.
- Accessible navigation for Overview, Products, Workflows, Quality, AI Enrichment, Exports, and Settings.
- Reusable page, card, metric, status, score, feedback, skeleton, notification, and table components.
- Overview KPI, catalog-quality, workflow-health, recent-product, and attention-required presentations.
- Ready, empty, loading, and safe error dashboard variants.
- Central Axios client, normalized errors and request IDs, and conservative React Query defaults.
- Behavioral component tests plus frontend architecture and design documentation.

## Data and routing

No aggregate API currently supplies accurate dashboard totals. Phase 1 values therefore live only in `src/mocks/dashboard.js` and are passed to presentation components; paginated APIs are not sampled to invent global counts. `/dashboard` is the only full page. Future routes render the reusable `ComingSoonPage`, including `/products`, `/products/:productId`, `/workflows`, `/quality`, `/ai-enrichment`, `/exports`, and `/settings`.

## Exclusions

No complete catalog, search, creation, upload, workflow execution/polling, human review, intelligence detail, AI editor, export download, authentication, authorization, dark mode, S3, deployment, or backend feature is included.

## Acceptance record

The implementation centralizes its design decisions, significantly customizes MUI, provides responsive and keyboard-accessible shell behavior, isolates fixture semantics, supports all dashboard states, includes reusable primitives and tests, documents the system, and passes repository quality gates. Visual QA covers 1440x900, 1280x800, 1024x768, 768x1024, and 390x844 in Chromium.
