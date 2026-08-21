import { describe, expect, it } from 'vitest'
import { validateSourceFile } from '../src/utils/sourceLabels'
import { buildWorkflowPhases } from '../src/utils/workflowPhases'
import { workflowErrorMessage } from '../src/utils/workflowErrors'
import { workflowPollingInterval } from '../src/utils/workflowLabels'

describe('SPEC-040 workflow and source policies', () => {
  it('polls only running workflows at the bounded interval', () => {
    expect(workflowPollingInterval('RUNNING')).toBe(2500)
    for (const status of [
      'WAITING_FOR_REVIEW',
      'FAILED',
      'COMPLETED',
      'COMPLETED_WITH_WARNINGS',
    ])
      expect(workflowPollingInterval(status)).toBe(false)
  })

  it('aggregates technical stages into human-friendly phases', () => {
    const phases = buildWorkflowPhases([
      { stage: 'SOURCE_PROCESSING', status: 'COMPLETED' },
      { stage: 'HUMAN_REVIEW', status: 'WAITING' },
      { stage: 'CATALOG_EXPORT', status: 'SKIPPED' },
      { stage: 'AI_ENRICHMENT', status: 'SKIPPED' },
    ])
    expect(phases.map((phase) => phase.label)).toEqual([
      'Analyze Sources',
      'Understand Product',
      'Structure Attributes',
      'Validate Catalog',
      'Human Review',
      'Prepare Catalog',
      'Generate Outputs',
      'Quality Evaluation',
    ])
    expect(phases.find((phase) => phase.id === 'review').status).toBe('WAITING')
    expect(phases.find((phase) => phase.id === 'outputs').status).toBe(
      'SKIPPED',
    )
  })

  it('maps workflow conflicts to safe business language', () => {
    expect(
      workflowErrorMessage({ code: 'WORKFLOW_REVIEW_NOT_COMPLETED' }),
    ).toMatch(/Complete the human review/)
    expect(workflowErrorMessage({ code: 'WORKFLOW_PRODUCT_CHANGED' })).toMatch(
      /product changed/,
    )
    expect(workflowErrorMessage({ code: 'WORKFLOW_SOURCES_CHANGED' })).toMatch(
      /Sources changed/,
    )
  })

  it('rejects MIME mismatches and unsupported text files', () => {
    expect(
      validateSourceFile(new File(['x'], 'data.txt', { type: 'text/plain' })),
    ).toMatch(/PDF/)
    expect(
      validateSourceFile(new File(['x'], 'data.pdf', { type: 'text/plain' })),
    ).toMatch(/PDF/)
  })
})
