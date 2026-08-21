import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NotificationProvider } from '../src/components/feedback/NotificationProvider'
import { ProductDetailPage } from '../src/pages/ProductDetailPage'
import { theme } from '../src/theme/theme'

const api = vi.hoisted(() => ({
  getProduct: vi.fn(),
  getSummary: vi.fn(),
  listSources: vi.fn(),
  uploadSource: vi.fn(),
  createText: vi.fn(),
  deleteSource: vi.fn(),
  listWorkflows: vi.fn(),
  getWorkflow: vi.fn(),
  startWorkflow: vi.fn(),
  resumeWorkflow: vi.fn(),
}))

vi.mock('../src/api/products', () => ({ getProduct: api.getProduct }))
vi.mock('../src/api/catalog', () => ({
  getCatalogProductSummary: api.getSummary,
}))
vi.mock('../src/api/sources', () => ({
  listProductSources: api.listSources,
  uploadProductSource: api.uploadSource,
  createTextSource: api.createText,
  deleteProductSource: api.deleteSource,
}))
vi.mock('../src/api/workflows', () => ({
  listCatalogWorkflows: api.listWorkflows,
  getCatalogWorkflow: api.getWorkflow,
  startCatalogWorkflow: api.startWorkflow,
  resumeCatalogWorkflow: api.resumeWorkflow,
}))

const productId = '11111111-1111-4111-8111-111111111111'
const workflowId = '22222222-2222-4222-8222-222222222222'
const reviewId = '33333333-3333-4333-8333-333333333333'
const product = {
  productId,
  name: 'Very Long Industrial High Efficiency Centrifugal Pump FC-410',
  manufacturer: 'FlowCore',
  modelNumber: 'FC-410',
  category: 'CENTRIFUGAL_PUMP',
  status: 'READY_TO_PUBLISH',
  version: 3,
  updatedAt: '2026-08-20T10:00:00Z',
}
const summary = {
  ...product,
  latestProjection: {
    status: 'READY_WITH_WARNINGS',
    projectionCurrent: false,
  },
  latestIntelligence: {
    overallScorePercent: 91,
    grade: 'EXCELLENT',
    intelligenceCurrent: false,
  },
  enrichmentAvailable: true,
  exportAvailable: true,
}
const source = {
  sourceId: '44444444-4444-4444-8444-444444444444',
  productId,
  sourceType: 'PDF',
  status: 'READY',
  originalFilename: 'Extremely Long Industrial Motor Technical Datasheet.pdf',
  displayName: null,
  errorMessage: null,
  createdAt: '2026-08-20T11:00:00Z',
  version: 2,
}
const stageNames = [
  'SOURCE_PROCESSING',
  'PRODUCT_CLASSIFICATION',
  'ATTRIBUTE_EXTRACTION',
  'ATTRIBUTE_NORMALIZATION',
  'CONFLICT_DETECTION',
  'COMPLETENESS',
  'ATTRIBUTE_VALIDATION',
  'ATTRIBUTE_SELECTION',
  'HUMAN_REVIEW',
  'REVIEWED_ATTRIBUTE_MATERIALIZATION',
  'CATALOG_PROJECTION',
  'PUBLISHING_READINESS',
  'CATALOG_EXPORT',
  'AI_ENRICHMENT',
  'PRODUCT_INTELLIGENCE_SCORE',
]
function makeWorkflow(status = 'RUNNING', overrides = {}) {
  return {
    workflowId,
    productId,
    status,
    version: 7,
    progressPercent: status === 'RUNNING' ? 42 : 60,
    currentStage: 'ATTRIBUTE_VALIDATION',
    nextAction: 'NONE',
    reviewId: null,
    projectionId: null,
    exportId: null,
    enrichmentId: null,
    scoreId: null,
    createdAt: '2026-08-20T12:00:00Z',
    startedAt: '2026-08-20T12:00:00Z',
    stages: stageNames.map((stage, index) => ({
      stage,
      status: index < 4 ? 'COMPLETED' : index === 4 ? 'RUNNING' : 'NOT_STARTED',
      jobId: null,
      childJobIds: [],
      resultReference: null,
      startedAt: null,
      completedAt: null,
      errorCode: null,
      errorMessage: null,
      skipReason: null,
    })),
    ...overrides,
  }
}

