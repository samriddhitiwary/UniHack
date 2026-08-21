# Product Catalog and Creation

## Page structure

`/products` is CatalogIQ's primary catalog workspace. A `PageHeader` and Add Product action sit above one `AppCard` containing the toolbar, active filters, results, localized feedback, and cursor footer. `/products/:productId` is a lightweight shell backed by the Product retrieve API.

## Indexed search modes

- **Product name:** submits `namePrefix`; matching is a backend-normalized prefix.
- **Model number:** submits exact `modelNumber`; partial model typing never sends requests.

Both modes submit on Enter or Search. They are exclusive and cannot combine with filters. Switching mode clears the previous search.

## Filters and compatibility

Category and status work independently or together. Manufacturer is normalized exact equality and is exclusive. Activating an exclusive search clears conflicting URL state. Incompatible controls remain visibly disabled with a tooltip rather than sending a known-invalid request. Active state is stored in clean URL keys and represented by removable chips; Clear all returns to the unfiltered first page.

Unsupported backend plans are deliberately absent: readiness, intelligence grade/score ranges, fuzzy, substring, semantic, and arbitrary full-text search.

## Pagination

The catalog requests 20 records and treats every continuation cursor as opaque. An in-memory cursor stack implements Previous and Next. Filter changes reset history. The UI says “Showing up to 20 products” and never invents a total or page number.

## Product presentation

At 900px and wider the catalog renders the shared `DataTableShell`; below that breakpoint compact accessible cards preserve product identity, status, intelligence, readiness, category, and updated date. Missing optional values use an em dash. Missing projection and score artifacts read “Not evaluated” and “Not scored.” Stale projection and intelligence artifacts use text-based Outdated indicators with explanatory tooltips.

## Product creation

All Add Product entry points open the same responsive 560px right drawer (full width on mobile). The form mirrors the backend contract: required name plus optional manufacturer, model number, category, and description. `UNCLASSIFIED` is a valid default and no automatic classification is implied.

React Hook Form and Zod enforce trimming and backend length/enum constraints. Submission is non-optimistic and duplicate-safe. A failure retains values and shows only normalized message/request-ID data. Success resets and closes the drawer, notifies the operator, invalidates catalog queries, seeds Product detail cache, and navigates to the new Product shell.

Unsaved-close confirmation is intentionally omitted in this first version; closing resets the form. MUI's drawer restores focus to its trigger and supports Escape.
