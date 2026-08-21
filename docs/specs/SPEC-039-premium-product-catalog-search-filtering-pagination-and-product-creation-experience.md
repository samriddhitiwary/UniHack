# SPEC-039 — Premium Product Catalog, Search, Filtering, Pagination, and Product Creation Experience

## Status

Completed

## Objective

Deliver CatalogIQ's first real product-management screen using the indexed SPEC-036 catalog API and Product create/detail APIs while preserving the SPEC-038 visual language.

## User Story

As a catalog operator, I can locate, assess, create, and open industrial product records through a trustworthy interface that accurately represents backend search constraints.

## Scope

The `/products` catalog, indexed search and filters, cursor navigation, desktop table, mobile cards, stale-state presentation, product creation drawer, and lightweight real-data detail shell.

## Out of Scope

Source upload or management, workflow execution/tracking, review decisions, intelligence drilldown, AI-content editing, export download, authentication, infrastructure, deployment, and backend search expansion.

## Existing Dependencies

SPEC-038 theme, shell, feedback primitives, API normalization and React Query; SPEC-036 catalog search; SPEC-003 Product create/retrieve.

## Product Catalog UX

One primary bordered surface contains a compact responsive toolbar, active-filter chips, desktop table or mobile cards, localized state feedback, and cursor controls. Identity remains the highest visual priority.

## Search Semantics

Product name uses normalized `namePrefix`. Model number uses normalized exact `modelNumber`. Both submit explicitly on Enter or Search and cannot combine with another filter.

## Filter Semantics

Category and status may be used alone or together. Manufacturer is normalized exact equality and exclusive. The UI clears conflicting state when an exclusive access pattern is activated and disables incompatible controls while it remains active.

## Pagination

Twenty records are requested. An in-memory opaque-cursor history enables Previous and Next without exposing cursor values or inventing totals. Any query-state change returns to the first page.

## Product Table

Desktop columns prioritize Product, Status, Intelligence, Readiness, Category, Updated, and an accessible chevron. Below 900px compact product cards replace the table.

## Product Identity Presentation

Product names use semibold, bounded typography with manufacturer and model metadata beneath. Missing optional values display an em dash.

## Intelligence and Readiness Presentation

Existing StatusBadge and IntelligenceScore primitives render lifecycle, projection readiness, and quality. Missing artifacts read “Not evaluated” or “Not scored.”

## Staleness Presentation

False `projectionCurrent` and `intelligenceCurrent` values show a text-based Outdated indicator with an explanatory tooltip.

## Product Creation UX

A 560px right drawer retains catalog context. Identity and classification sections contain only backend-supported fields. Success invalidates catalog queries, seeds detail cache, resets/closes the form, notifies the user, and navigates to the product shell.

## Form Validation

React Hook Form and Zod trim input, require a 2–200 character name, enforce backend maximum lengths, and validate the category enum. Backend failures remain safe and retain input.

## Server State

Central query keys include the access plan, filters, and cursor. React Query retains the prior page during cursor transitions and cancels obsolete Axios requests through its signal.

## Loading States

First load uses catalog-shaped table/mobile skeletons. Page transitions retain prior results with a localized progress bar.

## Empty States

Unfiltered zero data shows first-product onboarding. Filtered zero data gives adjustment and clear-filter guidance.

## Error States

Normalized errors show a calm catalog message, retry, and request ID. Creation errors remain in the drawer.

## Responsive Behaviour

Desktop shows table and inline filters; tablet reflows the toolbar; mobile keeps search visible, moves filters to a temporary drawer, and renders cards with no page overflow.

## Accessibility

Search submits by keyboard, controls are labeled, rows/cards activate by Enter or Space, icon buttons have names/tooltips, the drawer manages focus, and validation uses accessible helper text.

## Visual Quality Requirements

Maintain SPEC-038 spacing, palette, typography, borders, density, motion, and status semantics. Handle long identity text and wrapping chips without clutter.

## Acceptance Criteria

All 174 criteria from the controlling SPEC-039 amendment must pass without unrelated frontend or backend work.

## Test Plan

Cover rendering, each supported plan, compatibility behavior, chips, cursor history, feedback states, creation validation/success/failure, detail loading, mobile controls/cards, and accessibility.

## Implementation Notes

URL query parameters persist shareable search/filter state; opaque cursors remain local. No debounce is used because both indexed text modes submit explicitly, preventing partial exact-model requests and giving consistent keyboard behavior.

## Completion Record

Completed on 2026-08-20. The Product Catalog, supported indexed search/filter plans, opaque cursor navigation, responsive table/cards, stale-state indicators, Product creation drawer, and lightweight Product detail shell are implemented and documented. Frontend tests (29), ESLint, Prettier, Vite production build, backend tests (1,612 passed and 16 skipped), 90.01% backend coverage, API-package Ruff/format checks, strict mypy, Docker Compose configuration, and Git whitespace checks passed. Required breakpoint and state-focused visual QA was completed. Repository-wide Ruff additionally reports one pre-existing import-order issue in `scripts/dynamodb/create_tables.py`; SPEC-039 makes no backend or script changes.
