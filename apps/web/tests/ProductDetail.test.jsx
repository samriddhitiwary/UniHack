import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ProductDetailPage } from '../src/pages/ProductDetailPage'
import { theme } from '../src/theme/theme'

const api = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('../src/api/products', () => ({
  createProduct: vi.fn(),
  getProduct: api.get,
}))

function renderDetail(initialEntry = '/products/product-1') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={theme}>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route
              path="/products/:productId"
              element={<ProductDetailPage />}
            />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => api.get.mockReset())

describe('Product detail shell', () => {
  it('retrieves and presents the real product identity', async () => {
    api.get.mockResolvedValue({
      productId: 'product-1',
      name: 'Industrial Pump',
      manufacturer: 'FlowCore',
      modelNumber: 'FC-410',
      category: 'CENTRIFUGAL_PUMP',
      status: 'READY_TO_PUBLISH',
      description: 'A high-efficiency centrifugal pump.',
    })
    renderDetail()

    expect(
      await screen.findByRole('heading', { name: 'Industrial Pump' }),
    ).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('product-1', expect.anything())
    expect(screen.getByText('FlowCore · FC-410')).toBeInTheDocument()
    expect(screen.getByText('Ready to Publish')).toBeInTheDocument()
    expect(screen.getByText('Centrifugal Pump')).toBeInTheDocument()
    expect(
      screen.getByText('A high-efficiency centrifugal pump.'),
    ).toBeInTheDocument()
  })
})
