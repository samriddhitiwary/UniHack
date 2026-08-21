# Product Workspace

`/products/:productId` is the operational CatalogIQ workspace. It loads Product identity independently from catalog summary, source, and workflow queries so localized failures do not erase the header.

The header prioritizes name, manufacturer/model, category, lifecycle status, version, freshness, publishing readiness, intelligence score, and loaded source count. Its single primary action changes with workflow state. Keyboard-accessible Overview, Sources, and Workflow tabs keep the information architecture shallow and work as scrollable navigation on narrow screens.

Overview summarizes current state without duplicating full source or workflow content. `/products/:productId/review/:reviewId` preserves the exact future review deep link while deliberately providing no decision controls before SPEC-041.

The layout uses stacked mobile summaries and source rows, full-width mobile drawers, and the same vertical workflow timeline at every size. Product, source, and safe error text wrap without widening the page.
