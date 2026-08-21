import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined'
import { Button, ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { EmptyState } from '../src/components/common/EmptyState'
import { ErrorState } from '../src/components/common/ErrorState'
import { MetricCard } from '../src/components/common/MetricCard'
import { PageHeader } from '../src/components/common/PageHeader'
import { StatusBadge } from '../src/components/common/StatusBadge'
import { theme } from '../src/theme/theme'

function renderUi(node) {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter>{node}</MemoryRouter>
    </ThemeProvider>,
  )
}

describe('shared CatalogIQ components', () => {
  it('renders semantic page headings, breadcrumbs, status, and actions', () => {
    renderUi(
      <PageHeader
        title="Product quality"
        subtitle="Review catalog confidence."
        breadcrumbs={[
          { label: 'Overview', href: '/dashboard' },
          { label: 'Quality' },
        ]}
        status={<StatusBadge status="GOOD" />}
        actions={<Button>Export</Button>}
      />,
    )
    expect(
      screen.getByRole('heading', { level: 1, name: 'Product quality' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('navigation', { name: 'Breadcrumbs' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Export' })).toBeInTheDocument()
  })

  it('renders metric, empty, and safe error states', () => {
    const { rerender } = renderUi(
      <MetricCard
        label="Total Products"
        value="128"
        helper="Active catalog"
        icon={<Inventory2OutlinedIcon />}
      />,
    )
    expect(screen.getByText('128')).toBeInTheDocument()
    rerender(
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <EmptyState
            title="No products"
            description="Add the first product."
            actionLabel="Add Product"
          />
        </MemoryRouter>
      </ThemeProvider>,
    )
    expect(
      screen.getByRole('button', { name: 'Add Product' }),
    ).toBeInTheDocument()
    rerender(
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <ErrorState requestId="req-safe-123" onRetry={() => {}} />
        </MemoryRouter>
      </ThemeProvider>,
    )
    expect(screen.getByText('Request ID: req-safe-123')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it.each([
    'READY_TO_PUBLISH',
    'REVIEW_REQUIRED',
    'FAILED',
    'WAITING_FOR_REVIEW',
    'EXCELLENT',
    'CRITICAL',
  ])('maps %s to a readable label', (status) => {
    renderUi(<StatusBadge status={status} />)
    expect(
      screen.getByText(new RegExp(status.split('_').join(' '), 'i')),
    ).toBeInTheDocument()
  })
})
