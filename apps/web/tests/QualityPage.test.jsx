import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { QualityPage } from '../src/pages/QualityPage'
import {
  unilogComparisonFixture,
  unilogEvaluationFixture,
} from '../src/mocks/unilogEvaluation'
import { theme } from '../src/theme/theme'

vi.mock('../src/api/unilogEvaluation', () => ({
  getLatestUnilogEvaluation: vi.fn(),
  createUnilogEvaluation: vi.fn(),
  getUnilogLabelledComparison: vi.fn(),
}))

function renderPage(props) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <QualityPage {...props} />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

describe('Challenge Quality dashboard', () => {
  it('separates two-row accuracy from 1,000-row batch quality', async () => {
    renderPage({
      state: 'ready',
      data: unilogEvaluationFixture,
      comparisonData: unilogComparisonFixture,
    })
    expect(
      screen.getByRole('heading', { level: 1, name: 'Challenge Quality' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/2 officially labelled products/),
    ).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Batch quality metrics cover all 1,000 challenge input rows',
    )
    expect(screen.getByText('28 / 134')).toBeInTheDocument()
    expect(screen.getByText('1,000 / 1,000')).toBeInTheDocument()
    expect(screen.getAllByText(/not accuracy/i)).toHaveLength(2)
    expect(screen.queryByText(/AI Accuracy/i)).not.toBeInTheDocument()
    expect(screen.getByText('Unsupported Fact Violations')).toBeInTheDocument()
    expect(
      screen.getByText('Verified classification coverage'),
    ).toBeInTheDocument()
    expect(screen.getByText('Attribute coverage')).toBeInTheDocument()
    expect(
      screen.getByText('Manufacturer and brand resolution'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Manufacturer resolution coverage'),
    ).toBeInTheDocument()
    expect(screen.getByText('Labelled brand exact')).toBeInTheDocument()
    expect(screen.getByText('Labelled semantic precision')).toBeInTheDocument()
    expect(
      screen.getByText('Reduce evidence ambiguity before auto-approval'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('table', { name: 'Field group performance' }),
    ).toBeInTheDocument()
  })

  it('provides keyboard-labelled comparison filters and hides both-blank fields by default', async () => {
    const user = userEvent.setup()
    renderPage({
      state: 'ready',
      data: unilogEvaluationFixture,
      comparisonData: unilogComparisonFixture,
    })
    const table = screen.getByRole('table', {
      name: 'Labelled field comparison',
    })
    expect(within(table).getByText('Mfg_Part_Num')).toBeInTheDocument()
    expect(within(table).queryByText('UPC')).not.toBeInTheDocument()
    await user.click(screen.getByRole('switch', { name: 'Show blank fields' }))
    expect(within(table).getByText('UPC')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Mismatches' }))
    expect(within(table).getByText('INVOICE_DESC')).toBeInTheDocument()
    expect(within(table).queryByText('Mfg_Part_Num')).not.toBeInTheDocument()
    expect(within(table).getByText('Mismatch')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'PDSH4816AF' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('renders dashboard-shaped loading, actionable empty, and safe error states', () => {
    const { rerender } = renderPage({ state: 'loading' })
    expect(screen.getByLabelText('Loading dashboard')).toBeInTheDocument()
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <ThemeProvider theme={theme}>
          <MemoryRouter>
            <QualityPage state="empty" />
          </MemoryRouter>
        </ThemeProvider>
      </QueryClientProvider>,
    )
    expect(
      screen.getByRole('heading', { name: 'No challenge evaluation yet' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Run Evaluation' }),
    ).toBeInTheDocument()
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <ThemeProvider theme={theme}>
          <MemoryRouter>
            <QualityPage
              state="error"
              requestId="req-quality-043"
              onRetry={vi.fn()}
            />
          </MemoryRouter>
        </ThemeProvider>
      </QueryClientProvider>,
    )
    expect(screen.getByText('Request ID: req-quality-043')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})
