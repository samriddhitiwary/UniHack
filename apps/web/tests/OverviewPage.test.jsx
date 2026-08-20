import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { OverviewPage } from '../src/pages/OverviewPage'
import { theme } from '../src/theme/theme'

function renderPage(props) {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter>
        <OverviewPage {...props} />
      </MemoryRouter>
    </ThemeProvider>,
  )
}
describe('Overview dashboard states', () => {
  it('renders fixture-driven KPI values and readable product rows', () => {
    renderPage()
    expect(screen.getByText('128')).toBeInTheDocument()
    expect(screen.getByText('VectorDrive X90')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Add Product' }),
    ).toBeInTheDocument()
  })
  it('renders a layout-matched loading state', () => {
    renderPage({ state: 'loading' })
    expect(screen.getByLabelText('Loading dashboard')).toBeInTheDocument()
  })
  it('renders a premium zero-data state', () => {
    renderPage({ state: 'empty' })
    expect(
      screen.getByRole('heading', {
        name: 'Start building your product intelligence catalog',
      }),
    ).toBeInTheDocument()
  })
  it('renders retry and request ID without exposing raw errors', () => {
    const retry = vi.fn()
    renderPage({ state: 'error', requestId: 'req-038', onRetry: retry })
    expect(screen.getByText('Request ID: req-038')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
