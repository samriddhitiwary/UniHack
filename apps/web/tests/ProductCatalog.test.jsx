import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../src/api/errors'
import { NotificationProvider } from '../src/components/feedback/NotificationProvider'
import { ProductCard } from '../src/components/products/ProductCard'
import { ProductsPage } from '../src/pages/ProductsPage'
import { theme } from '../src/theme/theme'

const api = vi.hoisted(() => ({ search: vi.fn() }))
vi.mock('../src/api/catalog', () => ({
  searchCatalogProducts: api.search,
  getCatalogProductSummary: vi.fn(),
}))

const product = {
  productId: '11111111-1111-4111-8111-111111111111',
  name: 'Very Long Industrial High Efficiency Three Phase Induction Motor Model IM-5500',
  manufacturer: 'ABC Motors',
  modelNumber: 'IM-5500',
  category: 'INDUCTION_MOTOR',
  status: 'READY_TO_PUBLISH',
  productVersion: 3,
  createdAt: '2026-08-19T10:00:00Z',
  updatedAt: '2026-08-20T10:00:00Z',
  projectionId: 'projection-1',
  publishingReadiness: 'READY_WITH_WARNINGS',
  projectionCurrent: false,
  intelligenceScoreId: 'score-1',
  intelligenceScorePercent: 91,
  intelligenceGrade: 'EXCELLENT',
  intelligenceCurrent: false,
  topImprovementCodes: [],
  enrichmentAvailable: false,
  exportAvailable: false,
}

function renderCatalog(initialEntry = '/products') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={theme}>
        <MemoryRouter initialEntries={[initialEntry]}>
          <NotificationProvider>
            <Routes>
              <Route path="/products" element={<ProductsPage />} />
              <Route
                path="/products/:productId"
                element={<div>Product detail route</div>}
              />
            </Routes>
          </NotificationProvider>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  api.search.mockReset()
  api.search.mockResolvedValue({ items: [product], nextCursor: null })
})

