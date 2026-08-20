# CatalogIQ Design System

CatalogIQ's interface is a polished, information-dense light enterprise system. It favors clarity, trust, and calm over decorative “AI” effects.

## Foundations

- **Palette:** indigo `#4f46e5` is the primary action/intelligence accent. Slate 50 through 900 provide canvas, borders, secondary copy, and primary copy. Success, warning, error, and info each provide readable foreground, tint, and border values.
- **Typography:** Inter when available, followed by the system sans-serif stack. Page titles are 32px/700; sections 18–22px/650; body copy 14px; metadata 12–13px; KPI values 28–32px.
- **Spacing:** MUI's base unit is 4px. Preferred steps are 4, 8, 12, 16, 20, 24, 32, 40, and 48px.
- **Radius:** inputs and controls use 9px; cards use 14px; badges use a pill radius.
- **Elevation:** ordinary cards use a one-pixel cool-gray border and minimal shadow. Menus use one restrained larger shadow.
- **Motion:** interaction feedback uses a 180ms ease transition. Pages do not animate on load.

## Status semantics

Neutral represents draft, pending, or archived states. Blue represents active/informational processing. Green represents ready, completed, and excellent states. Amber represents review, warnings, and fair quality. Red represents blocked, failed, poor, or critical states. `StatusBadge` always includes readable text, making color supplementary.

## Component usage

Use `PageContainer` and `PageHeader` on every page. Use `AppCard` for bounded surfaces, `SectionHeader` inside cards, `MetricCard` for prominent measures, and `DataTableShell` for structured records. Use shared empty, error, and skeleton components instead of page-specific feedback. Icon-only controls require a tooltip and accessible label.

## Responsive breakpoints

- Desktop (1200px and wider): persistent sidebar, four KPI columns, two-column dashboard regions, 32px page padding.
- Tablet (768–1199px): drawer navigation, two KPI columns, stacked primary regions, 24px page padding.
- Mobile (below 768px): drawer navigation, compact header, one KPI column, stacked cards, 16px page padding, horizontally scrollable tables.
