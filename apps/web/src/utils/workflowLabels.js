export const workflowStatusLabels = {
  PENDING: 'Pending',
  RUNNING: 'Processing',
  WAITING_FOR_REVIEW: 'Review Required',
  FAILED: 'Failed',
  COMPLETED: 'Completed',
  COMPLETED_WITH_WARNINGS: 'Completed with Warnings',
}

export const stageLabels = {
  SOURCE_PROCESSING: 'Process source evidence',
  PRODUCT_CLASSIFICATION: 'Classify product',
  ATTRIBUTE_EXTRACTION: 'Extract attributes',
  ATTRIBUTE_NORMALIZATION: 'Normalize values and units',
  CONFLICT_DETECTION: 'Detect conflicts',
  COMPLETENESS: 'Check completeness',
  ATTRIBUTE_VALIDATION: 'Validate attributes',
  ATTRIBUTE_SELECTION: 'Select candidates',
  HUMAN_REVIEW: 'Human review',
  REVIEWED_ATTRIBUTE_MATERIALIZATION: 'Materialize reviewed attributes',
  CATALOG_PROJECTION: 'Build catalog projection',
  PUBLISHING_READINESS: 'Evaluate publishing readiness',
  CATALOG_EXPORT: 'Generate export package',
  AI_ENRICHMENT: 'Generate AI commerce content',
  PRODUCT_INTELLIGENCE_SCORE: 'Calculate intelligence score',
}

export const stageStatusLabels = {
  NOT_STARTED: 'Not started',
  RUNNING: 'Processing',
  WAITING: 'Waiting for review',
  COMPLETED: 'Completed',
  SKIPPED: 'Skipped',
  FAILED: 'Failed',
}

export const terminalWorkflowStatuses = new Set([
  'FAILED',
  'COMPLETED',
  'COMPLETED_WITH_WARNINGS',
])

export function isActiveWorkflow(status) {
  return status === 'RUNNING' || status === 'WAITING_FOR_REVIEW'
}

export function workflowPollingInterval(status) {
  return status === 'RUNNING' ? 2500 : false
}