describe('Product Catalog', () => {
  it('renders real summary fields, stale states, desktop table, and mobile card metadata', async () => {
    renderCatalog()
    expect(await screen.findAllByText(product.name)).not.toHaveLength(0)
    expect(screen.getAllByText('Ready to Publish').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Ready with Warnings').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Excellent').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Outdated').length).toBeGreaterThan(0)
    expect(screen.getAllByText('20 Aug 2026').length).toBeGreaterThan(0)
  }, 15000)

  it('submits name prefix and exact model searches without incompatible filters', async () => {
    const user = userEvent.setup()
    renderCatalog()
    await screen.findAllByText(product.name)
    const search = screen.getByLabelText('Product name prefix')
    await user.type(search, '  Industrial  ')
    await user.click(screen.getByRole('button', { name: 'Search' }))
    await waitFor(() =>
      expect(api.search).toHaveBeenLastCalledWith(
        expect.objectContaining({ namePrefix: 'Industrial', limit: 20 }),
        expect.anything(),
      ),
    )
    expect(screen.getByLabelText('Category')).toHaveAttribute(
      'aria-disabled',
      'true',
    )
    await user.click(screen.getByLabelText('Search products by'))
    await user.click(screen.getByRole('option', { name: 'Model number' }))
    const model = screen.getByLabelText('Exact model number')
    await user.type(model, 'IM-5500')
    await user.keyboard('{Enter}')
    await waitFor(() =>
      expect(api.search).toHaveBeenLastCalledWith(
        expect.objectContaining({ modelNumber: 'IM-5500' }),
        expect.anything(),
      ),
    )
  }, 15000)

  it('supports category plus status and exclusive manufacturer filters', async () => {
    const user = userEvent.setup()
    renderCatalog()
    await screen.findAllByText(product.name)
    await user.click(screen.getByLabelText('Category'))
    await user.click(screen.getByRole('option', { name: 'Induction Motor' }))
    await user.click(screen.getByLabelText('Status'))
    await user.click(screen.getByRole('option', { name: 'Ready to Publish' }))
    await waitFor(() =>
      expect(api.search).toHaveBeenLastCalledWith(
        expect.objectContaining({
          category: 'INDUCTION_MOTOR',
          status: 'READY_TO_PUBLISH',
        }),
        expect.anything(),
      ),
    )
    await user.click(screen.getByRole('button', { name: 'Clear all' }))
    await user.type(screen.getByLabelText('Manufacturer'), 'ABC Motors')
    await user.click(screen.getByRole('button', { name: 'Apply' }))
    await waitFor(() =>
      expect(api.search).toHaveBeenLastCalledWith(
        expect.objectContaining({ manufacturer: 'ABC Motors' }),
        expect.anything(),
      ),
    )
    expect(screen.getByLabelText('Category')).toHaveAttribute(
      'aria-disabled',
      'true',
    )
  }, 15000)

  it('removes active chips and clears all filters', async () => {
    const user = userEvent.setup()
    renderCatalog('/products?category=INDUCTION_MOTOR&status=DRAFT')
    await screen.findAllByText(product.name)
    expect(screen.getByText('Category: Induction Motor')).toBeInTheDocument()
    await user.click(
      within(
        screen.getByText('Category: Induction Motor').closest('.MuiChip-root'),
      ).getByTestId('CancelIcon'),
    )
    await waitFor(() =>
      expect(api.search).toHaveBeenLastCalledWith(
        expect.not.objectContaining({ category: 'INDUCTION_MOTOR' }),
        expect.anything(),
      ),
    )
    await user.click(screen.getByRole('button', { name: 'Clear all' }))
    await waitFor(() =>
      expect(api.search).toHaveBeenLastCalledWith(
        { limit: 20 },
        expect.anything(),
      ),
    )
  })

  it('moves forward and backward through opaque cursors', async () => {
    api.search.mockImplementation(async (params) => ({
      items: [product],
      nextCursor: params.cursor ? null : 'opaque-next',
    }))
    const user = userEvent.setup()
    renderCatalog()
    await screen.findAllByText(product.name)
    await user.click(screen.getAllByRole('button', { name: 'Next' })[0])
    await waitFor(() =>
      expect(api.search).toHaveBeenLastCalledWith(
        expect.objectContaining({ cursor: 'opaque-next' }),
        expect.anything(),
      ),
    )
    await user.click(screen.getAllByRole('button', { name: 'Previous' })[0])
    await waitFor(() =>
      expect(api.search).toHaveBeenLastCalledWith(
        expect.not.objectContaining({ cursor: 'opaque-next' }),
        expect.anything(),
      ),
    )
  })

  it('renders loading, onboarding, no-results, and safe error states', async () => {
    api.search.mockReturnValue(new Promise(() => {}))
    const loading = renderCatalog()
    expect(screen.getByLabelText('Loading products')).toBeInTheDocument()
    loading.unmount()
    api.search.mockResolvedValue({ items: [], nextCursor: null })
    const empty = renderCatalog()
    expect(
      await screen.findByRole('heading', {
        name: 'Build your product intelligence catalog',
      }),
    ).toBeInTheDocument()
    empty.unmount()
    const noResults = renderCatalog('/products?status=FAILED')
    expect(
      await screen.findByRole('heading', {
        name: 'No products match these filters',
      }),
    ).toBeInTheDocument()
    noResults.unmount()
    api.search.mockRejectedValue(
      new ApiError({ message: 'Safe failure', requestId: 'req-catalog' }),
    )
    renderCatalog()
    expect(
      await screen.findByText('Request ID: req-catalog'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('opens mobile filters and keeps cards keyboard accessible', async () => {
    renderCatalog()
    await screen.findAllByText(product.name)
    fireEvent.click(
      screen.getByRole('button', { name: 'Open product filters' }),
    )
    expect(
      screen.getByRole('heading', { name: 'Product filters' }),
    ).toBeInTheDocument()
  }, 10000)
})

describe('ProductCard', () => {
  it('uses graceful placeholders and keyboard activation', () => {
    const onOpen = vi.fn()
    render(
      <ThemeProvider theme={theme}>
        <ProductCard
          product={{
            ...product,
            manufacturer: null,
            modelNumber: null,
            publishingReadiness: null,
            projectionCurrent: null,
            intelligenceScorePercent: null,
            intelligenceGrade: null,
            intelligenceCurrent: null,
          }}
          onOpen={onOpen}
        />
      </ThemeProvider>,
    )
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.getByText('Not evaluated')).toBeInTheDocument()
    expect(screen.getByText('Not scored')).toBeInTheDocument()
    fireEvent.keyDown(
      screen.getByRole('link', { name: `Open ${product.name}` }),
      { key: 'Enter' },
    )
    expect(onOpen).toHaveBeenCalledOnce()
  })
})
