import { ThemeProvider } from '@mui/material'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { WorkflowSection } from '../src/components/workflows/WorkflowSection'
import { theme } from '../src/theme/theme'

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

function workflow(status, overrides = {}) {
  return {
    workflowId: 'workflow-1',
    status,
    version: 9,
    progressPercent: status === 'FAILED' ? 53 : 100,
    createdAt: '2026-08-20T10:00:00Z',
    startedAt: '2026-08-20T10:00:00Z',
    nextAction: 'NONE',
    projectionId: 'projection-1',
    exportId: 'export-1',
    enrichmentId: 'enrichment-1',
    scoreId: 'score-1',
    stages: stageNames.map((stage) => ({
      stage,
      status: 'COMPLETED',
      jobId: null,
      childJobIds: [],
      resultReference: null,
      startedAt: null,
      completedAt: '2026-08-20T10:10:00Z',
      errorCode: null,
      errorMessage: null,
      skipReason: null,
    })),
    ...overrides,
  }
}

function renderWorkflow(value) {
  const onSelect = vi.fn()
  const historyItem = {
    workflowId: value.workflowId,
    status: value.status,
    progressPercent: value.progressPercent,
    currentStage: 'CATALOG_PROJECTION',
    createdAt: value.createdAt,
  }
  render(
    <ThemeProvider theme={theme}>
      <WorkflowSection
        sourceCount={3}
        summary={{
          latestProjection: { status: 'READY_WITH_WARNINGS' },
          latestIntelligence: { overallScorePercent: 88, grade: 'GOOD' },
        }}
        historyQuery={{
          data: { pages: [{ items: [historyItem], nextCursor: null }] },
          isLoading: false,
          isError: false,
          hasNextPage: false,
        }}
        workflowQuery={{ data: value, isLoading: false, isError: false }}
        selectedId={value.workflowId}
        onSelect={onSelect}
        onLaunch={vi.fn()}
        onReview={vi.fn()}
        onResume={vi.fn()}
        resumeMutation={{ isPending: false, isError: false }}
      />
    </ThemeProvider>,
  )
  return onSelect
}

describe('Workflow presentation', () => {
  it('shows completed outputs, progress, timeline statuses, and selectable history', async () => {
    const onSelect = renderWorkflow(workflow('COMPLETED'))
    expect(
      screen.getByText(/Catalog Intelligence Complete/),
    ).toBeInTheDocument()
    expect(screen.getByText('Catalog Projection')).toBeInTheDocument()
    expect(screen.getByText('AI Commerce Content')).toBeInTheDocument()
    expect(screen.getByText('Export Package')).toBeInTheDocument()
    expect(screen.getByText('Intelligence')).toBeInTheDocument()
    expect(
      screen.getByRole('progressbar', { name: 'Workflow progress' }),
    ).toHaveAttribute('aria-valuenow', '100')
    expect(screen.getByText('Analyze Sources — Completed')).toBeInTheDocument()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Latest workflow/ }))
    expect(onSelect).toHaveBeenCalledWith('workflow-1')
  })

  it('uses warning semantics and shows optional stages as skipped rather than failed', () => {
    const stages = workflow('COMPLETED').stages.map((stage) =>
      ['CATALOG_EXPORT', 'AI_ENRICHMENT'].includes(stage.stage)
        ? { ...stage, status: 'SKIPPED', skipReason: 'DISABLED' }
        : stage,
    )
    renderWorkflow(
      workflow('COMPLETED_WITH_WARNINGS', {
        stages,
        exportId: null,
        enrichmentId: null,
      }),
    )
    expect(
      screen.getAllByText('Completed with Warnings').length,
    ).toBeGreaterThan(0)
    expect(screen.getByText('Generate Outputs — Skipped')).toBeInTheDocument()
  })

  it('shows a safe terminal failure without a resume action', () => {
    const stages = workflow('FAILED').stages.map((stage) =>
      stage.stage === 'ATTRIBUTE_VALIDATION'
        ? {
            ...stage,
            status: 'FAILED',
            errorCode: 'VALIDATION_FAILED',
            errorMessage: 'A long safe validation error.',
          }
        : { ...stage, status: 'NOT_STARTED', completedAt: null },
    )
    renderWorkflow(
      workflow('FAILED', {
        stages,
        errorCode: 'VALIDATION_FAILED',
        errorMessage: 'Catalog validation could not complete.',
        projectionId: null,
        exportId: null,
        enrichmentId: null,
        scoreId: null,
      }),
    )
    expect(screen.getByText('Workflow Failed')).toBeInTheDocument()
    expect(
      screen.getAllByText('Error code: VALIDATION_FAILED').length,
    ).toBeGreaterThan(0)
    expect(
      screen.queryByRole('button', { name: 'Resume Workflow' }),
    ).not.toBeInTheDocument()
    expect(screen.getByText('Validate Catalog — Failed')).toBeInTheDocument()
  })
})
