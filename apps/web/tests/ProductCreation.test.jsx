import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NotificationProvider } from '../src/components/feedback/NotificationProvider'
import { ProductCreationDrawer } from '../src/components/products/ProductCreationDrawer'
import { theme } from '../src/theme/theme'

const api = vi.hoisted(() => ({ create: vi.fn() }))
vi.mock('../src/api/products', () => ({
  createProduct: api.create,
  getProduct: vi.fn(),
}))

function renderDrawer(props = {}) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  const values = { open: true, onClose: vi.fn(), onCreated: vi.fn(), ...props }
  render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <NotificationProvider>
            <ProductCreationDrawer {...values} />
          </NotificationProvider>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  )
  return values
}

beforeEach(() => api.create.mockReset())

describe('Product creation drawer', () => {
  it('is accessible and rejects an empty required name', async () => {
    const user = userEvent.setup()
    renderDrawer()
    expect(
      screen.getByRole('heading', { name: 'Add Product' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/Product name/)).toHaveFocus()
    await user.click(screen.getByRole('button', { name: 'Create Product' }))
    expect(
      await screen.findByText('Product name is required.'),
    ).toBeInTheDocument()
    expect(api.create).not.toHaveBeenCalled()
  })
  it('submits the exact backend contract and completes the success flow', async () => {
    const created = {
      productId: 'new-product',
      name: 'Industrial Motor',
      category: 'UNCLASSIFIED',
      status: 'DRAFT',
    }
    api.create.mockResolvedValue(created)
    const callbacks = renderDrawer()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/Product name/), ' Industrial Motor ')
    await user.type(screen.getByLabelText('Manufacturer'), ' ABC Motors ')
    await user.type(screen.getByLabelText('Model number'), ' IM-1 ')
    await user.click(screen.getByRole('button', { name: 'Create Product' }))
    await waitFor(() =>
      expect(api.create).toHaveBeenCalledWith(
        {
          name: 'Industrial Motor',
          manufacturer: 'ABC Motors',
          modelNumber: 'IM-1',
          category: 'UNCLASSIFIED',
          description: null,
        },
        expect.anything(),
      ),
    )
    expect(
      await screen.findByText('Product created successfully.'),
    ).toBeInTheDocument()
    expect(callbacks.onClose).toHaveBeenCalled()
    expect(callbacks.onCreated).toHaveBeenCalledWith(created)
  })
  it('retains values and safely presents request IDs on failure', async () => {
    const mutation = {
      isError: true,
      isPending: false,
      error: {
        message: 'A product conflict occurred.',
        requestId: 'req-create',
      },
      mutate: vi.fn(),
      reset: vi.fn(),
    }
    renderDrawer({
      mutation: {
        ...mutation,
      },
    })
    const user = userEvent.setup()
    const name = screen.getByLabelText(/Product name/)
    await user.type(name, 'Industrial Pump')
    await user.click(screen.getByRole('button', { name: 'Create Product' }))
    expect(mutation.mutate).toHaveBeenCalled()
    expect(
      screen.getByText("We couldn't create this product."),
    ).toBeInTheDocument()
    expect(screen.getByText('Request ID: req-create')).toBeInTheDocument()
    expect(name).toHaveValue('Industrial Pump')
  })
  it('closes with Escape through the drawer focus trap', async () => {
    const callbacks = renderDrawer()
    const user = userEvent.setup()
    await user.keyboard('{Escape}')
    await waitFor(() => expect(callbacks.onClose).toHaveBeenCalled())
  })
})
