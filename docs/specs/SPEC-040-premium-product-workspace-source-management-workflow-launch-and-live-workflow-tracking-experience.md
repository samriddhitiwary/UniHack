# SPEC-040 — Premium Product Workspace, Source Management, Workflow Launch, and Live Workflow Tracking Experience

## Status

Completed

## Objective

Turn `/products/:productId` into CatalogIQ's operational workspace for source evidence and the Catalog Intelligence workflow.

## User Story

As a catalog operator, I can understand a product, manage its evidence, launch intelligence processing, follow business-friendly progress, respond to review checkpoints, and inspect prior runs.

## Scope

Product identity and catalog summaries, Overview/Sources/Workflow navigation, single-file source upload, text-source creation, source deletion, workflow configuration/start/resume, grouped timeline, output summaries, history, and review-route preparation.

## Out of Scope

Review decisions, candidate controls, manual overrides, detailed intelligence analysis, enrichment editing, export downloads, raw evidence, authentication, S3, deployment, WebSockets, workers, and backend expansion.

## Existing Dependencies

SPEC-038 design primitives, SPEC-039 Product routes/query conventions, Product/source/catalog-summary APIs, and SPEC-037 workflow APIs.

## Product Workspace Information Architecture

A rich identity header and compact summary strip lead into keyboard-accessible Overview, Sources, and Workflow tabs. Localized queries allow partial sections to fail without losing Product identity.

## Product Header

Shows name, manufacturer/model, category, lifecycle status, version, and updated timestamp with one workflow-aware primary action.

## Workspace Navigation

MUI Tabs provide Overview, Sources, and Workflow views without nested route complexity. History remains inside Workflow.

## Source Management

The newest-first cursor list uses rich source rows, friendly type/status labels, safe errors, Load More, and versioned deletion. Rename is intentionally omitted.

## File Upload UX

A compact accessible dropzone accepts one PDF, CSV, PNG, JPEG, or WEBP at a time. PDF/images are limited to 10 MiB and CSV to 5 MiB before the authoritative backend check. Upload uses an honest indeterminate progress state.

## Text Source UX

A responsive right drawer accepts an optional 200-character name and required trimmed text up to 50,000 characters. Creation never auto-starts a workflow.

## Source Status Presentation

PENDING, READY, PROCESSING, COMPLETED, and FAILED map to explicit friendly labels and centralized semantics. Failure detail remains bounded and safe.

## Source Actions

Delete is disabled while a workflow is RUNNING or WAITING_FOR_REVIEW and otherwise uses a focused confirmation dialog with the current source version.

## Workflow Launch

The no-workflow state explains the pipeline and enables launch only after sources are confirmed. Returned synchronous workflow state renders immediately.

## Workflow Configuration

Publishing readiness, export, AI enrichment, and intelligence score default on. Optional-stage strict failure defaults off under Advanced settings.

## Workflow State Presentation

Friendly labels, backend progress, terminal outcome summaries, safe mapped errors, and a single attention callout communicate state without console-style terminology.

## Workflow Timeline

Fifteen technical stages aggregate centrally into Analyze Sources, Understand Product, Structure Attributes, Validate Catalog, Human Review, Prepare Catalog, Generate Outputs, and Quality Evaluation. Technical details are collapsed by default.

## Human Review Checkpoint

WAITING_FOR_REVIEW preserves the exact review ID and offers review navigation only. No decision or bypass control is implemented.

## Workflow Resume

Resume is shown only for the backend `RESUME_WORKFLOW` next action and sends the exact workflow version. Review, version, Product-change, and source-change conflicts use safe business copy and refetch where appropriate.

## Workflow History

Newest-first history loads ten records initially and supports bounded Load More. Selecting a historical workflow retrieves its full timeline without polling terminal records.

## Polling Strategy

Only a selected/current RUNNING workflow polls every 2,500ms. Polling stops for review, failure, completion, and warning completion and does not force background-tab polling.

## Loading States

The first load uses a workspace-shaped skeleton; sources and workflows use localized skeletons and pending buttons/progress.

## Empty States

Dedicated states cover no sources and no workflow, with source-aware launch eligibility.

## Error States

Product 404 is page-level. Summary, sources, workflow, upload, text creation, deletion, start, and resume errors stay localized and surface request IDs safely.

## Responsive Behaviour

Desktop uses broad summary/timeline surfaces, tablet reflows controls, and mobile uses scrollable tabs, stacked source rows, full-width drawers, a choose-file-first upload surface, and a vertical timeline.

## Accessibility

Tabs, dropzone, native file input, dialogs/drawers, named actions, progress semantics, and textual phase statuses support keyboard and screen-reader use.

## Visual Quality Requirements

Preserve SPEC-038 hierarchy and density; prioritize identity, attention, catalog state, sources, progress, then technical detail. Avoid nested heavy cards and raw processing jargon.

## Acceptance Criteria

All 236 controlling SPEC-040 criteria must pass with no SPEC-041 or backend feature work.

## Test Plan

Cover workspace contracts, partial states, file validation/uploads, text creation, deletion constraints, workflow defaults/start/polling/timeline/review/resume/outcomes/history, responsiveness, and accessibility.

## Implementation Notes

Source and workflow cursors stay opaque. Source count is labeled as loaded rather than global when more pages exist. Single-file upload was selected to keep progress honest and bounded. Catalog summary remains authoritative for readiness and intelligence.

## Completion Record

Completed on 2026-08-21. The Product Workspace, source-management experience,
workflow launch/tracking, review handoff, versioned resume, output summary, and
bounded history were implemented without backend expansion or SPEC-041 scope.

Verification: 44 frontend tests passed; ESLint, Prettier, and Vite build passed;
1,612 backend tests passed with 16 skipped and 90.01% coverage; Ruff lint/format,
strict mypy, Docker Compose validation, and Git whitespace validation passed.
Responsive visual QA covered 1440x900, 1280x800, 1024x768, 768x1024, and
390x844 layouts plus the required source and workflow state presentations.
