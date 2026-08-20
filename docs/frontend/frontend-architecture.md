# CatalogIQ Frontend Architecture

## Structure

`src/api` owns transport, safe errors, and React Query. `components/common` owns reusable primitives; `components/dashboard`, `feedback`, and `layout` contain bounded concerns. `pages` composes routes, `routes` owns navigation and route configuration, `theme` centralizes presentation, and `mocks` isolates visual fixtures.

## Routing and shell

React Router renders one `AppShell`. `/dashboard` is implemented; future-facing routes deliberately reuse `ComingSoonPage`, avoiding broken links and half-built features. Desktop navigation is persistent and tablet/mobile navigation uses a modal drawer that closes after navigation.

## Theme

`tokens.js`, `typography.js`, `componentOverrides.js`, and `theme.js` form the design system. Components consume semantic theme values and shared primitives.

## API and server state

`VITE_API_BASE_URL` is parsed once. The Axios client applies a 15-second timeout and converts failures into `ApiError` with `status`, `code`, `message`, `requestId`, and safe `details`. React Query manages future server state with one retry, no focus refetch, and a 30-second default stale time. Local state manages the drawer and notification surface. Redux is intentionally absent.

## Dashboard fixtures

No dedicated aggregate endpoint exists. `src/mocks/dashboard.js` is the sole source of Phase 1 visual metrics; components receive data through props and never infer totals from paginated product data. The page exposes deterministic ready, loading, empty, and error modes for future query integration.
