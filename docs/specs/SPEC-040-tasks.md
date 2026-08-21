# SPEC-040 Task Checklist

## Planning

- [x] ✅ Inspect Product GET/catalog-summary APIs
- [x] ✅ Inspect source APIs and enums
- [x] ✅ Inspect workflow APIs, enums, and stages
- [x] ✅ Define workspace, source, workflow, review, polling, and mobile UX

## API and State

- [x] ✅ Add Product/catalog/source/workflow queries
- [x] ✅ Add source and workflow mutations
- [x] ✅ Add centralized query keys, invalidation, safe errors, and RUNNING-only polling

## Product Workspace

- [x] ✅ Replace Product detail placeholder
- [x] ✅ Add identity header, summaries, staleness, tabs, and overview

## Source Management

- [x] ✅ Add source list, pagination, states, cards, icons, and statuses
- [x] ✅ Add accessible validated file upload
- [x] ✅ Add validated text-source drawer
- [x] ✅ Add versioned delete confirmation and active-workflow restriction

## Workflow Experience

- [x] ✅ Add launch configuration and defaults
- [x] ✅ Add workflow summary, progress, grouped timeline, and technical details
- [x] ✅ Add review checkpoint route/action and versioned resume
- [x] ✅ Add terminal outcomes, optional outputs, errors, and history

## Testing

- [x] ✅ Add workspace, source, workflow, polling, review, outcome, mobile, and accessibility tests

## Documentation

- [x] ✅ Add Product Workspace, source-management, and workflow-tracking documentation
- [x] ✅ Update frontend architecture, README, and completion record

## Verification

- [x] ✅ Frontend tests, ESLint, Prettier, and Vite build
- [x] ✅ Backend tests and coverage >=90%
- [x] ✅ Ruff lint/format and strict mypy
- [x] ✅ Docker Compose and Git whitespace validation
- [x] ✅ Required breakpoint/state visual QA
- [x] ✅ Confirm no unrelated feature implemented