function renderWorkspace() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={theme}>
        <MemoryRouter initialEntries={[`/products/${productId}`]}>
          <NotificationProvider>
            <Routes>
              <Route
                path="/products/:productId"
                element={<ProductDetailPage />}
              />
              <Route
                path="/products/:productId/review/:reviewId"
                element={<div>Review route reached</div>}
              />
            </Routes>
          </NotificationProvider>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  for (const mock of Object.values(api)) mock.mockReset()
  api.getProduct.mockResolvedValue(product)
  api.getSummary.mockResolvedValue(summary)
  api.listSources.mockResolvedValue({ items: [source], nextCursor: null })
  api.uploadSource.mockResolvedValue(source)
  api.createText.mockResolvedValue({ ...source, sourceType: 'TEXT' })
  api.deleteSource.mockResolvedValue(undefined)
  api.listWorkflows.mockResolvedValue({ items: [], nextCursor: null })
  api.getWorkflow.mockResolvedValue(makeWorkflow())
  api.startWorkflow.mockResolvedValue(makeWorkflow())
  api.resumeWorkflow.mockResolvedValue(makeWorkflow('COMPLETED'))
})

describe('Product Workspace', () => {
  it('renders real Product identity, catalog summaries, navigation, and sources', async () => {
    const user = userEvent.setup()
    renderWorkspace()
    expect(
      await screen.findByRole('heading', { name: product.name }),
    ).toBeInTheDocument()
    expect(screen.getByText('FlowCore · FC-410')).toBeInTheDocument()
    expect(screen.getAllByText('Ready with Warnings').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Outdated').length).toBe(2)
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    await user.click(screen.getByRole('tab', { name: 'Sources' }))
    expect(await screen.findByText(source.originalFilename)).toBeInTheDocument()
    expect(screen.getByText('PDF Datasheet')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: `Delete ${source.originalFilename}` }),
    ).toBeEnabled()
  })

  it('validates files locally and uploads every supported source family', async () => {
    const user = userEvent.setup()
    renderWorkspace()
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('tab', { name: 'Sources' }))
    const input = screen.getByLabelText('Choose product source file')
    fireEvent.change(input, {
      target: {
        files: [new File(['bad'], 'nameplate.bmp', { type: 'image/bmp' })],
      },
    })
    expect(
      screen.getByText('Choose a PDF, CSV, PNG, JPEG, or WEBP file.'),
    ).toBeInTheDocument()
    expect(api.uploadSource).not.toHaveBeenCalled()

    const supported = [
      new File(['%PDF-1.7'], 'motor.pdf', { type: 'application/pdf' }),
      new File(['a,b'], 'motor.csv', { type: 'text/csv' }),
      new File(['png'], 'plate.png', { type: 'image/png' }),
      new File(['jpg'], 'plate.jpg', { type: 'image/jpeg' }),
      new File(['webp'], 'plate.webp', { type: 'image/webp' }),
    ]
    for (const [index, file] of supported.entries()) {
      fireEvent.change(input, { target: { files: [file] } })
      await waitFor(() =>
        expect(api.uploadSource).toHaveBeenCalledTimes(index + 1),
      )
      expect(api.uploadSource).toHaveBeenLastCalledWith(
        { productId, file },
        expect.anything(),
      )
    }
  })

  it('rejects oversized PDF and CSV files before upload', async () => {
    const user = userEvent.setup()
    renderWorkspace()
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('tab', { name: 'Sources' }))
    const input = screen.getByLabelText('Choose product source file')
    const pdf = new File(['pdf'], 'large.pdf', { type: 'application/pdf' })
    Object.defineProperty(pdf, 'size', { value: 10 * 1024 * 1024 + 1 })
    fireEvent.change(input, { target: { files: [pdf] } })
    expect(
      screen.getByText('PDF and image files must be 10 MiB or smaller.'),
    ).toBeInTheDocument()
    const csv = new File(['csv'], 'large.csv', { type: 'text/csv' })
    Object.defineProperty(csv, 'size', { value: 5 * 1024 * 1024 + 1 })
    fireEvent.change(input, { target: { files: [csv] } })
    expect(
      screen.getByText('CSV files must be 5 MiB or smaller.'),
    ).toBeInTheDocument()
    expect(api.uploadSource).not.toHaveBeenCalled()
  })

  it('creates a validated text source without starting a workflow', async () => {
    const user = userEvent.setup()
    renderWorkspace()
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('tab', { name: 'Sources' }))
    await user.click(screen.getByRole('button', { name: 'Add Text Source' }))
    await user.type(screen.getByLabelText('Source name'), 'Supplier email')
    await user.type(
      screen.getByLabelText('Source text'),
      'Maximum pressure: 16 bar',
    )
    await user.click(screen.getByRole('button', { name: 'Add Text Source' }))
    await waitFor(() =>
      expect(api.createText).toHaveBeenCalledWith(
        {
          productId,
          displayName: 'Supplier email',
          textContent: 'Maximum pressure: 16 bar',
        },
        expect.anything(),
      ),
    )
    expect(api.startWorkflow).not.toHaveBeenCalled()
  })

  it('uses the confirmed empty-source state to prevent workflow launch', async () => {
    api.listSources.mockResolvedValue({ items: [], nextCursor: null })
    const user = userEvent.setup()
    renderWorkspace()
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('tab', { name: 'Workflow' }))
    expect(
      screen.getByText(
        'Add at least one source before starting product intelligence.',
      ),
    ).toBeInTheDocument()
    expect(
      screen
        .getAllByRole('button', { name: 'Start Intelligence Workflow' })
        .at(-1),
    ).toBeDisabled()
  })

  it('deletes a source with its exact version after confirmation', async () => {
    const user = userEvent.setup()
    renderWorkspace()
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('tab', { name: 'Sources' }))
    await user.click(
      screen.getByRole('button', { name: `Delete ${source.originalFilename}` }),
    )
    expect(screen.getByRole('dialog')).toHaveTextContent('Delete this source?')
    await user.click(screen.getByRole('button', { name: 'Delete Source' }))
    await waitFor(() =>
      expect(api.deleteSource).toHaveBeenCalledWith(
        { productId, sourceId: source.sourceId, version: 2 },
        expect.anything(),
      ),
    )
  })

  it('launches with the exact friendly default configuration', async () => {
    const user = userEvent.setup()
    renderWorkspace()
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('tab', { name: 'Workflow' }))
    await user.click(
      screen
        .getAllByRole('button', { name: 'Start Intelligence Workflow' })
        .at(-1),
    )
    expect(
      screen.getByRole('switch', { name: /Prepare publishing readiness/ }),
    ).toBeChecked()
    expect(
      screen.getByRole('switch', { name: /Generate export package/ }),
    ).toBeChecked()
    expect(
      screen.getByRole('switch', { name: /Generate AI commerce content/ }),
    ).toBeChecked()
    expect(
      screen.getByRole('switch', { name: /Calculate intelligence score/ }),
    ).toBeChecked()
    await user.click(screen.getByText('Advanced settings'))
    expect(
      screen.getByRole('switch', { name: /Stop workflow/ }),
    ).not.toBeChecked()
    await user.click(screen.getByRole('button', { name: 'Start Workflow' }))
    await waitFor(() =>
      expect(api.startWorkflow).toHaveBeenCalledWith(
        {
          productId,
          configuration: {
            applyPublishingReadiness: true,
            generateExport: true,
            generateAiEnrichment: true,
            calculateIntelligenceScore: true,
            failOnOptionalStageError: false,
          },
        },
        expect.anything(),
      ),
    )
    expect(
      await screen.findByRole('progressbar', { name: 'Workflow progress' }),
    ).toHaveAttribute('aria-valuenow', '42')
  })

  it('preserves reviewId and exposes review navigation without bypass controls', async () => {
    const waiting = makeWorkflow('WAITING_FOR_REVIEW', {
      reviewId,
      nextAction: 'COMPLETE_PRODUCT_REVIEW',
      stages: stageNames.map((stage) => ({
        stage,
        status:
          stage === 'HUMAN_REVIEW'
            ? 'WAITING'
            : stageNames.indexOf(stage) < 8
              ? 'COMPLETED'
              : 'NOT_STARTED',
        jobId: null,
        childJobIds: [],
        resultReference: null,
        startedAt: null,
        completedAt: null,
        errorCode: null,
        errorMessage: null,
        skipReason: null,
      })),
    })
    api.listWorkflows.mockResolvedValue({ items: [waiting], nextCursor: null })
    api.getWorkflow.mockResolvedValue(waiting)
    const user = userEvent.setup()
    renderWorkspace()
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('tab', { name: 'Workflow' }))
    await user.click(screen.getByRole('tab', { name: 'Sources' }))
    expect(
      screen.getByRole('button', { name: `Delete ${source.originalFilename}` }),
    ).toBeDisabled()
    expect(
      screen.getByText(/included only when the next workflow starts/),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Workflow' }))
    await user.click(
      await screen.findByRole('button', { name: 'Review Attributes' }),
    )
    expect(await screen.findByText('Review route reached')).toBeInTheDocument()
    expect(screen.queryByText(/Approve|Reject|Bypass/)).not.toBeInTheDocument()
  })

  it('resumes only with the current workflow version', async () => {
    const waiting = makeWorkflow('WAITING_FOR_REVIEW', {
      reviewId,
      nextAction: 'RESUME_WORKFLOW',
    })
    api.listWorkflows.mockResolvedValue({ items: [waiting], nextCursor: null })
    api.getWorkflow.mockResolvedValue(waiting)
    const user = userEvent.setup()
    renderWorkspace()
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('tab', { name: 'Workflow' }))
    await user.click(
      await screen.findByRole('button', { name: 'Resume Workflow' }),
    )
    await waitFor(() =>
      expect(api.resumeWorkflow).toHaveBeenCalledWith(
        {
          productId,
          workflowId,
          version: 7,
        },
        expect.anything(),
      ),
    )
  })
})
