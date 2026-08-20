import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { App } from '../src/App'

describe('CatalogIQ application shell', () => {
  it('renders the premium dashboard shell and fixture dashboard', async () => {
    render(<App />)
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Overview' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Total Products')).toBeInTheDocument()
    expect(screen.getByText('Catalog Quality')).toBeInTheDocument()
    expect(screen.getByText('Workflow Health')).toBeInTheDocument()
    expect(screen.getByText('Recent Products')).toBeInTheDocument()
    expect(screen.getByText('Attention Required')).toBeInTheDocument()
    expect(
      screen.getAllByRole('navigation', { name: 'Primary navigation' }).length,
    ).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: 'Overview' })[0]).toHaveClass(
      'active',
    )
  })

  it('opens mobile navigation and routes future features safely', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('heading', { level: 1, name: 'Overview' })
    const menu = screen.getByRole('button', { name: 'Open navigation' })
    expect(menu).toBeInTheDocument()
    await user.click(menu)
    const productLinks = screen.getAllByRole('link', { name: 'Products' })
    await user.click(productLinks[productLinks.length - 1])
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Products' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Products is coming soon')).toBeInTheDocument()
  })
})
