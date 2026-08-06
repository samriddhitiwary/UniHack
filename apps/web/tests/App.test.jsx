import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { App } from '../src/App'

describe('CatalogIQ application shell', () => {
  it('renders the foundation home page', () => {
    render(<App />)
    expect(screen.getByText('CatalogIQ AI')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Product intelligence, built on trustworthy foundations.',
    )
    expect(screen.getByText('Foundation ready')).toBeInTheDocument()
  })
})
